from typing import Awaitable

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol.context import Context
from youwol.web_socket import WebSocketsCache

router = APIRouter()


@router.post("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        config: YouwolEnvironment = Depends(yw_config)
):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.environment)
    body = await request.json()
    command = config.commands.get(command_name)
    if command is None:
        return HTTPException(status_code=404, detail=f"Command {command_name} not found")

    result = command.onTriggered(body, context)
    return await result if isinstance(result, Awaitable) else result


@router.get("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        config: YouwolEnvironment = Depends(yw_config)
        ):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.environment)
    body = await request.json()
    command = config.commands.get(command_name)
    if command is None:
        return HTTPException(status_code=404, detail=f"Command {command_name} not found")

    result = command.do_get(context)
    return await result if isinstance(result, Awaitable) else result
