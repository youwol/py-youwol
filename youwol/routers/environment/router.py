import asyncio
import itertools
import random
from typing import List, Optional

import importlib_resources
from cowpy import cow
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from starlette.requests import Request

from youwol.environment import FlowSwitcherMiddleware, yw_config, YouwolEnvironment, \
    YouwolEnvironmentFactory, Connection, DirectAuth
from youwol.middlewares import JwtProviderPyYouwol
from youwol.routers.environment.models import LoginBody, RemoteGatewayInfo, CustomDispatchesResponse, UserInfo
from youwol.routers.environment.upload_assets.upload import upload_asset
from youwol.routers.projects import ProjectLoader
from youwol.web_socket import LogsStreamer
from youwol_utils import to_json
from youwol_utils.clients.oidc.oidc_config import OidcConfig
from youwol_utils.context import Context

router = APIRouter()
flatten = itertools.chain.from_iterable


class EnvironmentStatusResponse(BaseModel):
    configuration: YouwolEnvironment
    users: List[str]
    userInfo: UserInfo
    remoteGatewayInfo: Optional[RemoteGatewayInfo]
    remotesInfo: List[RemoteGatewayInfo]


@router.get("/cow-say",
            response_class=PlainTextResponse,
            summary="status")
async def cow_say():
    #  https://github.com/bmc/fortunes/
    quotes = importlib_resources.files().joinpath('fortunes.txt').read_text().split("%")
    return cow.milk_random_cow(random.choice(quotes))


@router.get("/configuration",
            response_model=YouwolEnvironment,
            summary="configuration")
async def configuration(
        config: YouwolEnvironment = Depends(yw_config)
):
    return config


@router.post("/configuration",
             summary="reload configuration")
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


@router.get("/configuration/config-file",
            response_class=PlainTextResponse,
            summary="text content of the configuration file")
async def file_content(
        config: YouwolEnvironment = Depends(yw_config)
):
    return config.pathsBook.config.read_text()


@router.get("/configurations/predefined/{rest_of_path:path}",
            summary="load a predefined configuration file")
async def load_predefined_config_file(
        request: Request,
        rest_of_path: str
):
    async with Context.start_ep(
            request=request,
            with_reporters=[LogsStreamer()],
    ):
        from youwol.environment import predefined_configs
        source = importlib_resources.files(predefined_configs).joinpath(rest_of_path)
        with importlib_resources.as_file(source) as path:
            env = await YouwolEnvironmentFactory.load_from_file(path)
            asyncio.ensure_future(ProjectLoader.initialize(env=env))
            return await status(request, env)


@router.get("/status",
            summary="status")
async def status(
        request: Request,
        config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
            request=request,
            with_reporters=[LogsStreamer()],
    ) as ctx:  # type: Context
        remote_gateway_info = config.get_remote_info()
        if remote_gateway_info:
            remote_gateway_info = RemoteGatewayInfo(host=remote_gateway_info.host, connected=True)
        data = request.state.user_info
        users = [auth.userName for auth in config.get_remote_info().authentications if isinstance(auth, DirectAuth)]
        response = EnvironmentStatusResponse(
            users=users,
            userInfo=(UserInfo(id=data["upn"], name=data["username"], email=data["email"], memberOf=[])),
            configuration=config,
            remoteGatewayInfo=remote_gateway_info,
            remotesInfo=[
                RemoteGatewayInfo(host=remote.host, connected=(remote.host == config.get_remote_info().host))
                for remote in config.remotes
            ]
        )
        # disable projects loading for now
        # await ctx.send(ProjectsLoadingResults(results=await ProjectLoader.get_results(config, ctx)))
        await ctx.send(response)
        # Returning 'response' instead 'to_json(response)' (along with 'response_model=EnvironmentStatusResponse')
        # lead to missing fields (e.g. some middlewares). Not sure what the problem is.
        return to_json(response)


@router.get("/configuration/custom-dispatches",
            response_model=CustomDispatchesResponse,
            summary="list custom dispatches")
async def custom_dispatches(
        request: Request,
        config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
            request=request,
            with_reporters=[LogsStreamer()],
    ):
        flow_switches = [(switcher.name, switch) for switcher in config.customMiddlewares
                         if isinstance(switcher, FlowSwitcherMiddleware) for switch in switcher.oneOf]

        infos = await asyncio.gather(*[f.info() for _, f in flow_switches])
        dispatches = zip([f[0] for f in flow_switches], infos)
        grouped = itertools.groupby(sorted(dispatches, key=lambda d: d[0]), key=lambda d: d[0])
        dispatches = {k: [item[1] for item in items] for k, items in grouped}

        return CustomDispatchesResponse(dispatches=dispatches)


@router.post("/login",
             summary="log in as specified user")
async def login(
        request: Request,
        body: LoginBody
):
    async with Context.from_request(request).start(action="login") as ctx:
        # Need to check validity of combination envId, authId
        # What happen if switch from 'DirectAuth' to 'BrowserAuth', following code will not work,
        # should a somehow a redirect takes place?
        env = await YouwolEnvironmentFactory.reload(Connection(authId=body.authId, envId=body.envId))
        await status(request, env)
        auth_provider = env.get_remote_info().authProvider
        auth_token = await JwtProviderPyYouwol.get_auth_token(
            auth_provider=auth_provider,
            authentication=env.get_authentication_info(),
            context=ctx
        )
        data = await OidcConfig(auth_provider.openidBaseUrl).token_decode(auth_token)
        return UserInfo(id=data["upn"], name=data["username"], email=data["email"], memberOf=[])


@router.post("/upload/{asset_id}",
             summary="upload an asset")
async def upload(
        request: Request,
        asset_id: str,
        config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
            request=request,
            with_attributes={
                'asset_id': asset_id
            },
            with_reporters=[LogsStreamer()]
    ) as ctx:
        return await upload_asset(remote_host=config.get_remote_info().host, asset_id=asset_id, options=None,
                                  context=ctx)
