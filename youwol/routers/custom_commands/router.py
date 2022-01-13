from typing import Awaitable

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol.web_socket import WebSocketsStore
from youwol_utils.context import ContextFactory

router = APIRouter()


@router.get("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        config: YouwolEnvironment = Depends(yw_config)
        ):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )
    command = config.commands.get(command_name)
    if command is None:
        raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")

    if command.do_get is None:
        raise HTTPException(status_code=405, detail=f"Method GET not allowed for command '{command_name}'")

    result = command.do_get(context)
    return await result if isinstance(result, Awaitable) else result


@router.post("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        config: YouwolEnvironment = Depends(yw_config)
):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )
    body = await request.json()
    command = config.commands.get(command_name)
    if command is None:
        raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")

    if command.do_post is None:
        raise HTTPException(status_code=405, detail=f"Method POST not allowed for command '{command_name}'")

    result = command.do_post(body, context)
    return await result if isinstance(result, Awaitable) else result


@router.put("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        config: YouwolEnvironment = Depends(yw_config)
):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )
    body = await request.json()
    command = config.commands.get(command_name)
    if command is None:
        raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")

    if command.do_put is None:
        raise HTTPException(status_code=405, detail=f"Method PUT not allowed for command '{command_name}'")

    result = command.do_put(body, context)
    return await result if isinstance(result, Awaitable) else result


@router.delete("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        config: YouwolEnvironment = Depends(yw_config)
):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )
    command = config.commands.get(command_name)
    if command is None:
        raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")

    if command.do_delete is None:
        raise HTTPException(status_code=405, detail=f"Method DELETE not allowed for command '{command_name}'")

    result = command.do_delete(context)
    return await result if isinstance(result, Awaitable) else result
