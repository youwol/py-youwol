# standard library
import asyncio
import itertools
import random

from importlib import resources

# typing
from typing import Dict, List, Optional

# third parties
from cowpy import cow
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from starlette.requests import Request

# Youwol application
from youwol.app.environment import (
    Command,
    Connection,
    CustomMiddleware,
    DirectAuth,
    FlowSwitcherMiddleware,
    FwdArgumentsReload,
    PathsBook,
    Projects,
    YouwolEnvironment,
    YouwolEnvironmentFactory,
    yw_config,
)
from youwol.app.environment.models import predefined_configs
from youwol.app.middlewares import get_connected_local_tokens
from youwol.app.routers.projects import ProjectLoader
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils.clients.oidc.oidc_config import OidcConfig
from youwol.utils.context import Context

# relative
from .models import CustomDispatchesResponse, LoginBody, RemoteGatewayInfo, UserInfo
from .upload_assets.upload import upload_asset

router = APIRouter()
flatten = itertools.chain.from_iterable


class ConfigurationResponse(BaseModel):
    httpPort: int
    customMiddlewares: List[CustomMiddleware]
    projects: Projects
    commands: Dict[str, Command]
    currentConnection: Connection
    pathsBook: PathsBook


class EnvironmentStatusResponse(BaseModel):
    configuration: ConfigurationResponse
    users: List[str]
    userInfo: UserInfo
    remoteGatewayInfo: Optional[RemoteGatewayInfo]
    remotesInfo: List[RemoteGatewayInfo]


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


@router.get("/configuration", response_model=YouwolEnvironment, summary="configuration")
async def configuration(config: YouwolEnvironment = Depends(yw_config)):
    return config


@router.post("/configuration", summary="reload configuration")
async def reload_configuration(
    request: Request,
):
    async with Context.start_ep(
        request=request,
        with_reporters=[LogsStreamer()],
    ):
        env = await YouwolEnvironmentFactory.reload()
        asyncio.ensure_future(ProjectLoader.initialize(env=env))
        return await status(request, env)


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
                fwd_args_reload=FwdArgumentsReload(token_storage=env.tokens_storage),
            )
            asyncio.ensure_future(ProjectLoader.initialize(env=env))
            return await status(request, env)


@router.get("/status", summary="status")
async def status(request: Request, config: YouwolEnvironment = Depends(yw_config)):
    async with Context.start_ep(
        request=request,
        with_reporters=[LogsStreamer()],
    ) as ctx:  # type: Context
        remote_gateway_info = config.get_remote_info()
        if remote_gateway_info:
            remote_gateway_info = RemoteGatewayInfo(
                host=remote_gateway_info.host, connected=True
            )
        data = request.state.user_info
        users = [
            auth.userName
            for auth in config.get_remote_info().authentications
            if isinstance(auth, DirectAuth)
        ]
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
            configuration=ConfigurationResponse(**config.dict()),
            remoteGatewayInfo=remote_gateway_info,
            remotesInfo=[
                RemoteGatewayInfo(
                    host=remote.host,
                    connected=(remote.host == config.get_remote_info().host),
                )
                for remote in config.remotes
            ],
        )
        # disable projects loading for now
        # await ctx.send(ProjectsLoadingResults(results=await ProjectLoader.get_results(config, ctx)))
        await ctx.send(response)
        return response


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


@router.post("/login", summary="log in as specified user")
async def login(request: Request, body: LoginBody):
    async with Context.from_request(request).start(action="login") as ctx:
        # Need to check validity of combination envId, authId
        # What happen if switch from 'DirectAuth' to 'BrowserAuth', following code will not work,
        # should a somehow a redirect takes place?
        env = await YouwolEnvironmentFactory.reload(
            Connection(authId=body.authId, envId=body.envId)
        )
        await status(request, env)
        tokens = await get_connected_local_tokens(context=ctx)
        access_token = await tokens.access_token()
        access_token_decoded = await OidcConfig(
            env.get_remote_info().authProvider.openidBaseUrl
        ).token_decode(access_token)
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
            remote_host=config.get_remote_info().host,
            asset_id=asset_id,
            options=None,
            context=ctx,
        )
