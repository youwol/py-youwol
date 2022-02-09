from enum import Enum
from typing import Awaitable

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol_utils.context import Context

router = APIRouter()


class CmdMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


def get_command(command_name: str, method: CmdMethod, env: YouwolEnvironment):
    command = env.commands.get(command_name)

    if command is None:
        raise HTTPException(status_code=404, detail=f"Command '{command_name}' not found")

    dos = {CmdMethod.GET: command.do_get,
           CmdMethod.POST: command.do_post,
           CmdMethod.PUT: command.do_put,
           CmdMethod.DELETE: command.do_delete}
    if dos[method] is None:
        raise HTTPException(status_code=405, detail=f"Method {method} not allowed for command '{command_name}'")

    return command


@router.get("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        env: YouwolEnvironment = Depends(yw_config)
):
    context = Context.from_request(request)
    command = get_command(command_name, CmdMethod.GET, env)
    result = command.do_get(context)
    return await result if isinstance(result, Awaitable) else result


@router.post("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        env: YouwolEnvironment = Depends(yw_config)
):
    context = Context.from_request(request)
    body = await request.json()
    command = get_command(command_name, CmdMethod.POST, env)
    result = command.do_post(body, context)
    return await result if isinstance(result, Awaitable) else result


@router.put("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        env: YouwolEnvironment = Depends(yw_config)
):
    context = Context.from_request(request)
    body = await request.json()
    command = get_command(command_name, CmdMethod.PUT, env)
    result = command.do_put(body, context)
    return await result if isinstance(result, Awaitable) else result


@router.delete("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        env: YouwolEnvironment = Depends(yw_config)
):
    context = Context.from_request(request)
    command = get_command(command_name, CmdMethod.DELETE, env)
    result = command.do_delete(context)
    return await result if isinstance(result, Awaitable) else result
