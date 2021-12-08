import inspect

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from pydantic.main import BaseModel

from youwol.configuration.youwol_configuration import YouwolConfiguration
from youwol.configuration.youwol_configuration import yw_config
from context import Context
from web_socket import WebSocketsCache

router = APIRouter()


class BodyCommand(BaseModel):
    pass


@router.post("/{command_name}", summary="execute a custom command")
async def execute_command(
        request: Request,
        command_name: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):

    context = Context(config=config, request=request, web_socket=WebSocketsCache.environment)
    body = await request.json()
    command = next((command for command in config.userConfig.customCommands if command.name == command_name), None)
    if not command:
        return HTTPException(status_code=404, detail=f"Command {command_name} not found")

    if inspect.iscoroutinefunction(command.onTriggered):
        return await command.onTriggered(body, context)

    return command.onTriggered(body, context)
