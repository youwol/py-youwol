import itertools

from fastapi import APIRouter, WebSocket, Depends
from starlette.requests import Request

from youwol.configuration import ErrorResponse
from youwol.configuration.user_configuration import YouwolConfiguration, get_remote_auth_token
from youwol.configuration.youwol_configuration import yw_config, YouwolConfigurationFactory, ConfigurationLoadingStatus
from youwol.context import Context, Action, ActionStep
from youwol.routers.environment.models import (
    StatusResponse, SwitchConfigurationBody, SyncUserBody, LoginBody,
    PostParametersBody,
    )
from youwol.utils_low_level import to_json
from youwol.utils_paths import parse_json, write_json
from youwol.web_socket import WebSocketsCache
from youwol_utils import retrieve_user_info

router = APIRouter()
flatten = itertools.chain.from_iterable


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
    resp = StatusResponse(
        configurationPath=str(config.pathsBook.config_path),
        configurationParameters=config.configurationParameters,
        users=config.userConfig.general.get_users_list(),
        userInfo=await config.userConfig.general.get_user_info(context),
        configuration=config.userConfig
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
    load_status = await YouwolConfigurationFactory.switch(body.path, context)

    if load_status.validated:
        new_conf = await yw_config()
        await status(request, new_conf)

    return load_status


@router.post("/login",
             summary="log in as specified user")
async def login(
        request: Request,
        body: LoginBody
        ):

    await YouwolConfigurationFactory.login(body.email)
    new_conf = await yw_config()
    await status(request, new_conf)


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
    async with context.with_target(body.email).start(Action.SYNC_USER) as ctx:
        secret = config.userConfig.general.get_secret(body.remoteEnvironment)
        auth_token = await get_remote_auth_token(
            username=body.email,
            pwd=body.password,
            client_id=secret.clientId,
            client_secret=secret.clientSecret,
            )
        await ctx.info(step=ActionStep.RUNNING, content="Retrieved auth token successfully.")
        user_info = await retrieve_user_info(auth_token)
        secrets = parse_json(config.userConfig.general.secretsFile)
        identities = secrets['identities'] if 'identities' in secrets else {}
        identities[body.email] = body.password
        secrets['identities'] = identities
        write_json(secrets, config.userConfig.general.secretsFile)

        users_info = parse_json(config.userConfig.general.usersInfo)
        users_info[body.email] = {
            "id": user_info['sub'],
            "name": user_info['preferred_username'],
            "memberOf": user_info['memberof'],
            "email": user_info["email"]
            }
        write_json(users_info, config.userConfig.general.usersInfo)
        await status(request=request, config=config)
        return users_info[body.email]
