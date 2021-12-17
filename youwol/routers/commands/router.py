from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from pydantic.main import BaseModel

from youwol.context import Context
from routers.commands.commands_factory import commands_factory
from youwol.configuration.youwol_configuration import YouwolConfiguration
from youwol.configuration.youwol_configuration import yw_config
from web_socket import WebSocketsCache

router = APIRouter()


class BodyCommand(BaseModel):
    pass


@router.post("/{command_name}", summary="execute a command")
async def execute_command(
        request: Request,
        command_name: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    body = await request.json()
    command = next((v for k, v in commands_factory.items() if k == command_name), None)
    if not command:
        return HTTPException(status_code=404, detail=f"Command {command_name} not found")
    context = Context(config=config, request=request, web_socket=WebSocketsCache.environment)

    return await command(body, context)
