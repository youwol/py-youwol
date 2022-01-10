import itertools
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aiohttp.web import HTTPException
from aiohttp.client_exceptions import ClientConnectorError, ContentTypeError
from starlette.requests import Request

from youwol.environment.clients import RemoteClients
from youwol.environment.models import UserInfo
from youwol.environment.youwol_environment import yw_config, YouwolEnvironment, YouwolEnvironmentFactory
from youwol.models import Label
from youwol.context import Context

from youwol.utils_low_level import get_public_user_auth_token


from youwol.routers.environment.models import (
    SyncUserBody, LoginBody, RemoteGatewayInfo, SelectRemoteBody
)

from youwol.utils_paths import parse_json, write_json
from youwol.web_socket import WebSocketsCache
from youwol_utils import retrieve_user_info

router = APIRouter()
flatten = itertools.chain.from_iterable


class StatusResponse(BaseModel):
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
            labels=[Label.STATUS],
            text="Authorization: HTTP Error",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except ClientConnectorError as e:
        await context.info(
            labels=[Label.STATUS],
            text="Authorization: Connection error (internet on?)",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except RuntimeError as e:
        await context.info(
            labels=[Label.STATUS],
            text="Authorization error",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except ContentTypeError as e:
        await context.info(
            labels=[Label.STATUS],
            text="Failed to call healthz on assets-gateway",
            data={'host': remote_gateway_info.host, 'error': str(e)})
        return False


@router.get("/configuration",
            response_model=YouwolEnvironment,
            summary="configuration")
async def configuration(
        config: YouwolEnvironment = Depends(yw_config)
        ):
    return config


@router.get("/file-content",
            summary="text content of the configuration file")
async def file_content(
        config: YouwolEnvironment = Depends(yw_config)
        ):

    return {
        "content": config.pathsBook.config.read_text()
        }


@router.get("/status",
            response_model=StatusResponse,
            summary="status")
async def status(
        request: Request,
        config: YouwolEnvironment = Depends(yw_config)
        ):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.userChannel)
    response: Optional[StatusResponse] = None
    async with context.start(
            action="Get environment status",
            succeeded_data=lambda _ctx: ('EnvironmentStatusResponse', response)
            ) as _ctx:
        connected = await connect_to_remote(config=config, context=context)
        remote_gateway_info = config.get_remote_info()
        if remote_gateway_info:
            remote_gateway_info = RemoteGatewayInfo(name=remote_gateway_info.name,
                                                    host=remote_gateway_info.host,
                                                    connected=connected)
        remotes_info = parse_json(config.pathsBook.remotesInfo)['remotes'].values()
        response = StatusResponse(
            users=config.get_users_list(),
            userInfo=config.get_user_info(),
            configuration=config,
            remoteGatewayInfo=remote_gateway_info,
            remotesInfo=list(remotes_info)
            )
        return response


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

    context = Context(
        request=request,
        config=config,
        web_socket=WebSocketsCache.environment
        )
    async with context.start(f"Sync. user {body.email}") as ctx:

        try:
            auth_token = await get_public_user_auth_token(
                username=body.email,
                pwd=body.password,
                client_id=config.get_remote_info().metadata['keycloakClientId'],
                openid_host=config.openid_host
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

        user_info = await retrieve_user_info(auth_token=auth_token, openid_host=config.openid_host)

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
