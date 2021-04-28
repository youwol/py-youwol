import traceback
import uuid

from async_generator import async_generator, yield_, asynccontextmanager

from typing import Union, NamedTuple, Any

from pydantic import BaseModel, Json
from starlette.requests import Request
from starlette.websockets import WebSocket

from youwol.models import Action, LogLevel, ActionStep
from youwol_utils import JSON


YouwolConfiguration = "youwol.configuration.youwol_configuration"


class MessageWebSocket(BaseModel):
    action: str
    level: str
    step: str
    target: str
    content: Union[Json, str]


class ActionException(Exception):
    def __init__(self, action: str, message: str):
        self.action = action
        self.message = message
        super().__init__(self.message)


class UserCodeException(Exception):
    def __init__(self, message: str, tb: Any):
        self.traceback = tb
        self.message = message
        super().__init__(self.message)


async def log(
        level: LogLevel,
        action: str,
        step: ActionStep,
        target: str,
        content: Union[Json, str],
        context_id: str,
        web_socket: WebSocket,
        json: JSON = None,
        ):
    message = {
        "action": str(action) if action else "",
        "target": target,
        "level": level.name,
        "step": step.name,
        "content": content,
        "json": json,
        "contextId": context_id
        }
    web_socket and await web_socket.send_json(message)


class Context(NamedTuple):

    web_socket: WebSocket
    config: YouwolConfiguration
    request: Request = None
    target: Union[str, None] = None
    action: Union[str, None] = None
    uid: Union[str, None] = None

    def with_target(self, name: str) -> 'Context':
        return Context(web_socket=self.web_socket, config=self.config, action=self.action, target=name)

    def with_action(self, action: str) -> 'Context':
        return Context(web_socket=self.web_socket, config=self.config, target=self.target, action=action)

    @asynccontextmanager
    @async_generator
    async def start(self, action: str):
        ctx = Context(web_socket=self.web_socket, config=self.config, target=self.target, action=action,
                      uid=str(uuid.uuid4()))
        try:
            await ctx.info(ActionStep.STARTED, "")
            await yield_(ctx)
        except UserCodeException as _:
            await ctx.abort(content=f"Exception during {action} while executing custom code")
            traceback.print_exc()
        except ActionException as e:
            await ctx.abort(content=f"Exception during {action}: {e.message}")
            traceback.print_exc()
        except Exception as e:
            await ctx.abort(content=f"Exception during {action}", json={"error": str(e)})
            traceback.print_exc()
            raise e
        else:
            await ctx.info(ActionStep.DONE, f"{action} done")

    async def debug(self, step: ActionStep, content: str, json: JSON = None):
        await log(level=LogLevel.DEBUG, action=self.action, step=step, target=self.target, content=content,
                  json=json, context_id=self.uid, web_socket=self.web_socket)

    async def info(self, step: ActionStep, content: str, json: JSON = None):
        await log(level=LogLevel.INFO, action=self.action, step=step, target=self.target, content=content,
                  json=json, context_id=self.uid, web_socket=self.web_socket)

    async def error(self, step: ActionStep, content: str, json: JSON = None):
        await log(level=LogLevel.ERROR, action=self.action, step=step, target=self.target, content=content,
                  json=json, context_id=self.uid, web_socket=self.web_socket)

    async def abort(self, content, json: JSON = None):
        await log(level=LogLevel.ERROR, action=self.action, step=ActionStep.DONE, target=self.target, content=content,
                  json=json, context_id=self.uid, web_socket=self.web_socket)
