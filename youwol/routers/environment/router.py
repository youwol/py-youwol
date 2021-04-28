import itertools

from fastapi import APIRouter, WebSocket, Depends
from aiohttp.web import HTTPException
from aiohttp.client_exceptions import ClientConnectorError, ContentTypeError
from starlette.requests import Request

from configuration import get_public_user_auth_token
from youwol.configuration import ErrorResponse
from youwol.configuration.youwol_configuration import YouwolConfiguration
from youwol.configuration.youwol_configuration import yw_config, YouwolConfigurationFactory, ConfigurationLoadingStatus
from youwol.context import Context, Action, ActionStep
from youwol.routers.environment.models import (
    StatusResponse, SwitchConfigurationBody, SyncUserBody, LoginBody,
    PostParametersBody, RemoteGatewayInfo, SelectRemoteBody,
    )
from youwol.utils_low_level import to_json
from youwol.utils_paths import parse_json, write_json
from youwol.web_socket import WebSocketsCache
from youwol_utils import retrieve_user_info

router = APIRouter()
flatten = itertools.chain.from_iterable


async def connect_to_remote(config: YouwolConfiguration, context: Context) -> bool:

    remote_gateway_info = config.get_remote_info()
    if not remote_gateway_info:
        return False

    try:
        await config.get_auth_token(context)
        client = await config.get_assets_gateway_client(context)
        await client.healthz()
        return True
    except HTTPException as e:
        await context.info(
            ActionStep.STATUS,
            "Authorization: HTTP Error",
            json={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except ClientConnectorError as e:
        await context.info(
            ActionStep.STATUS,
            "Authorization: Connection error (internet on?)",
            json={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except RuntimeError as e:
        await context.info(
            ActionStep.STATUS,
            "Authorization error",
            json={'host': remote_gateway_info.host, 'error': str(e)})
        return False
    except ContentTypeError as e:
        await context.info(
            ActionStep.STATUS,
            "Failed to call healthz on assets-gateway",
            json={'host': remote_gateway_info.host, 'error': str(e)})
        return False


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):

    YouwolConfigurationFactory.clear_cache()
    await ws.accept()
    WebSocketsCache.environment = ws
    await ws.send_json({})

    load_status = await YouwolConfigurationFactory.reload()
    if not load_status.validated:
        config = await yw_config()
        context = Context(config=config, web_socket=WebSocketsCache.environment)
        first_error = next(c for c in load_status.checks if isinstance(c.status, ErrorResponse))
        await context.error(
            step=ActionStep.STATUS,
            content="Failed to re-load configuration, configuration not updated",
            json={
                "status": to_json(load_status),
                "firstError": to_json(first_error)
                })

    while True:
        _ = await ws.receive_text()


@router.get("/file-content",
            summary="text content of the configuration file")
async def file_content(
        config: YouwolConfiguration = Depends(yw_config)
        ):

    return {
        "content": config.pathsBook.config_path.read_text()
        }


@router.get("/status",
            response_model=StatusResponse,
            summary="status")
async def status(
        request: Request,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.environment)
    connected = await connect_to_remote(config=config, context=context)

    remote_gateway_info = config.get_remote_info()
    if remote_gateway_info:
        remote_gateway_info = RemoteGatewayInfo(name=remote_gateway_info.name,
                                                host=remote_gateway_info.host,
                                                connected=connected)
    remotes_info = parse_json(config.userConfig.general.remotesInfo)['remotes'].values()
    resp = StatusResponse(
        configurationPath=list(config.pathsBook.config_path.parts),
        configurationParameters=config.configurationParameters,
        users=config.userConfig.general.get_users_list(),
        userInfo=config.get_user_info(),
        configuration=config.userConfig,
        remoteGatewayInfo=remote_gateway_info,
        remotesInfo=list(remotes_info)
        )

    dict_resp = to_json(resp)

    WebSocketsCache.environment and await WebSocketsCache.environment.send_json({
        **{"type": "Environment"},
        **dict_resp
        })
    WebSocketsCache.environment and await WebSocketsCache.environment.send_json({
        "type": "ConfigurationUpdated"
        })
    await context.info(step=ActionStep.STATUS, content="Current configuration", json=dict_resp)

    return resp


@router.post("/switch-configuration",
             response_model=ConfigurationLoadingStatus,
             summary="switch configuration")
async def switch_configuration(
        request: Request,
        body: SwitchConfigurationBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(
        request=request,
        config=config,
        web_socket=WebSocketsCache.environment
        )
    load_status = await YouwolConfigurationFactory.switch('/'.join(body.path), context)

    if load_status.validated:
        new_conf = await yw_config()
        await status(request, new_conf)

    return load_status


@router.post("/login",
             summary="log in as specified user")
async def login(
        request: Request,
        body: LoginBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    await YouwolConfigurationFactory.login(email=body.email, remote_name=config.selectedRemote)
    new_conf = await yw_config()
    await status(request, new_conf)
    return new_conf.get_user_info()


@router.post("/select-remote-gateway",
             summary="select a remote")
async def select_remote(
        request: Request,
        body: SelectRemoteBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    await YouwolConfigurationFactory.login(email=config.userEmail, remote_name=body.name)
    new_conf = await yw_config()
    await status(request, new_conf)
    return new_conf.get_user_info()


@router.post("/configuration/parameters",
             summary="update_parameters")
async def update_parameters(
        request: Request,
        body: PostParametersBody
        ):
    print(body)
    await YouwolConfigurationFactory.reload(body.values)
    new_conf = await yw_config()
    await status(request, new_conf)


@router.post("/sync-user",
             summary="sync a new local user w/ remote one")
async def sync_user(
        request: Request,
        body: SyncUserBody,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(
        request=request,
        config=config,
        web_socket=WebSocketsCache.environment
        )
    async with context.with_target(body.email).start(f"Sync. user {body.email}") as ctx:

        try:
            auth_token = await get_public_user_auth_token(
                username=body.email,
                pwd=body.password,
                client_id=config.get_remote_info().metadata['keycloakClientId']
                )
        except Exception as e:
            raise RuntimeError(f"Can not authorize from email/pwd @ {config.get_remote_info().host}")

        await ctx.info(step=ActionStep.RUNNING, content="Login successful")

        secrets = parse_json(config.pathsBook.secret_path)
        if body.email in secrets:
            secrets[body.email] = {**secrets[body.email], **{"password": body.password}}
        else:
            secrets[body.email] = {"password": body.password}
        write_json(secrets, config.pathsBook.secret_path)

        user_info = await retrieve_user_info(auth_token)

        users_info = parse_json(config.userConfig.general.usersInfo)
        users_info['users'][body.email] = {
            "id": user_info['sub'],
            "name": user_info['preferred_username'],
            "memberOf": user_info['memberof'],
            "email": user_info["email"]
            }
        write_json(users_info, config.userConfig.general.usersInfo)
        await login(request=request, body=LoginBody(email=body.email), config= config)
        return users_info['users'][body.email]
