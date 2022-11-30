from pathlib import Path
import socket
from typing import Union, Callable, Awaitable, Any, Dict, Tuple

from youwol.environment.paths import PathsBook
from youwol.environment.models.defaults import default_path_cache_dir, default_path_data_dir, default_http_port, \
    default_path_projects_dir, default_platform_host, default_auth_provider
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
    """
Gather the list of events on which user actions can be performed.

**Attributes**:

*  **onLoad** (:class:`Context`) => :class:`Any` or :class:`Awaitable[Any]`
Action when configuration is loaded.
"""
    onLoad: Callable[[Context], Optional[Union[Any, Awaitable[Any]]]] = None


ConfigPath = Union[str, Path]


class UploadTarget(BaseModel):
    """
Upload target are used when configuring Pipeline, see dedicated documentation of the pipeline.
Pipelines can define some required upload targets by sub-classing this class.

**Attributes**:

*  **name** list of :class:`str`
Name of the target.
"""
    name: str


class UploadTargets(BaseModel):
    """
Upload targets are used when configuring Pipeline, see dedicated documentation of the pipeline.

**Attributes**:

*  **targets** list of :class:`UploadTarget`
Gather :class:`UploadTarget` targets of similar king (e.g. multiple docker registries, multiple remote CDN )

"""

    targets: List[UploadTarget]


class ProjectTemplate(BaseModel):
    """
Definition of a template that create an initial project folder that can be built & published.
Usually they come from python packages formalizing a particular type of project based on a particular stack.

See for instance 'lib_ts_webpack_template' and 'app_ts_webpack_template' generators.

**Attributes**:

*  **icon** :class:`JSON`
A json DOM representation of the icon for the template. See the library '@youwol/flux-view'.

*  **type**  :class:`str`
A unique type id that represent the type of the project.

*  **folder**  :class:`str`
Where the created project folders will be located.

*  **parameters**  :class:`Dict[str, str]`
A dictionary *'parameter name'* -> *'parameter default value'* defining the parameters the user will have to supply
to create the template.

*  **generators** (:class:`Path`, :class:`Dict[str, str]`, class:`Context`) => ( :class:`str`,  :class:`Path`)

The generator called to create the template project, arguments are:

1 - First argument is the folder's path in which the project needs to be created (parent folder of the created project).

2 - Second argument is the value of the parameters the user supplied.

3 - Third argument is the context.

Return the project's name and its path.
"""
    icon: Any
    type: str
    folder: Union[str, Path]
    parameters: Dict[str, str]
    generator: Callable[[Path, Dict[str, str], Context], Awaitable[Tuple[str, Path]]]


class Projects(BaseModel):
    """
Specification of projects to contribute to the YouWol's ecosystem.

Attributes:

- **finder** either (all path are absolute):

1 - :class:`ConfigPath`

Projects will be automatically discovered recursively from this path.

2 - list of :class:`ConfigPath`

Projects will be automatically discovered recursively from each of the provided path.

3 - Callable (:class:`PathsBook`, :class:`Context`) => list of  :class:`ConfigPath`

A function that returns the path of the projects.

4 - Callable (:class:`PathsBook`, :class:`Context`) => awaitable of list of  :class:`ConfigPath`

An awaitable function that returns the path of the projects.

*Default to ~/Projects*

- **templates** :class:`ProjectTemplate`
List of projects' template.

*Default to empty list*
    """
    finder: Union[
        ConfigPath,
        List[ConfigPath],
        Callable[[PathsBook, Context], List[ConfigPath]],
        Callable[[PathsBook, Context], Awaitable[List[ConfigPath]]]
    ] = Path.home() / default_path_projects_dir

    templates: List[ProjectTemplate] = []


class AuthorizationProvider(BaseModel):
    openidBaseUrl: str
    openidClient: Union[PublicClient, PrivateClient]
    keycloakAdminBaseUrl: str
    keycloakAdminClient: Optional[PrivateClient] = None


class Authentication(BaseModel):
    """
Virtual base class for authentication modes.

**Attributes**:

- **authId** :class:`string`
Unique id of the authentication for encapsulating :class:`CloudEnvironment`.
"""
    authId: str


class BrowserAuth(Authentication):
    """
Authentication using the browser using cookies: the browser automatically handle authentication (eventually redirecting
to the login page if needed).

  **Attributes**:

- **userName** :class:`string`
Credential's user-name

- **password** :class:`string`
Credential's password
    """
    pass


class DirectAuth(Authentication):
    """
Authentication using direct-flow.

    **Attributes**:

- **userName** :class:`string`
Credential's user-name

- **password** :class:`string`
Credential's password
    """
    userName: str
    password: str


class CloudEnvironment(BaseModel):
    """
Specification of a remote YouWol environment.

Attributes:

- **envId** :class:`string`
Unique id for this environment.

- **host** :class:`string`
host of the environment (e.g. platform.youwol.com).

- **authProvider** :class:`AuthorizationProvider`
Specification of the authorization provider

- **authentications** list of :class:`Authentication`
List of accepted authentications for the environment.
    """
    envId: str
    host: str
    authProvider: AuthorizationProvider
    authentications: List[Authentication]


class Connection(BaseModel):
    """
A connection is the association of an environment id and an authentication id.

Attributes:

- **envId** :class:`string`
Reference a :class:`CloudEnvironment`.envId

- **authId** :class:`string`
Reference a :class:`Authentication`.authId
    """
    envId: str
    authId: str


class CloudEnvironments(BaseModel):
    """
Cloud environments on which connection can be established.
At a particular time, py-youwol is connected to one cloud environment.
This is where missing data & libraries are retrieved.

    **Attributes**:

- **defaultConnection** :class:`Connection`

Connection used when py-youwol is started

- **environments** list of :class:`CloudEnvironment`

Available (YouWol) cloud environments with which py-youwol can connect.
    """
    defaultConnection: Connection
    environments: List[CloudEnvironment]


class LocalEnvironment(BaseModel):
    """
Local folders to store data. If paths are relatives, they are referenced with respect to the parent folder of the
configuration file.

**Attributes**:

- **dataDir** :class:`ConfigPath`
Defines folder location in which persisted data are saved.

*Default to './databases'*

- **cacheDir** :class:`ConfigPath`
Defines folder location of cached data.

*Default to './system'*
    """
    dataDir: ConfigPath = default_path_data_dir
    cacheDir: ConfigPath = default_path_cache_dir


class System(BaseModel):
    f"""
Specification of local & remote environments.

**Attributes**:

- **httpPort** :class:`int`
Local port on which py-youwol is served.

*optional, default to 2000*

- **cloudEnvironments** :class:`CloudEnvironments`
Specify remote environment(s) from where data can be collected.

*optional, default to the standard YouWol cloud environment with Browser based authentication*

- **localEnvironment** :class:`LocalEnvironment`
Specify how data are persisted in the computer.

*optional, default to LocalEnvironment()*
    """
    httpPort: Optional[int] = default_http_port
    cloudEnvironments: CloudEnvironments = CloudEnvironments(
        defaultConnection=Connection(envId='public-youwol', authId='browser'),
        environments=[
            CloudEnvironment(
                envId='public-youwol',
                host=default_platform_host,
                authProvider=AuthorizationProvider(**default_auth_provider()),
                authentications=[
                    BrowserAuth(authId="browser")
                ]
            )
        ]
    )
    localEnvironment: LocalEnvironment = LocalEnvironment()


class CustomEndPoints(BaseModel):
    """
Extends the environment by adding custom end-points.

**Attributes**:

- **commands** list of :class:`Command`
A list of commands that can be triggered via HTTP requests.

*Default to empty list*

- **routers** :class:`FastApiRouter`
Additional routers to bind to the environment.

*Default to empty list*
"""
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
    """
Summary of the state of a :class:`FlowSwitch` (used as displayed info).

**Attributes**:

- **name** :class:`str`
Name of the switch.

- **activated** :class:`bool`
Whether the switch is actually applicable or not (e.g. dev-server listening or not)

- **parameters** :class:`Dict[str, str]`
Some relevant parameters to display, dictionary 'parameter's name' -> 'value'

*Default to empty dict*
"""
    name: str
    activated: bool
    parameters: Dict[str, str] = {}


class FlowSwitch(BaseModel):
    """
Abstract class.

A FlowSwitch is used in :class:`FlowSwitcherMiddleware`, it provides the ability to interrupt the normal flow of
a request by redirecting it to another target end-point.

A typical example is when running a dev-server of a front app (:class:`CdnSwitch`). In this case a 'FlowSwitch'
can switch from the original target (underlying resource in the CDN database), to the running dev-server.

"""
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
    """
Given a list of :class:`FlowSwitch`, this middleware will eventually switch from the original targeted end-point
 to another one if one, and only one, :class:`FlowSwitch` element match the original request.

**Attributes**:

- **name** :class:`str`
Name of the middleware.

- **oneOf** list of :class:`FlowSwitch`
List of the :class:`FlowSwitch` elements.
"""
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
    """
CDN resource are stored in the CDN database: each time a related resource is queried, it is retrieved from here.
The class CdnSwitch can alter this behavior for a particular package, and serve the resources using a running
dev-server.

**Attributes**:

- **packageName** :class:`str`
Name of the targeted package.

- **port** :class:`int`
Listening port of the dev-server.
"""

    packageName: str
    port: int

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
    """
Redirect switch target requests with url that starts with a predefined 'origin', in this case the request is redirected
to a corresponding 'destination' (the rest of the path appended to it).

**Attributes**:

- **origin** :class:`str`
Origin base path targeted.

- **destination** :class:`int`
Corresponding destination
"""

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
    """
Exposes customization options.

**Attributes**:

- **endPoints** :class:`CustomEndPoints`
Allows adding custom end-points to the environment.

*Default to CustomEndPoints()*

- **middlewares** :class:`CustomMiddleware`
Allows adding custom middlewares to the environment.

*Default to empty list*

- **events** :class:`Events`
Allows defining actions to be triggered on specific events.

*Default to Events()*
    """
    endPoints: CustomEndPoints = CustomEndPoints()
    middlewares: Optional[List[CustomMiddleware]] = []
    events: Optional[Events] = Events()


class Configuration(BaseModel):
    """
Defines py-youwol running environment.

**Attributes**:

- **system** :class:`System`
Essentially about data, e.g. how they are retrieved & stored.

*Default to System()*

- **projects** :class:`Projects`
Defines projects that can be built & published in the youwol's ecosystem.

*Default to Projects()*

- **customization** :class:`Customization`
Various handles for customization (e.g. middleware, commands, ...)

*Default to Customization()*
    """

    system: System = System()
    projects: Projects = Projects()
    customization: Customization = Customization()


def is_localhost_ws_listening(port: int):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    location = ('localhost', port)
    return a_socket.connect_ex(location) == 0
