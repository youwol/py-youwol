import itertools
import random
from pathlib import Path
from typing import List, Optional

from cowpy import cow
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from starlette.requests import Request

from youwol.environment.models import UserInfo
from youwol.environment.projects_loader import ProjectLoader
from youwol.environment.youwol_environment import yw_config, YouwolEnvironment, YouwolEnvironmentFactory
from youwol.routers.environment.models import (
    LoginBody, RemoteGatewayInfo, ProjectsLoadingResults,
    CustomDispatch, CustomDispatchesResponse
)
from youwol.routers.environment.upload_assets.upload import upload_asset
from youwol.web_socket import LogsStreamer
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
    quotes = (Path(__file__).parent / 'fortunes.txt').read_text().split("%")
    return cow.milk_random_cow(random.choice(quotes))


@router.get("/configuration",
            response_model=YouwolEnvironment,
            summary="configuration")
async def configuration(
        config: YouwolEnvironment = Depends(yw_config)
):
    return config


@router.post("/configuration",
             response_model=EnvironmentStatusResponse,
             summary="reload configuration")
async def reload_configuration(
        request: Request,
):
    env = await YouwolEnvironmentFactory.reload()
    return await status(request, env)


@router.get("/configuration/config-file",
            response_class=PlainTextResponse,
            summary="text content of the configuration file")
async def file_content(
        config: YouwolEnvironment = Depends(yw_config)
):
    return config.pathsBook.config.read_text()


@router.get("/status",
            summary="status",
            response_model=EnvironmentStatusResponse)
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
            remote_gateway_info = RemoteGatewayInfo(name=remote_gateway_info.name,
                                                    host=remote_gateway_info.host,
                                                    connected=True)
        data = request.state.user_info
        response = EnvironmentStatusResponse(
            users=config.get_users_list(),
            userInfo=(UserInfo(id=data["upn"], name=data["username"], email=data["email"], memberOf=[])),
            configuration=config,
            remoteGatewayInfo=remote_gateway_info,
            remotesInfo=[
                RemoteGatewayInfo(name=remote.name, host=remote.host, connected=(remote.host == config.selectedRemote))
                for remote in config.remotes
            ]
        )
        await ctx.send(response)
        await ctx.send(ProjectsLoadingResults(results=await ProjectLoader.get_results(config, ctx)))
        return response


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
        dispatches = [CustomDispatch(type=d.__class__.__name__, **(await d.info()).dict())
                      for d in config.customDispatches]

        def key_fct(d):
            return d.type

        grouped = itertools.groupby(sorted(dispatches, key=key_fct), key=key_fct)
        dispatches = {k: list(items) for k, items in grouped}
        return CustomDispatchesResponse(dispatches=dispatches)


@router.post("/login",
             summary="log in as specified user")
async def login(
        request: Request,
        body: LoginBody,
        config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.from_request(request).start(action="login") as ctx:
        await YouwolEnvironmentFactory.reload(selected_user=body.email, selected_remote=body.remote)
        conf = await yw_config()
        await status(request, conf)
        data = await OidcConfig(conf.get_remote_info().openidBaseUrl).token_decode(await conf.get_auth_token(ctx))
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
