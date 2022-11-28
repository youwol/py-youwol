from pathlib import Path
import socket
from typing import Union, Callable, Awaitable, Any, Dict, Tuple

from youwol.environment.paths import PathsBook
from youwol.environment.models.defaults import default_path_cache_dir, default_path_data_dir, default_http_port, \
    default_platform_host, default_cloud_environment
from youwol.environment.projects_finders import default_projects_finder
from youwol.routers.custom_commands.models import Command
from youwol_utils.clients.oidc.oidc_config import PublicClient, PrivateClient
from youwol_utils.servers.fast_api import FastApiRouter
from typing import List, Optional

from aiohttp import ClientSession
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol_utils.utils_requests import redirect_request
from youwol_utils import Context, encode_id, YouWolException, youwol_exception_handler, ResourcesNotFoundException
from youwol_utils.context import Label


class Events(BaseModel):
    onLoad: Callable[[Context], Optional[Union[Any, Awaitable[Any]]]] = None


ConfigPath = Union[str, Path]


class UploadTarget(BaseModel):
    name: str


class UploadTargets(BaseModel):
    targets: List[UploadTarget]


class ProjectTemplate(BaseModel):
    icon: Any
    type: str
    folder: Union[str, Path]
    parameters: Dict[str, str]
    generator: Callable[[Path, Dict[str, str], Context], Awaitable[Tuple[str, Path]]]


class Projects(BaseModel):
    finder: Union[
        ConfigPath,
        List[ConfigPath],
        Callable[[PathsBook, Context], List[ConfigPath]],
        Callable[[PathsBook, Context], Awaitable[List[ConfigPath]]]
    ] = lambda paths_book, _ctx: default_projects_finder(paths_book=paths_book)
    templates: List[ProjectTemplate] = []


class YouwolCloud(BaseModel):
    host: str
    name: str
    openidBaseUrl: str
    openidClient: Union[PublicClient, PrivateClient]
    keycloakAdminBaseUrl: str
    keycloakAdminClient: Optional[PrivateClient] = None


class RemoteConnection(BaseModel):
    host: str
    userId: Optional[str]


class BrowserAuthConnection(RemoteConnection):
    host: str


class ImpersonateAuthConnection(RemoteConnection):
    host: str
    userId: str


class Impersonation(BaseModel):
    userId: str
    userName: str
    password: str
    forHosts: List[str] = []


class CloudEnvironments(BaseModel):
    defaultConnection: RemoteConnection = BrowserAuthConnection(host=default_platform_host)
    environments: List[YouwolCloud] = []
    impersonations: List[Impersonation] = []


class LocalEnvironment(BaseModel):
    dataDir: Optional[ConfigPath] = default_path_data_dir
    cacheDir: Optional[ConfigPath] = default_path_cache_dir


class System(BaseModel):
    httpPort: Optional[int] = default_http_port
    cloudEnvironments: CloudEnvironments = CloudEnvironments(
        environments=[YouwolCloud(**default_cloud_environment(default_platform_host))]
    )
    localEnvironment: LocalEnvironment = LocalEnvironment()


class CustomEndPoints(BaseModel):
    commands: Optional[List[Command]] = []
    routers: Optional[List[FastApiRouter]] = []


class CustomMiddleware(BaseModel):

    async def dispatch(self,
                       incoming_request: Request,
                       call_next: RequestResponseEndpoint,
                       context: Context
                       ) -> Optional[Response]:
        raise NotImplementedError("CustomMiddleware.switch not implemented")


class DispatchInfo(BaseModel):
    name: str
    activated: Optional[bool]
    parameters: Optional[Dict[str, str]]


class FlowSwitch(BaseModel):

    async def info(self) -> DispatchInfo:
        return DispatchInfo(name=self.__str__(), activated=True,
                            parameters={"description": "no description provided ('info' method not overriden)"})

    async def is_matching(self, incoming_request: Request, context: Context) -> bool:
        raise NotImplementedError("FlowSwitchMiddleware.is_matching not implemented")

    async def switch(self,
                     incoming_request: Request,
                     context: Context
                     ) -> Optional[Response]:
        raise NotImplementedError("AbstractDispatch.switch not implemented")


class FlowSwitcherMiddleware(CustomMiddleware):

    name: str
    oneOf: List[FlowSwitch]

    async def dispatch(self,
                       incoming_request: Request,
                       call_next: RequestResponseEndpoint,
                       context: Context
                       ) -> Optional[Response]:

        async with context.start(
                action=f'FlowSwitcher: {self.name}',
                with_labels=[Label.MIDDLEWARE]
        ) as ctx:  # type: Context

            async with ctx.start(action=f"Get status of {len(self.oneOf)} switches"
                                 ) as ctx_status:  # type: Context
                matches = [d for d in self.oneOf if await d.is_matching(incoming_request=incoming_request,
                                                                        context=ctx_status)]
            if len(matches) > 1:
                raise RuntimeError("Multiple flow-switches match the incoming request")

            if not matches:
                await ctx.info(f"No match from the flow-switcher")
                return await call_next(incoming_request)

            try:
                response = await matches[0].switch(incoming_request=incoming_request, context=ctx)
            except YouWolException as e:
                return await youwol_exception_handler(incoming_request, e)

            await ctx.info(f"Got response from a flow-switcher")
            return response


class CdnSwitch(FlowSwitch):
    packageName: str
    port: Optional[int]

    async def info(self):
        return DispatchInfo(
            name=self.packageName,
            activated=is_localhost_ws_listening(self.port),
            parameters={
                'package': self.packageName,
                'redirected to':  f'localhost:{self.port}'
            })

    async def is_matching(self, incoming_request: Request, context: Context):
        if incoming_request.method != "GET":
            return False

        encoded_id = encode_id(self.packageName)

        if not (incoming_request.url.path.startswith(f"/api/assets-gateway/raw/package/{encoded_id}") or
                incoming_request.url.path.startswith(f"/api/cdn-backend/resources/{encoded_id}")):
            await context.info(text=f"CdnSwitch[{self}]: URL not matching",
                               data={"url": incoming_request.url.path, "encoded_id": encoded_id})
            return False

        if not is_localhost_ws_listening(self.port):
            await context.info(text=f"CdnSwitch[{self}]: ws not listening")
            return False

        await context.info(text=f"CdnSwitch[{self}]: MATCHING")
        return True

    async def switch(self,
                     incoming_request: Request,
                     context: Context) -> Optional[Response]:

        rest_of_path = incoming_request.url.path.split('/')[-1]
        url = f"http://localhost:{self.port}/{rest_of_path}"
        await context.info(text=f"CdnSwitch[{self}] execution",
                           data={"origin": incoming_request.url.path,
                                 "destination": url})

        async with ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url) as resp:
                if resp.status != 200:
                    await context.error(text=f"CdnSwitch[{self}]: \
                        Error status while dispatching", data={
                        "origin": incoming_request.url.path,
                        "destination": url,
                        "path": rest_of_path,
                        "status": resp.status
                    })
                    raise ResourcesNotFoundException(
                        path=rest_of_path,
                        detail=resp.reason
                    )
                content = await resp.read()
                return Response(content=content, headers={k: v for k, v in resp.headers.items()})

    def __str__(self):
        return f"serving cdn package '{self.packageName}' from local port '{self.port}'"


class RedirectSwitch(FlowSwitch):

    origin: str
    destination: str

    def is_listening(self):
        return is_localhost_ws_listening(int(self.destination.split(':')[-1]))

    async def info(self) -> DispatchInfo:
        return DispatchInfo(
            name=self.origin,
            activated=self.is_listening(),
            parameters={
                'from url': self.origin,
                'redirected to': self.destination
            })

    async def is_matching(self, incoming_request: Request, context: Context):

        if not incoming_request.url.path.startswith(self.origin):
            await context.info(text=f"RedirectSwitch[{self}]: URL not matching",
                               data={"url": incoming_request.url.path})
            return False

        if not self.is_listening():
            await context.info(f"RedirectSwitch[{self}]: destination not listening -> proceed with no dispatch")
            return False

        return True

    async def switch(self,
                     incoming_request: Request,
                     context: Context) -> Optional[Response]:

        headers = {
            **{k: v for k, v in incoming_request.headers.items()},
            **context.headers()
        }

        await context.info(text=f"RedirectSwitch[{self}] execution",
                           data={"origin": incoming_request.url.path,
                                 "destination": self.destination})

        resp = await redirect_request(
            incoming_request=incoming_request,
            origin_base_path=self.origin,
            destination_base_path=self.destination,
            headers=headers
        )
        await context.info(
            f"Got response from dispatch",
            data={
                "headers": {k: v for k, v in resp.headers.items()},
                "status": resp.status_code
            }
        )
        return resp

    def __str__(self):
        return f"redirecting '{self.origin}' to '{self.destination}'"


class Customization(BaseModel):
    endPoints: CustomEndPoints = CustomEndPoints()
    middlewares: Optional[List[CustomMiddleware]] = []
    events: Optional[Events] = Events()


class Configuration(BaseModel):
    system: Optional[System] = System()
    projects: Optional[Projects] = Projects()
    customization: Optional[Customization] = Customization()


def is_localhost_ws_listening(port: int):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    location = ('localhost', port)
    return a_socket.connect_ex(location) == 0
