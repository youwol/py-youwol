# standard library
from enum import Enum

# typing
from typing import Awaitable

# third parties
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

# Youwol application
from youwol.app.environment import YouwolEnvironment, yw_config
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils.context import Context

router = APIRouter()


class CmdMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


def get_command(command_name: str, method: CmdMethod, env: YouwolEnvironment):
    command = env.commands.get(command_name)

    if command is None:
        raise HTTPException(
            status_code=404, detail=f"Command '{command_name}' not found"
        )

    dos = {
        CmdMethod.GET: command.do_get,
        CmdMethod.POST: command.do_post,
        CmdMethod.PUT: command.do_put,
        CmdMethod.DELETE: command.do_delete,
    }
    if dos[method] is None:
        raise HTTPException(
            status_code=405,
            detail=f"Method {method} not allowed for command '{command_name}'",
        )

    return command


@router.get("/{command_name}", summary="execute a GET custom command")
async def execute_command(
    request: Request, command_name: str, env: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
        request=request,
        with_attributes={
            "topic": "commands",
            "commandName": command_name,
            "method": "GET",
        },
        with_reporters=[LogsStreamer()],
    ) as ctx:
        command = get_command(command_name, CmdMethod.GET, env)
        result = command.do_get(ctx)
        return await result if isinstance(result, Awaitable) else result


@router.post("/{command_name}", summary="execute a POST custom command")
async def execute_post_command(
    request: Request, command_name: str, env: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
        request=request,
        with_attributes={
            "topic": "commands",
            "commandName": command_name,
            "method": "POST",
        },
        with_reporters=[LogsStreamer()],
    ) as ctx:
        body = await request.json()
        command = get_command(command_name, CmdMethod.POST, env)
        result = command.do_post(body, ctx)
        return await result if isinstance(result, Awaitable) else result


@router.put("/{command_name}", summary="execute a PUT custom command")
async def execute_put_command(
    request: Request, command_name: str, env: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
        request=request,
        with_attributes={
            "topic": "commands",
            "commandName": command_name,
            "method": "PUT",
        },
        with_reporters=[LogsStreamer()],
    ) as ctx:
        body = await request.json()
        command = get_command(command_name, CmdMethod.PUT, env)
        result = command.do_put(body, ctx)
        return await result if isinstance(result, Awaitable) else result


@router.delete("/{command_name}", summary="execute a DELETE custom command")
async def execute_delete_command(
    request: Request, command_name: str, env: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
        request=request,
        with_attributes={
            "topic": "commands",
            "commandName": command_name,
            "method": "DELETE",
        },
        with_reporters=[LogsStreamer()],
    ) as ctx:
        command = get_command(command_name, CmdMethod.DELETE, env)
        result = command.do_delete(ctx)
        return await result if isinstance(result, Awaitable) else result
