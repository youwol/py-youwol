from datetime import datetime
import json
import os

from pathlib import Path
from typing import List, Dict, Any, Union, Optional, Awaitable
from pydantic import BaseModel

from youwol.context import Context
from youwol.utils_low_level import get_public_user_auth_token
from youwol.configuration.models_config import ConfigurationHandler, configuration_from_json, \
    configuration_from_python, Events, UserInfo, RemoteGateway
from youwol.middlewares.dynamic_routing.custom_dispatch_rules import AbstractDispatch
from youwol.models import Label
from youwol.configuration.clients import LocalClients
from youwol.configuration.python_function_runner import get_python_function, PythonSourceFunction
from youwol.services.backs.assets_gateway.models import DefaultDriveResponse
from youwol.web_socket import WebSocketsCache

from youwol.errors import HTTPResponseException
from youwol.main_args import get_main_arguments
from youwol.utils_paths import parse_json

from youwol.configurations import get_full_local_config


from youwol.configuration.configuration_validation import (
    ConfigurationLoadingStatus, ConfigurationLoadingException,
    CheckSystemFolderWritable, CheckDatabasesFolderHealthy, CheckSecretPathExist,
    CheckSecretHealthy
)
from youwol.configuration.models_base import ErrorResponse, Project
from youwol.configuration.paths import PathsBook
from youwol_utils import encode_id


class DeadlinedCache(BaseModel):
    value: Any
    deadline: float
    dependencies: Dict[str, str]

    def is_valid(self, dependencies) -> bool:

        for k, v in self.dependencies.items():
            if k not in dependencies or dependencies[k] != v:
                return False
        margin = self.deadline - datetime.timestamp(datetime.now())
        return margin > 0


class YouwolConfiguration(BaseModel):
    localGateway: LocalGateway
    available_profiles: List[str]
    http_port: int
    openid_host: str
    events: Events
    active_profile: Optional[str]
    cdnAutomaticUpdate: bool
    customDispatches: List[AbstractDispatch]
    commands: Dict[str, Any]

    userEmail: Optional[str]
    selectedRemote: Optional[str]

    pathsBook: PathsBook

    projects: List[Project]

    cache: Dict[str, Any] = {}
    private_cache: Dict[str, Any] = {}

    tokensCache: List[DeadlinedCache] = []

    def get_user_info(self) -> UserInfo:

        users_info = parse_json(self.pathsBook.usersInfo)['users']

        if self.userEmail in users_info:
            data = users_info[self.userEmail]
            return UserInfo(**data)

        raise Exception(f"User '{self.userEmail}' not reference in '{str(self.pathsBook.usersInfo)}")

    def get_users_list(self) -> List[str]:
        users = list(parse_json(self.pathsBook.usersInfo)['users'].keys())
        return users

    def get_remote_info(self) -> Optional[RemoteGateway]:

        info = parse_json(self.pathsBook.remotesInfo)['remotes']

        if self.selectedRemote in info:
            data = info[self.selectedRemote]
            return RemoteGateway(**data)

        return None

    async def get_auth_token(self, context: Context, use_cache=True):
        username = self.userEmail
        remote = self.get_remote_info()
        dependencies = {"username": username, "host": remote.host, "type": "auth_token"}
        cached_token = next((c for c in self.tokensCache if c.is_valid(dependencies)), None)
        if use_cache and cached_token:
            return cached_token.value

        secrets = parse_json(self.pathsBook.secrets)
        if username not in secrets:
            raise RuntimeError(f"Can not find {username} in {str(self.pathsBook.secrets)}")

        pwd = secrets[username]['password']
        try:
            access_token = await get_public_user_auth_token(
                username=username,
                pwd=pwd,
                client_id=remote.metadata['keycloakClientId'],
                openid_host=self.openid_host
            )
        except Exception as e:
            raise RuntimeError(f"Can not authorize from email/pwd provided in " +
                               f"{str(self.pathsBook.secrets)} (error:{e})")

        deadline = datetime.timestamp(datetime.now()) + 1 * 60 * 60 * 1000
        self.tokensCache.append(DeadlinedCache(value=access_token, deadline=deadline, dependencies=dependencies))

        await context.info(labels=[Label.STATUS], text="Access token renewed",
                           data={"host": remote.host, "access_token": access_token})
        return access_token

    async def get_default_drive(self, context: Context) -> DefaultDriveResponse:

        if self.private_cache.get("default-drive"):
            return self.private_cache.get("default-drive")
        default_drive = await LocalClients.get_assets_gateway_client(context).get_default_user_drive()
        self.private_cache["default-drive"] = DefaultDriveResponse(**default_drive)
        return DefaultDriveResponse(**default_drive)

    def __str__(self):

        return f"""
Configuration loaded from '{self.pathsBook.config}'
- active profile: {self.active_profile if self.active_profile else "Default profile"}
- paths: {self.pathsBook}
- cdn packages count: {len(parse_json(self.pathsBook.local_cdn_docdb)['documents'])}
- assets count: {len(parse_json(self.pathsBook.local_docdb / 'assets' / 'entities' / 'data.json')['documents'])}
- list of projects:
{chr(10).join([f"  * {p.path} ({p.pipeline.id})" for p in self.projects])}
- list of redirections:
{chr(10).join([f"  * {redirection}" for redirection in self.customDispatches])}
"""


class YouwolConfigurationFactory:
    __cached_config: Optional[YouwolConfiguration] = None

    @staticmethod
    async def get():
        cached = YouwolConfigurationFactory.__cached_config
        config = cached or await YouwolConfigurationFactory.init()
        return config

    @staticmethod
    async def reload(profile: str = None):
        cached = YouwolConfigurationFactory.__cached_config
        conf = await safe_load(
            path=cached.pathsBook.config,
            profile=profile or get_main_arguments().profile,
            user_email=cached.userEmail,
            selected_remote=cached.selectedRemote
        )

        await YouwolConfigurationFactory.trigger_on_load(config=conf)
        print(conf)
        YouwolConfigurationFactory.__cached_config = conf

    @staticmethod
    async def login(email: Union[str, None], remote_name: Union[str, None], context: Context = None):
        conf = YouwolConfigurationFactory.__cached_config
        email, remote_name = await login(email, remote_name, conf.pathsBook.usersInfo,
                                         conf.pathsBook.remotesInfo, context)

        new_conf = YouwolConfiguration(
            openid_host=conf.openid_host,
            userEmail=email,
            selectedRemote=remote_name,
            pathsBook=conf.pathsBook,
            projects=conf.projects,
            http_port=conf.http_port,
            cache={},
            localGateway=conf.localGateway,
            available_profiles=conf.available_profiles,
            commands=conf.commands,
            customDispatches=conf.customDispatches,
            cdnAutomaticUpdate=conf.cdnAutomaticUpdate,
            events=conf.events
        )
        YouwolConfigurationFactory.__cached_config = new_conf
        await YouwolConfigurationFactory.trigger_on_load(config=conf)
        return new_conf

    @staticmethod
    async def init():
        path = (await get_full_local_config()).starting_yw_config_path
        conf = await safe_load(path=path, profile=get_main_arguments().profile, user_email=None, selected_remote=None)

        YouwolConfigurationFactory.__cached_config = conf
        await YouwolConfigurationFactory.trigger_on_load(config=conf)
        return YouwolConfigurationFactory.__cached_config

    @staticmethod
    def clear_cache():
        conf = YouwolConfigurationFactory.__cached_config
        new_conf = YouwolConfiguration(
            openid_host=conf.openid_host,
            userEmail=conf.userEmail,
            selectedRemote=conf.selectedRemote,
            pathsBook=conf.pathsBook,
            projects=conf.projects,
            http_port=conf.http_port,
            cache={},
            localGateway=conf.localGateway,
            available_profiles=conf.available_profiles,
            commands=conf.commands,
            customDispatches=conf.customDispatches,
            cdnAutomaticUpdate=conf.cdnAutomaticUpdate,
            events=conf.events
        )
        YouwolConfigurationFactory.__cached_config = new_conf

    @staticmethod
    async def trigger_on_load(config: YouwolConfiguration):
        context = Context(config=config, web_socket=WebSocketsCache.environment)
        if not config.events or not config.events.onLoad:
            return
        on_load_cb = config.events.onLoad

        data = await on_load_cb(config, context) \
            if inspect.iscoroutinefunction(on_load_cb) \
            else on_load_cb(config, context)

        await context.info(labels=[Label.STATUS], text="Applied onLoad event's callback", data=data)


async def yw_config() -> YouwolConfiguration:
    return await YouwolConfigurationFactory.get()


async def login(
        user_email: Union[str, None],
        selected_remote: Union[str, None],
        users_info_path: Path,
        remotes_info: Path,
        context: Union[Context, None]) -> (str, str):
    if user_email is None:
        users_info = parse_json(users_info_path)
        if 'default' in users_info['policies']:
            user_email = users_info['policies']["default"]

    if user_email is None:
        raise HTTPResponseException(
            status_code=401,
            title="User has not been identified",
            descriptions=[f"make sure your users info file ({users_info_path}) contains"],
            hints=[
                "a 'default' field is pointing to the desired default email address",
                "the desired default email address is associated to an identity"
            ]
        )
    if user_email not in parse_json(users_info_path)['users']:
        context and await context.info(
            labels=[Label.STATUS],
            text=f"User {user_email} not registered in {users_info_path}: switch user",
            data={"user_email": user_email, 'usersInfo': parse_json(users_info_path)
                  }
        )
        return await login(user_email=None, selected_remote=selected_remote, users_info_path=users_info_path,
                           remotes_info=remotes_info,
                           context=context)

    if remotes_info is None:
        return user_email, None

    remotes_info = parse_json(remotes_info)
    remotes = remotes_info['remotes']

    if selected_remote in remotes:
        return user_email, selected_remote

    if "policies" in remotes_info and "default" in remotes_info['policies']:
        default = remotes_info['policies']['default']
        if default in remotes:
            return user_email, default

    return user_email, None


async def safe_load(
        path: Path,
        profile: str,
        user_email: Optional[str],
        selected_remote: Optional[RemoteGateway],
        context: Optional[Context] = None,
) -> YouwolConfiguration:
    check_system_folder_writable = CheckSystemFolderWritable()
    check_database_folder_healthy = CheckDatabasesFolderHealthy()
    check_secret_exists = CheckSecretPathExist()
    check_secret_healthy = CheckSecretHealthy()

    def get_status(validated: bool = False):
        return ConfigurationLoadingStatus(
            path=str(path),
            validated=validated,
            checks=[
                check_system_folder_writable,
                check_database_folder_healthy,
                check_secret_exists,
                check_secret_healthy
            ]
        )

    loaders = {
        ".py": configuration_from_python,
        ".json": configuration_from_json
    }

    try:
        conf_handler: ConfigurationHandler = await loaders[path.suffix](path, profile)
    except KeyError as k:
        print(f"Unknown suffix : ${k}")
        raise ConfigurationLoadingException(get_status(False))

    paths_book = PathsBook(
        config=path,
        databases=Path(conf_handler.get_data_dir()),
        system=Path(conf_handler.get_cache_dir()),
        secrets=Path(conf_handler.get_config_dir() / Path("secrets.json")),
        usersInfo=Path(conf_handler.get_config_dir() / Path("users-info.json")),
        remotesInfo=Path(conf_handler.get_config_dir() / Path("remotes-info.json"))
    )

    if not os.access(paths_book.system.parent, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system.parent)}",
            hints=[f"Ensure you have permission to write in {paths_book.system}."]
        )
        raise ConfigurationLoadingException(get_status(False))

    if not paths_book.system.exists():
        os.mkdir(paths_book.system)

    check_system_folder_writable.status = True

    if not os.access(paths_book.system, os.W_OK):
        check_system_folder_writable.status = ErrorResponse(
            reason=f"Can not write in folder {str(paths_book.system)}",
            hints=[f"Ensure you have permission to write in {paths_book.system}."]
        )
        raise ConfigurationLoadingException(get_status(False))

    if not paths_book.store_node_modules.exists():
        os.mkdir(paths_book.store_node_modules)

    if not paths_book.packages_cache_path.exists():
        open(paths_book.packages_cache_path, "w").write(json.dumps({}))

    if not paths_book.usersInfo.exists():
        open(paths_book.usersInfo, "w").write(json.dumps({"policies": {}, "users": {}}))

    if not paths_book.remotesInfo.exists():
        open(paths_book.remotesInfo, "w").write(json.dumps({"remotes": {}}))

    if not paths_book.secrets.exists():
        base_secrets = {
            "identities": {}
        }
        open(paths_book.secrets, "w").write(json.dumps(base_secrets))

    if not paths_book.packages_cache_path.exists():
        open(paths_book.secrets, "w").write(json.dumps({}))

    user_email, selected_remote = await login(
        user_email=user_email,
        selected_remote=selected_remote,
        users_info_path=paths_book.usersInfo,
        remotes_info=paths_book.remotesInfo,
        context=context)

    projects = []
    targets_dirs = []
    nb_targets_dirs = len(targets_dirs)
    for projects_dir in conf_handler.get_projects_dirs():
        if (projects_dir / '.yw_pipeline').exists():
            targets_dirs.append(projects_dir)
        else:
            for subdir in os.listdir(projects_dir):
                if (projects_dir / Path(subdir) / '.yw_pipeline').exists():
                    targets_dirs.append(projects_dir / Path(subdir))
        nb_targets_dirs_found = len(targets_dirs) - nb_targets_dirs
        nb_targets_dirs = len(targets_dirs)
        if nb_targets_dirs_found == 0:
            print(f"No project found in '{projects_dir}'")
        else:
            print(f"found {nb_targets_dirs_found} projects in '{projects_dir}'")

    for path in targets_dirs:
        try:
            pipeline = get_python_function(
                PythonSourceFunction(path=path / '.yw_pipeline' / 'yw_pipeline.py', name='pipeline'))(conf_handler)

            name = pipeline.projectName(path)
            project = Project(
                name=name,
                id=encode_id(name),
                version=pipeline.projectVersion(path),
                pipeline=pipeline,
                path=path
            )
            projects.append(project)

        except Exception as e:
            print(f"Could not load project in dir '{path}' : ", str(e))

    youwol_configuration = YouwolConfiguration(
        active_profile=conf_handler.get_profile(),
        available_profiles=conf_handler.get_available_profiles(),
        openid_host=conf_handler.get_openid_host(),
        http_port=conf_handler.get_http_port(),
        userEmail=user_email,
        selectedRemote=selected_remote,
        events=conf_handler.get_events(),
        cdnAutomaticUpdate=conf_handler.get_cdn_auto_update(),
        pathsBook=paths_book,
        projects=projects,
        commands={key: get_python_function(source_function=source) for (key, source) in
                  conf_handler.get_commands().items()},
        localGateway=LocalGateway(),
        customDispatches=conf_handler.get_dispatches()
    )

    return conf_handler.customize(youwol_configuration)
