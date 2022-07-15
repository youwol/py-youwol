import random
from pathlib import Path
from typing import List, Optional

import itertools
from aiohttp.client_exceptions import ClientConnectorError, ContentTypeError
from cowpy import cow
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from starlette.requests import Request

from youwol.environment.clients import RemoteClients
from youwol.environment.models import UserInfo
from youwol.environment.projects_loader import ProjectLoader
from youwol.environment.youwol_environment import yw_config, YouwolEnvironment, YouwolEnvironmentFactory
from youwol.routers.environment.models import (
    SyncUserBody, LoginBody, RemoteGatewayInfo, SelectRemoteBody, AvailableProfiles, ProjectsLoadingResults,
    CustomDispatch, CustomDispatchesResponse
)
from youwol.routers.environment.upload_assets.upload import upload_asset
from youwol.utils.utils_low_level import get_public_user_auth_token
from youwol.web_socket import LogsStreamer
from youwol_utils import retrieve_user_info
from youwol_utils.context import Context
from youwol_utils.utils_paths import parse_json, write_json

router = APIRouter()
flatten = itertools.chain.from_iterable


class EnvironmentStatusResponse(BaseModel):
    configuration: YouwolEnvironment
    users: List[str]
    userInfo: UserInfo
    remoteGatewayInfo: Optional[RemoteGatewayInfo]
    remotesInfo: List[RemoteGatewayInfo]


async def connect_to_remote(config: YouwolEnvironment, context: Context) -> bool:
    remote_gateway_info = config.get_remote_info()
    if not remote_gateway_info:
        return False

    try:
        await config.get_auth_token(context)
        client = await RemoteClients.get_assets_gateway_client(context)
        await client.healthz()
        return True
    except HTTPException as e:
        await context.info(
            text="Authorization: HTTP Error",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except ClientConnectorError as e:
        await context.info(
            text="Authorization: Connection error (internet on?)",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except RuntimeError as e:
        await context.info(
            text="Authorization error",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except ContentTypeError as e:
        await context.info(
            text="Failed to call healthz on assets-gateway",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False


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


@router.get("/configuration/profiles/",
            response_model=AvailableProfiles,
            summary="list available configuration profiles")
async def change_configuration_profile(
        config: YouwolEnvironment = Depends(yw_config)
):
    return AvailableProfiles(profiles=config.availableProfiles,
                             active=config.activeProfile)


@router.put("/configuration/profiles/active",
            response_model=EnvironmentStatusResponse,
            summary="change configuration profile")
async def change_configuration_profile(
        request: Request,
        body: AvailableProfiles,
        config: YouwolEnvironment = Depends(yw_config)
):
    profile = body.active
    if profile == config.activeProfile:
        raise HTTPException(status_code=409, detail=f"current configuration profile is already '{profile}'")
    if profile not in config.availableProfiles:
        raise HTTPException(status_code=404, detail=f"no configuration profile '{profile}'")

    env = await YouwolEnvironmentFactory.reload(profile)
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
            with_attributes={"profile": config.activeProfile or 'default'}
    ) as ctx:   # type: Context
        connected = await connect_to_remote(config=config, context=ctx)
        remote_gateway_info = config.get_remote_info()
        if remote_gateway_info:
            remote_gateway_info = RemoteGatewayInfo(name=remote_gateway_info.name,
                                                    host=remote_gateway_info.host,
                                                    connected=connected)
        remotes_info = parse_json(config.pathsBook.remotesInfo)['remotes'].values()
        response = EnvironmentStatusResponse(
            users=config.get_users_list(),
            userInfo=config.get_user_info(),
            configuration=config,
            remoteGatewayInfo=remote_gateway_info,
            remotesInfo=list(remotes_info)
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
    await YouwolEnvironmentFactory.login(email=body.email, remote_name=config.selectedRemote)
    new_conf = await yw_config()
    await status(request, new_conf)
    return new_conf.get_user_info()


@router.post("/select-remote-gateway",
             summary="select a remote")
async def select_remote(
        request: Request,
        body: SelectRemoteBody,
        config: YouwolEnvironment = Depends(yw_config)
):
    await YouwolEnvironmentFactory.login(email=config.userEmail, remote_name=body.name)
    new_conf = await yw_config()
    await status(request, new_conf)
    return new_conf.get_user_info()


@router.post("/sync-user",
             summary="sync a new local user w/ remote one")
async def sync_user(
        request: Request,
        body: SyncUserBody,
        config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
            request=request,
            with_reporters=[LogsStreamer()]
    ) as ctx:

        try:
            auth_token = await get_public_user_auth_token(
                username=body.email,
                pwd=body.password,
                client_id=config.get_remote_info().metadata['keycloakClientId'],
                openid_host=config.openidHost
            )
        except Exception:
            raise RuntimeError(f"Can not authorize from email/pwd @ {config.get_remote_info().host}")

        await ctx.info(text="Login successful")

        secrets = parse_json(config.pathsBook.secrets)
        if body.email in secrets:
            secrets[body.email] = {**secrets[body.email], **{"password": body.password}}
        else:
            secrets[body.email] = {"password": body.password}
        write_json(secrets, config.pathsBook.secrets)

        user_info = await retrieve_user_info(auth_token=auth_token, openid_host=config.openidHost)

        users_info = parse_json(config.pathsBook.usersInfo)
        users_info['users'][body.email] = {
            "id": user_info['sub'],
            "name": user_info['preferred_username'],
            "memberOf": user_info['memberof'],
            "email": user_info["email"]
        }
        write_json(users_info, config.pathsBook.usersInfo)
        await login(request=request, body=LoginBody(email=body.email), config=config)
        return users_info['users'][body.email]


@router.post("/upload/{asset_id}",
             summary="upload an asset")
async def upload(
        request: Request,
        asset_id: str
):
    async with Context.start_ep(
            request=request,
            with_attributes={
                'asset_id': asset_id
            },
            with_reporters=[LogsStreamer()]
    ) as ctx:
        return await upload_asset(asset_id=asset_id, options=None, context=ctx)
