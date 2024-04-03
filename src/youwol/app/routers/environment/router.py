# standard library
import asyncio
import itertools
import random
import shutil
import tempfile

from importlib import resources
from pathlib import Path

# typing
from typing import Any, Literal, cast

# third parties
from aiohttp import ClientSession
from cowpy import cow
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from starlette.requests import Request

# Youwol application
from youwol.app.environment import (
    BrowserAuth,
    Command,
    Connection,
    DirectAuth,
    FlowSwitcherMiddleware,
    FwdArgumentsReload,
    NeedInteractiveSession,
    PathsBook,
    ProjectsResolver,
    RemoteClients,
    YouwolEnvironment,
    YouwolEnvironmentFactory,
    get_connected_local_tokens,
    yw_config,
)
from youwol.app.environment.models import predefined_configs
from youwol.app.environment.proxied_backends import ProxyInfo
from youwol.app.routers.local_cdn import emit_local_cdn_status
from youwol.app.routers.projects import ProjectLoader, emit_projects_status
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import OidcConfig
from youwol.utils.context import Context

# relative
from .models import (
    AuthenticationResponse,
    BrowserCacheStatusResponse,
    ClearBrowserCacheBody,
    ClearBrowserCacheResponse,
    CloudEnvironmentResponse,
    CustomDispatchesResponse,
    LoginBody,
    SwitchConfigurationBody,
    UserInfo,
)
from .upload_assets.upload import upload_asset

router = APIRouter()
flatten = itertools.chain.from_iterable


class YouwolEnvironmentResponse(BaseModel):
    """
    Response model corresponding to [YouwolEnvironment](@yw-nav-class:YouwolEnvironment).
    """

    httpPort: int
    """
    Serving port,
    see [YouwolEnvironment.httpPort](@yw-nav-attr:YouwolEnvironment.httPort).
    """
    customMiddlewares: list[dict[str, Any]]
    """
    Custom middlewares,
    see [YouwolEnvironment.customMiddlewares](@yw-nav-attr:YouwolEnvironment.customMiddlewares).
    """
    projects: ProjectsResolver
    """
    Projects resolver,
    see [YouwolEnvironment.projects](@yw-nav-attr:YouwolEnvironment.projects).
    """
    commands: dict[str, Command]
    """
    Commands list,
    see [YouwolEnvironment.commands](@yw-nav-attr:YouwolEnvironment.commands).
    """
    currentConnection: Connection
    """
    Current connection,
    see [YouwolEnvironment.currentConnection](@yw-nav-attr:YouwolEnvironment.currentConnection).
    """
    pathsBook: PathsBook
    """
    List of predefined paths related to the configuration,
    see [YouwolEnvironment.pathsBook](@yw-nav-attr:YouwolEnvironment.pathsBook).
    """
    proxiedBackends: list[ProxyInfo]
    """
    List of proxied backends,
    see [YouwolEnvironment.proxiedBackends](@yw-nav-attr:YouwolEnvironment.proxiedBackends).
    """
    remotes: list[CloudEnvironmentResponse]
    """
    List of available remotes environment,
    see [YouwolEnvironment.remotes](@yw-nav-attr:YouwolEnvironment.remotes).
    """

    @staticmethod
    def from_yw_environment(yw_env: YouwolEnvironment):
        """
        Converter from [YouwolEnvironment](@yw-nav-class:YouwolEnvironment) instance.

        Parameters:
            yw_env: Instance to serialize.

        Return:
             Serialized `yw_env`.
        """
        proxied_backends = [
            ProxyInfo(
                name=proxy.name,
                version=proxy.version,
                port=proxy.port,
                pid=proxy.process and proxy.process.pid,
            )
            for proxy in yw_env.proxied_backends.store
        ]
        remotes = [
            CloudEnvironmentResponse(
                envId=remote.envId,
                host=remote.host,
                authentications=[
                    AuthenticationResponse(
                        authId=auth.authId,
                        type=cast(
                            Literal["BrowserAuth", "DirectAuth"],
                            (
                                "BrowserAuth"
                                if isinstance(auth, BrowserAuth)
                                else "DirectAuth"
                            ),
                        ),
                    )
                    for auth in remote.authentications
                ],
            )
            for remote in yw_env.remotes
        ]

        return YouwolEnvironmentResponse(
            httpPort=yw_env.httpPort,
            customMiddlewares=[m.dict() for m in yw_env.customMiddlewares],
            projects=yw_env.projects,
            commands=yw_env.commands,
            currentConnection=yw_env.currentConnection,
            pathsBook=yw_env.pathsBook,
            proxiedBackends=proxied_backends,
            remotes=remotes,
        )


class EnvironmentStatusResponse(BaseModel):
    """
    Response when calling [`/admin/environment/status`](@yw-nav-func:environment.router.status).
    """

    configuration: YouwolEnvironmentResponse
    """
    Deprecated, use attribute [youwolEnvironment](@yw-nav-attr:EnvironmentStatusResponse.youwolEnvironment).

    Warning:
        Deprecated in 0.1.9
    """

    youwolEnvironment: YouwolEnvironmentResponse
    """
    Serialization of [YouwolEnvironment](@yw-nav-class:YouwolEnvironment), it essentially reflects the provided
    [Configuration](@yw-nav-class:models_config.Configuration).
    """

    users: list[str]
    """
    Deprecated, user information can be retrieved from attribute
     [youwolEnvironment](@yw-nav-attr:EnvironmentStatusResponse.youwolEnvironment).

    Warning:
        Deprecated in 0.1.9
    """

    userInfo: UserInfo
    """
    Deprecated, user information should be retrieved from attribute
     [youwolEnvironment](@yw-nav-attr:EnvironmentStatusResponse.youwolEnvironment).

    Warning:
        Deprecated in 0.1.9
    """

    remoteGatewayInfo: CloudEnvironmentResponse | None
    """
    Deprecated, remotes information should be retrieved from attribute
     [youwolEnvironment](@yw-nav-attr:EnvironmentStatusResponse.youwolEnvironment).

    Warning:
        Deprecated in 0.1.9
    """

    remotesInfo: list[CloudEnvironmentResponse]
    """
    Deprecated, remotes information should be retrieved from attribute
     [youwolEnvironment](@yw-nav-attr:EnvironmentStatusResponse.youwolEnvironment).

    Warning:
        Deprecated in 0.1.9
    """


async def on_env_changed(
    env: YouwolEnvironment, context: Context
) -> EnvironmentStatusResponse:
    await ProjectLoader.initialize(env=env)
    env_status, _, _ = await asyncio.gather(
        emit_environment_status(context=context),
        emit_local_cdn_status(context=context),
        emit_projects_status(context=context),
    )
    return env_status


@router.get("/cow-say", response_class=PlainTextResponse, summary="status")
async def cow_say():
    #  https://github.com/bmc/fortunes/
    quotes = (
        resources.files(__package__)
        .joinpath("fortunes.txt")
        .read_text(encoding="UTF-8")
        .split("%")
    )
    return cow.milk_random_cow(random.choice(quotes))


@router.get(
    "/configuration",
    response_model=YouwolEnvironmentResponse,
    summary="Return the running environment.",
)
async def configuration(
    config: YouwolEnvironment = Depends(yw_config),
) -> YouwolEnvironmentResponse:
    """
    Return the running environment.

    Parameters:
        config: Actual environment - automatically injected.

    Return:
        The environment.
    """
    return YouwolEnvironmentResponse.from_yw_environment(config)


@router.post(
    "/configuration",
    response_model=EnvironmentStatusResponse,
    summary="Trigger reload of the configuration.",
)
async def reload_configuration(
    request: Request,
) -> EnvironmentStatusResponse:
    """
    Trigger reload of the configuration.

    Loaded projects are re-initialized asynchronously, related status is sent via the data web-socket

    Parameters:
        request: Incoming request.

    Return:
        The environment status.
    """
    async with Context.start_ep(
        request=request,
        with_reporters=[LogsStreamer()],
    ) as ctx:
        env = await YouwolEnvironmentFactory.reload()
        return await on_env_changed(env=env, context=ctx)


@router.get(
    "/configuration/config-file",
    response_class=PlainTextResponse,
    summary="text content of the configuration file",
)
async def file_content(config: YouwolEnvironment = Depends(yw_config)):
    return config.pathsBook.config.read_text()


@router.get(
    "/configurations/predefined/{rest_of_path:path}",
    summary="load a predefined configuration file",
)
async def load_predefined_config_file(request: Request, rest_of_path: str):
    async with Context.start_ep(
        request=request,
        with_reporters=[LogsStreamer()],
    ) as ctx:
        source = resources.files(predefined_configs).joinpath(rest_of_path)
        with resources.as_file(source) as path:
            env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
            env = await YouwolEnvironmentFactory.load_from_file(
                path=path,
                fwd_args_reload=FwdArgumentsReload(
                    token_storage=env.tokens_storage, http_port=env.httpPort
                ),
            )
            return await on_env_changed(env=env, context=ctx)


@router.post(
    "/configurations/switch",
    summary="Switch to a new configuration from a URL pointing to its content.",
)
async def switch_configuration(
    request: Request, body: SwitchConfigurationBody
) -> EnvironmentStatusResponse:
    """
    Switch to a new configuration from a URL pointing to its content.

    Warning:
        There are few limitations for now regarding the flexibility to switch configuration:
          *  The url should point to a 'standalone' configuration: no external symbols (beyond those available in the
          youwol's python environment) can be referenced.
          *  The new configuration is not able to change the serving HTTP port of youwol.
          *  Switch involving change in remote host using
           [browser based authentication](@yw-nav-class:model_remote.BrowserAuth) may not necessarily work. To function,
           a session ID corresponding to the new targeted host should be available in the
           [TokensStorage](@yw-nav-class:TokensStorage).
          *  [Custom Middlewares](@yw-nav-class:models_config.CustomMiddleware) changes are not effective.

    Parameters:
        request: Incoming request.
        body: Specifies the new configuration to switch to, essentially an URL pointing to the content of the new
        configuration file.

    Return:
        The environment status.
    """
    async with Context.start_ep(
        request=request,
        with_reporters=[LogsStreamer()],
    ) as ctx:
        tmp_folder = Path(tempfile.gettempdir()) / "youwol" / "tmp_configs"
        shutil.rmtree(tmp_folder, ignore_errors=True)
        tmp_folder.mkdir(parents=True, exist_ok=True)
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        async with ClientSession(
            headers=ctx.headers(), cookies=ctx.cookies()
        ) as client:
            async with client.get(
                url=f"http://localhost:{env.httpPort}{body.url}"
            ) as resp:
                content = await resp.text()
                path = tmp_folder / body.url.split("/")[-1]
                path.write_text(content)
                env = await YouwolEnvironmentFactory.load_from_file(
                    path,
                    fwd_args_reload=FwdArgumentsReload(
                        token_storage=env.tokens_storage, http_port=env.httpPort
                    ),
                )

                return await on_env_changed(env=env, context=ctx)


async def emit_environment_status(context: Context) -> EnvironmentStatusResponse:
    """
    Emit the current [environment](@yw-nav-class:EnvironmentStatusResponse) via the
    [data web-socket channels](@yw-nav-attr:WebSocketsStore.data).

    Parameters:
        context: Current context.

    Return:
        The current environment.
    """

    async with context.start(
        action="emit_environment_status", with_reporters=[LogsStreamer()]
    ) as ctx:

        env = await ctx.get("env", YouwolEnvironment)

        data = ctx.request.state.user_info
        users = [
            auth.userName
            for auth in env.get_remote_info().authentications
            if isinstance(auth, DirectAuth)
        ]
        conf_response = YouwolEnvironmentResponse.from_yw_environment(env)
        youwol_env = YouwolEnvironmentResponse.from_yw_environment(env)
        response = EnvironmentStatusResponse(
            users=users,
            userInfo=(
                UserInfo(
                    id=data["sub"],
                    # Does not make sense, see comments on UserInfo
                    name=data["email"],
                    email=data["email"],
                    # Does not make sense, see comments on UserInfo
                    memberOf=[],
                )
            ),
            configuration=youwol_env,
            youwolEnvironment=youwol_env,
            remoteGatewayInfo=next(
                r
                for r in conf_response.remotes
                if r.envId == conf_response.currentConnection.envId
            ),
            remotesInfo=conf_response.remotes,
        )
        # disable projects loading for now
        # await ctx.send(ProjectsLoadingResults(results=await ProjectLoader.get_results(config, ctx)))
        await ctx.send(response)
        return response


@router.get("/status", summary="status")
async def status(request: Request) -> EnvironmentStatusResponse:
    """
    Return  the current environment and emit it using the [data web-socket channels](@yw-nav-attr:WebSocketsStore.data).

    Parameters:
        request: Incoming request.

    Return:
        The current environment.
    """
    async with Context.start_ep(
        request=request,
        with_reporters=[LogsStreamer()],
    ) as ctx:
        return await emit_environment_status(context=ctx)


@router.get(
    "/configuration/custom-dispatches",
    response_model=CustomDispatchesResponse,
    summary="list custom dispatches",
)
async def custom_dispatches(
    request: Request, config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
        request=request,
        with_reporters=[LogsStreamer()],
    ):
        flow_switches = [
            (switcher.name, switch)
            for switcher in config.customMiddlewares
            if isinstance(switcher, FlowSwitcherMiddleware)
            for switch in switcher.oneOf
        ]

        infos = await asyncio.gather(*[f.info() for _, f in flow_switches])
        dispatches = zip([f[0] for f in flow_switches], infos)
        grouped = itertools.groupby(
            sorted(dispatches, key=lambda d: d[0]), key=lambda d: d[0]
        )
        dispatches = {k: [item[1] for item in items] for k, items in grouped}

        return CustomDispatchesResponse(dispatches=dispatches)


@router.post(
    "/login",
    response_model=UserInfo,
    summary="Login to a particular environment using a specific authentication mode.",
)
async def login(request: Request, body: LoginBody) -> UserInfo:
    """
    Login to a particular environment using a specific authentication mode (referenced
    from the configuration's models [CloudEnvironment](@yw-nav-class:CloudEnvironment)).

    Parameters:
        request: Incoming request.
        body: Login body.

    Return:
        User info of logged-in user.

    Raise:
        422: When a browser interactive session is needed but not available.
    """

    async with Context.from_request(request).start(action="login") as ctx:
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        actual_connection = env.currentConnection
        env = await YouwolEnvironmentFactory.reload(
            Connection(authId=body.authId, envId=body.envId)
        )
        try:
            tokens = await get_connected_local_tokens(context=ctx)
        except NeedInteractiveSession:
            await YouwolEnvironmentFactory.reload(actual_connection)
            raise HTTPException(
                status_code=422,
                detail=f"Need a browser interactive session for env '{body.envId}' that is not available in "
                f"tokens storage.",
            )
        access_token = await tokens.access_token()
        access_token_decoded = await OidcConfig(
            env.get_remote_info().authProvider.openidBaseUrl
        ).token_decode(access_token)

        await emit_environment_status(context=ctx)

        return UserInfo(
            id=access_token_decoded["sub"],
            # Does not make sense, see comments on UserInfo
            name=access_token_decoded["email"],
            email=access_token_decoded["email"],
            # Does not make sense, see comments on UserInfo
            memberOf=[],
        )


@router.post("/upload/{asset_id}", summary="upload an asset")
async def upload(
    request: Request, asset_id: str, config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
        request=request,
        with_attributes={"asset_id": asset_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        return await upload_asset(
            remote_assets_gtw=await RemoteClients.get_twin_assets_gateway_client(
                env=config
            ),
            asset_id=asset_id,
            options=None,
            context=ctx,
        )


@router.get(
    "/browser-cache",
    summary="upload an asset",
    response_model=BrowserCacheStatusResponse,
)
async def browser_cache_status(
    request: Request, env: YouwolEnvironment = Depends(yw_config)
) -> BrowserCacheStatusResponse:
    """
    Retrieves status of the [BrowserCacheStore](@yw-nav-class:BrowserCacheStore).

    Parameters:
        request: Incoming request.
        env: Current environment (automatically injected).

    Return:
        Info regarding the current state of the browser's cache of YouWol.
    """

    async with Context.start_ep(
        request=request,
    ):
        return BrowserCacheStatusResponse(
            sessionKey=env.browserCacheStore.session_key(),
            file=str(env.browserCacheStore.output_file_path()),
            items=env.browserCacheStore.items(),
        )


@router.delete(
    "/browser-cache",
    summary="upload an asset",
    response_model=ClearBrowserCacheResponse,
)
async def clear_browser_cache(
    request: Request,
    body: ClearBrowserCacheBody,
    env: YouwolEnvironment = Depends(yw_config),
) -> ClearBrowserCacheResponse:
    """
    Clear the [BrowserCacheStore](@yw-nav-class:BrowserCacheStore).

    Parameters:
        request: Incoming request.
        body: Options.
        env: Current environment (automatically injected).

    Return:
        Info regarding the current state of the browser's cache of YouWol.
    """

    async with Context.start_ep(
        request=request,
    ) as ctx:
        count = await env.browserCacheStore.clear(
            memory=body.memory, file=body.file, context=ctx
        )
        return ClearBrowserCacheResponse(deleted=count)
