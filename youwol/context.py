import traceback
import uuid

from async_generator import async_generator, yield_, asynccontextmanager

from typing import Union, NamedTuple, Any, Callable, Awaitable, Optional

from pydantic import BaseModel, Json
from starlette.requests import Request
from starlette.websockets import WebSocket

from auto_download.auto_download_thread import AssetDownloadThread
from youwol.models import LogLevel, ActionStep, Action
from youwol_utils import JSON

# This declaration is for backward compatibility, the error popup when refreshing the dashboard-developer page
Action = Action

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

CallableBlock = Callable[['Context'], Union[Awaitable, None]]
CallableBlockException = Callable[[Exception, 'Context'], Union[Awaitable, None]]


class Context(NamedTuple):

    web_socket: WebSocket

    config: YouwolConfiguration
    request: Request = None
    target: Union[str, None] = None
    action: Union[str, None] = None
    uid: Union[str, None] = None

    download_thread: AssetDownloadThread = None

    def with_target(self, name: str) -> 'Context':
        return Context(web_socket=self.web_socket, config=self.config, action=self.action, target=name)

    def with_action(self, action: str) -> 'Context':
        return Context(web_socket=self.web_socket, config=self.config, target=self.target, action=action)

    @asynccontextmanager
    @async_generator
    async def start(self, action: str, on_enter: CallableBlock = None, on_exit: CallableBlock = None,
                    on_exception: CallableBlockException = None):
        ctx = Context(web_socket=self.web_socket, config=self.config, target=self.target, action=action,
                      uid=str(uuid.uuid4()))

        async def execute_block(block: Optional[Union[CallableBlock, CallableBlockException]],
                                exception: Optional[Exception] = None):
            if not block:
                return
            block = block(ctx) if not exception else block(exception, ctx)
            if isinstance(block, Awaitable):
                await block

        try:
            await ctx.info(ActionStep.STARTED, "")
            await execute_block(on_enter)
            await yield_(ctx)
        except UserCodeException as e:
            await ctx.abort(content=f"Exception during {action} while executing custom code")
            await execute_block(on_exception, e)
            await execute_block(on_exit)
            traceback.print_exc()
        except ActionException as e:
            await ctx.abort(content=f"Exception during {action}: {e.message}")
            await execute_block(on_exception, e)
            await execute_block(on_exit)
            traceback.print_exc()
        except Exception as e:
            await ctx.abort(content=f"Exception during {action}", json={"error": str(e)})
            await execute_block(on_exception, e)
            await execute_block(on_exit)
            traceback.print_exc()
            raise e
        else:
            await ctx.info(ActionStep.DONE, f"{action} done")
            await execute_block(on_exit)

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
