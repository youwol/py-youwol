# standard library
import asyncio
import json
import os
import shutil

from glob import glob
from pathlib import Path

# typing
from typing import cast

# third parties
import brotli

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import (
    AuthorizationProvider,
    CdnSwitch,
    CloudEnvironment,
    CloudEnvironments,
    Command,
    Configuration,
    Connection,
    CustomEndPoints,
    Customization,
    CustomMiddleware,
    DirectAuth,
    FlowSwitcherMiddleware,
    IConfigurationFactory,
    LocalClients,
    LocalEnvironment,
    Projects,
    ProjectsFinder,
    RemoteClients,
    System,
    TokensStorageInMemory,
    YouwolEnvironment,
)
from youwol.app.main_args import MainArguments
from youwol.app.routers.projects import ProjectLoader
from youwol.app.routers.system.router import LeafLogResponse, Log, NodeLogResponse

# Youwol utilities
from youwol.utils import (
    ContextFactory,
    InMemoryReporter,
    PrivateClient,
    execute_shell_cmd,
    parse_json,
    sed_inplace,
)
from youwol.utils.context import Context, Label
from youwol.utils.http_clients.cdn_backend.utils import (
    encode_extra_index as encode_index,
)

# Youwol pipelines
import youwol.pipelines.pipeline_typescript_weback_npm as pipeline_ts

from youwol.pipelines.pipeline_typescript_weback_npm import (
    app_ts_webpack_template,
    lib_ts_webpack_template,
)

ref_folder = Path(__file__).parent
projects_folder = ref_folder / "projects"
system_folder = ref_folder / "youwol_system"
databases_folder = ref_folder / "databases"

users = [
    (os.getenv("USERNAME_INTEGRATION_TESTS"), os.getenv("PASSWORD_INTEGRATION_TESTS")),
    (
        os.getenv("USERNAME_INTEGRATION_TESTS_BIS"),
        os.getenv("PASSWORD_INTEGRATION_TESTS_BIS"),
    ),
]

direct_auths = [
    DirectAuth(authId=email, userName=email, password=pwd) for email, pwd in users
]

cloud_env = CloudEnvironment(
    envId="prod",
    host="platform.int.youwol.com",
    authProvider=AuthorizationProvider(
        openidClient=PrivateClient(
            client_id="integration-tests",
            client_secret=os.getenv("CLIENT_SECRET_INTEGRATION_TESTS"),
        ),
        openidBaseUrl="https://platform.int.youwol.com/auth/realms/youwol/",
    ),
    authentications=direct_auths,
)


def clear_data(databases: bool):
    shutil.rmtree(projects_folder, ignore_errors=True)
    shutil.rmtree(system_folder, ignore_errors=True)
    os.mkdir(projects_folder)
    os.mkdir(system_folder)
    if databases:
        shutil.rmtree(databases_folder, ignore_errors=True)


async def clone_project(git_url: str, branch: str, new_project_name: str, ctx: Context):
    folder_name = new_project_name.split("/")[-1]
    dst_folder = system_folder / folder_name
    await execute_shell_cmd(
        cmd=f"(cd {system_folder} && git clone -b {branch} {git_url} {folder_name})",
        context=ctx,
    )
    if not (system_folder / folder_name).exists():
        raise RuntimeError("Git repo not properly cloned")

    old_project_name = parse_json(dst_folder / "package.json")["name"]
    # Below implementation is specific for ts/js projects
    sed_inplace(dst_folder / "package.json", old_project_name, new_project_name)
    src_files = [
        *glob(f"{dst_folder}/**/*.js", recursive=True),
        *glob(f"{dst_folder}/**/*.ts", recursive=True),
        *glob(f"{dst_folder}/**/*.html", recursive=True),
    ]
    for file in src_files:
        sed_inplace(file, old_project_name, new_project_name)

    await execute_shell_cmd(
        cmd=f"(mv {system_folder}/{folder_name} {projects_folder}/{folder_name})",
        context=ctx,
    )
    return {}


async def exec_shell(command: str, ctx: Context):
    await execute_shell_cmd(cmd=f"(cd {ref_folder} && {command})", context=ctx)


async def purge_downloads(context: Context):
    async with context.start(action="purge_downloads") as ctx:  # type: Context
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        assets_gtw = await RemoteClients.get_twin_assets_gateway_client(env=env)
        headers = ctx.headers()
        default_drive = (
            await LocalClients.get_assets_gateway_client(env)
            .get_treedb_backend_router()
            .get_default_user_drive(headers=context.headers())
        )
        treedb_client = assets_gtw.get_treedb_backend_router()
        resp = await treedb_client.get_children(
            folder_id=default_drive["downloadFolderId"], headers=headers
        )
        await asyncio.gather(
            *[
                treedb_client.remove_item(item_id=item["treeId"], headers=headers)
                for item in resp["items"]
            ],
            *[
                treedb_client.remove_folder(folder_id=item["folderId"], headers=headers)
                for item in resp["folders"]
            ],
        )
        await treedb_client.purge_drive(
            drive_id=default_drive["driveId"], headers=headers
        )
        return {}


async def reset(ctx: Context):
    env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
    env.reset_cache()
    env.reset_databases()
    clear_data(databases=False)
    await ProjectLoader.initialize(env=env)


async def create_test_data_remote(context: Context):
    async with context.start("create_new_story_remote") as ctx:
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        target_cloud = env.get_remote_info()
        await ctx.info(f"selected Host for creation: {target_cloud.host}")
        folder_id = "private_51c42384-3582-494f-8c56-7405b01646ad_default-drive_home"
        gtw = await RemoteClients.get_assets_gateway_client(
            cloud_environment=target_cloud,
            auth_id=env.currentConnection.authId,
            tokens_storage=env.tokens_storage,
        )
        asset_resp = await gtw.get_assets_backend_router().create_asset(
            body={
                "rawId": "test-custom-asset",
                "kind": "custom-asset",
                "name": "Asset + files (remote test data in local-youwol-client)",
                "description": "A custom asset used to test posting files and auto-download of assets with files",
                "tags": ["integration-test", "local-youwol-client"],
            },
            params=[("folder-id", folder_id)],
            headers=ctx.headers(),
        )
        with open(ref_folder / "test-add-files.zip", "rb").read() as data:
            upload_resp = await gtw.get_assets_backend_router().add_zip_files(
                asset_id=asset_resp["assetId"], data=data, headers=ctx.headers()
            )

        resp_stories = await gtw.get_stories_backend_router().create_story(
            body={
                "storyId": "504039f7-a51f-403d-9672-577b846fdbd8",
                "title": "Story (remote test data in local-youwol-client)",
            },
            params=[("folder-id", folder_id)],
            headers=ctx.headers(),
        )

        resp_flux = await gtw.get_flux_backend_router().create_project(
            body={
                "projectId": "2d5cafa9-f903-4fa7-b343-b49dfba20023",
                "description": "a flux project dedicated to test in http-clients",
                "name": "Flux-project (remote test data in local-youwol-client)",
            },
            params=[("folder-id", folder_id)],
            headers=ctx.headers(),
        )

        content = json.dumps(
            {
                "description": "a file uploaded in remote env for test purposes (local-youwol-client)"
            }
        )
        form = {
            "file": str.encode(content),
            "content_type": "application/json",
            "file_id": "f72290f2-90bc-4192-80ca-20f983a1213d",
            "file_name": "Uploaded file (remote test data in local-youwol-client)",
        }
        resp_data = await gtw.get_files_backend_router().upload(
            data=form, params=[("folder-id", folder_id)], headers=ctx.headers()
        )
        resp = {
            "respCustomAsset": {"asset": asset_resp, "addFiles": upload_resp},
            "respStories": resp_stories,
            "respFlux": resp_flux,
            "respData": resp_data,
        }
        await ctx.info("Story successfully created", data=resp)
        return resp


async def erase_all_test_data_remote(context: Context):
    async with context.start("erase_all_test_data_remote") as ctx:
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        target_cloud = env.get_remote_info()
        await ctx.info(f"selected Host for deletion: {target_cloud.host}")
        drive_id = "private_51c42384-3582-494f-8c56-7405b01646ad_default-drive"
        folder_id = f"{drive_id}_home"
        gtw = await RemoteClients.get_assets_gateway_client(
            cloud_environment=target_cloud,
            auth_id=env.currentConnection.authId,
            tokens_storage=env.tokens_storage,
        )
        resp = await gtw.get_treedb_backend_router().get_children(
            folder_id=folder_id, headers=ctx.headers()
        )
        await asyncio.gather(
            *[
                gtw.get_treedb_backend_router().remove_item(
                    item_id=item["itemId"], headers=ctx.headers()
                )
                for item in resp["items"]
            ]
        )
        await gtw.get_treedb_backend_router().purge_drive(
            drive_id=drive_id, headers=ctx.headers()
        )
        return {"items": resp["items"]}


pipeline_ts.set_environment()


def apply_test_labels_logs(body, _ctx):
    ContextFactory.add_labels(
        key="labels@local-yw-clients-tests", labels={body["file"], body["testName"]}
    )
    return {}


def retrieve_logs(body, context: Context):
    logger = cast(InMemoryReporter, context.logs_reporters[0])
    root_logs, nodes_logs, leaf_logs, errors = (
        logger.root_node_logs,
        logger.node_logs,
        logger.leaf_logs,
        logger.errors,
    )

    test_name = body["testName"]
    file_name = body["file"]
    nodes: list[Log] = [
        NodeLogResponse(
            **Log.from_log_entry(log).dict(), failed=log.context_id in errors
        )
        for log in root_logs + nodes_logs
        if test_name in log.labels and file_name in log.labels
    ]
    leafs: list[Log] = [
        LeafLogResponse(**Log.from_log_entry(log).dict())
        for log in leaf_logs
        if test_name in log.labels and file_name in log.labels
    ]

    return {
        "nodes": sorted(nodes, key=lambda n: n.timestamp),
        "leafs": sorted(leafs, key=lambda n: n.timestamp),
    }


async def test_command_post(body, context: Context):
    await context.info(text="test message", data={"body": body})
    return body["returnObject"]


async def encode_extra_index(body, context: Context):
    await context.info(text="encode_extra_index", data={"body": body})
    return await encode_index(documents=body, context=context)


class BrotliDecompressMiddleware(CustomMiddleware):
    async def dispatch(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ):
        async with context.start(
            action="BrotliDecompressMiddleware.dispatch", with_labels=[Label.MIDDLEWARE]
        ) as ctx:  # type: Context
            response = await call_next(incoming_request)
            if response.headers.get("content-encoding") != "br":
                return response
            await ctx.info(
                text="Got 'br' content-encoding => apply brotli decompression"
            )
            await context.info("Apply brotli decompression")
            binary = b""
            # noinspection PyUnresolvedReferences
            async for data in response.body_iterator:
                binary += data
            headers = {
                k: v
                for k, v in response.headers.items()
                if k not in ["content-length", "content-encoding"]
            }
            decompressed = brotli.decompress(binary)
            resp = Response(decompressed.decode("utf8"), headers=headers)
            return resp


class ConfigurationFactory(IConfigurationFactory):
    async def get(self, _main_args: MainArguments) -> Configuration:

        return Configuration(
            system=System(
                httpPort=2001,
                tokensStorage=TokensStorageInMemory(),
                cloudEnvironments=CloudEnvironments(
                    defaultConnection=Connection(
                        envId="prod", authId=direct_auths[0].authId
                    ),
                    environments=[cloud_env],
                ),
                localEnvironment=LocalEnvironment(
                    dataDir=databases_folder,
                    cacheDir=system_folder,
                ),
            ),
            projects=Projects(
                finder=ProjectsFinder(
                    fromPath=projects_folder, lookUpDepth=2, watch=True
                ),
                templates=[
                    lib_ts_webpack_template(folder=projects_folder),
                    app_ts_webpack_template(folder=projects_folder),
                ],
            ),
            customization=Customization(
                middlewares=[
                    FlowSwitcherMiddleware(
                        name="CDN live servers",
                        oneOf=[CdnSwitch(packageName="package-name", port=3006)],
                    ),
                    BrotliDecompressMiddleware(),
                ],
                endPoints=CustomEndPoints(
                    commands=[
                        Command(name="reset", do_get=reset),
                        Command(
                            name="clone-project",
                            do_post=lambda body, ctx: clone_project(
                                body["url"], body["branch"], body["name"], ctx
                            ),
                        ),
                        Command(
                            name="purge-downloads",
                            do_delete=purge_downloads,
                        ),
                        Command(
                            name="create-test-data-remote",
                            do_get=create_test_data_remote,
                        ),
                        Command(
                            name="erase_all_test_data_remote",
                            do_delete=erase_all_test_data_remote,
                        ),
                        Command(
                            name="test-cmd-post",
                            do_post=test_command_post,
                        ),
                        Command(
                            name="test-cmd-put",
                            do_put=lambda body, ctx: body["returnObject"],
                        ),
                        Command(
                            name="test-cmd-delete",
                            do_delete=lambda ctx: {"status": "deleted"},
                        ),
                        Command(
                            name="get-logs",
                            do_post=retrieve_logs,
                        ),
                        Command(
                            name="set-jest-context",
                            do_post=apply_test_labels_logs,
                        ),
                        Command(
                            name="encode-extra-index",
                            do_post=encode_extra_index,
                        ),
                        Command(
                            name="exec-shell",
                            do_post=lambda body, ctx: exec_shell(body["command"], ctx),
                        ),
                    ]
                ),
            ),
        )
