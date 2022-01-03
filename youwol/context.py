import traceback
import uuid

from async_generator import async_generator, yield_, asynccontextmanager

from typing import Union, NamedTuple, Any, Callable, Awaitable, Optional, List, Tuple

from pydantic import BaseModel, Json
from starlette.requests import Request
from starlette.websockets import WebSocket

# from auto_download.auto_download_thread import AssetDownloadThread
from utils_low_level import to_json
from youwol.models import LogLevel, Label
from youwol_utils import JSON

YouwolConfiguration = 'youwol.configuration.YouwolConfiguration'


class MessageWebSocket(BaseModel):
    action: str
    level: str
    step: str
    target: str
    content: Union[Json, str]


class CommandException(Exception):
    def __init__(self, command: str, outputs: List[str]):
        self.command = command
        self.outputs = outputs
        super().__init__(f"{self.command} failed")


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
        text: Union[Json, str],
        labels: List[Label],
        web_socket: WebSocket,
        context_id: str,
        data: JSON = None,
        with_attributes:  JSON = None,
        parent_context_id: str = None,
        ):
    message = {
        "level": level.name,
        "attributes": with_attributes,
        "labels": [str(label) for label in labels],
        "text": text,
        "data": to_json(data) if isinstance(data, BaseModel) else data,
        "contextId": context_id,
        "parentContextId": parent_context_id
        }
    web_socket and await web_socket.send_json(message)

CallableBlock = Callable[['Context'], Union[Awaitable, None]]
CallableBlockException = Callable[[Exception, 'Context'], Union[Awaitable, None]]


class Context(NamedTuple):

    web_socket: WebSocket
    config: YouwolConfiguration
    request: Request = None

    uid: Union[str, None] = 'root'
    parent_uid: Union[str, None] = None

    with_attributes: JSON = {}
    download_thread: 'AssetDownloadThread' = None
    succeeded_data: Union[JSON, BaseModel] = None

    async def send_response(self, response: BaseModel):
        await self.web_socket.send_json(to_json(response))
        return response

    def succeeded(self, data: Union[JSON, BaseModel]):
        self.succeeded_data = data

    @asynccontextmanager
    @async_generator
    async def start(self,
                    action: str,
                    labels: List[Label] = None,
                    with_attributes: JSON = None,
                    succeeded_data: Callable[['Context'], Tuple[str, Union[BaseModel, JSON, float, int, bool, str]]] = None,
                    on_enter: CallableBlock = None,
                    on_exit: CallableBlock = None,
                    on_exception: CallableBlockException = None):
        with_attributes = with_attributes or {}
        labels = labels or []
        ctx = Context(web_socket=self.web_socket, config=self.config, uid=str(uuid.uuid4()),
                      parent_uid=self.uid, with_attributes={**self.with_attributes, **with_attributes})

        async def execute_block(block: Optional[Union[CallableBlock, CallableBlockException]],
                                exception: Optional[Exception] = None):
            if not block:
                return
            block = block(ctx) if not exception else block(exception, ctx)
            if isinstance(block, Awaitable):
                await block

        try:
            await ctx.info(text=action, labels=[Label.STARTED]+labels)
            await execute_block(on_enter)
            await yield_(ctx)

        except UserCodeException as e:
            await ctx.abort(text=f"Exception during {action} while executing custom code", labels=[])
            await execute_block(on_exception, e)
            await execute_block(on_exit)
            traceback.print_exc()
        except ActionException as e:
            await ctx.abort(text=f"Exception during {action}: {e.message}", labels=[])
            await execute_block(on_exception, e)
            await execute_block(on_exit)
            traceback.print_exc()
        except Exception as e:
            await ctx.abort(text=f"Exception during {action}", data={"error": str(e)}, labels=[])
            await execute_block(on_exception, e)
            await execute_block(on_exit)
            traceback.print_exc()
            raise e
        else:
            data_type, data = succeeded_data(ctx) if succeeded_data else (None, None)
            await ctx.info(text="", labels=[Label.DONE, data_type], data=data)
            await execute_block(on_exit)

    async def debug(self, text: str, labels: List[Label] = None, data: Union[JSON, BaseModel] = None):
        labels = labels or []
        await log(level=LogLevel.DEBUG, text=text, labels=[Label.LOG_DEBUG] + labels,
                  with_attributes=self.with_attributes, data=data, context_id=self.uid,
                  parent_context_id=self.parent_uid, web_socket=self.web_socket)

    async def info(self, text: str, labels: List[Label] = None, data: Union[JSON, BaseModel] = None):
        labels = labels or []
        await log(level=LogLevel.INFO, text=text, labels=[Label.LOG_INFO] + labels,
                  with_attributes=self.with_attributes, data=data, context_id=self.uid,
                  parent_context_id=self.parent_uid, web_socket=self.web_socket)

    async def error(self, text: str, labels: List[Label] = None, data: Union[JSON, BaseModel] = None):
        labels = labels or []
        await log(level=LogLevel.ERROR,  text=text, labels=[Label.LOG_ERROR] + labels,
                  with_attributes=self.with_attributes, data=data, context_id=self.uid,
                  parent_context_id=self.parent_uid, web_socket=self.web_socket)

    async def abort(self, text: str, labels: List[Label] = None, data: Union[JSON, BaseModel] = None):
        labels = labels or []
        await log(level=LogLevel.ERROR,  text=text, labels=[Label.LOG_ABORT] + labels,
                  with_attributes=self.with_attributes, data=data, context_id=self.uid,
                  parent_context_id=self.parent_uid, web_socket=self.web_socket)
