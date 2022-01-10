from __future__ import annotations

import traceback
import uuid

from async_generator import async_generator, yield_, asynccontextmanager

from typing import Union, NamedTuple, Callable, Awaitable, Optional, List, Tuple, TypeVar

from pydantic import BaseModel, Json
from starlette.requests import Request
from starlette.websockets import WebSocket

from youwol.utils_low_level import to_json
from youwol.models import LogLevel, Label
from youwol_utils import JSON


AssetDownloadThread = "youwol.auto_download.auto_download_thread"
YouwolConfiguration = "youwol.configuration.youwol_configuration"


class MessageWebSocket(BaseModel):
    action: str
    level: str
    step: str
    target: str
    content: Union[Json, str]


async def log(
        level: LogLevel,
        text: Union[Json, str],
        labels: List[Label],
        web_socket: WebSocket,
        context_id: str,
        data: Union[JSON, BaseModel] = None,
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


class Context(NamedTuple):

    web_socket: WebSocket
    config: YouwolConfiguration
    request: Request = None

    uid: Union[str, None] = 'root'
    parent_uid: Union[str, None] = None

    with_attributes: JSON = {}
    download_thread: AssetDownloadThread = None

    async def send_response(self, response: BaseModel):
        await self.web_socket.send_json(to_json(response))
        return response

    @asynccontextmanager
    @async_generator
    async def start(self,
                    action: str,
                    labels: List[Label] = None,
                    with_attributes: JSON = None,
                    succeeded_data: Callable[
                        [Context],
                        Tuple[str, Union[BaseModel, JSON, float, int, bool, str]]
                    ] = None,
                    on_enter: CallableBlock = None,
                    on_exit: CallableBlock = None,
                    on_exception: CallableBlockException = None):
        with_attributes = with_attributes or {}
        labels = labels or []
        ctx = Context(web_socket=self.web_socket, config=self.config, uid=str(uuid.uuid4()),
                      request=self.request, parent_uid=self.uid, with_attributes={**self.with_attributes,
                                                                                  **with_attributes})

        async def execute_block(block: Optional[Union[CallableBlock, CallableBlockException]],
                                exception: Optional[Exception] = None):
            if not block:
                return
            block = block(ctx) if not exception else block(exception, ctx)
            if isinstance(block, Awaitable):
                await block

        try:
            await ctx.info(text=action, labels=[Label.STARTED, *labels])
            await execute_block(on_enter)
            await yield_(ctx)
        except Exception as e:
            await ctx.abort(
                text=f"Exception raised",
                data=e.__dict__,
                labels=[Label.EXCEPTION, *labels]
            )
            await execute_block(on_exception, e)
            await execute_block(on_exit)
            traceback.print_exc()
            raise e
        else:
            data_type, data = succeeded_data(ctx) if succeeded_data else (None, None)
            await ctx.info(text="", labels=[Label.DONE, data_type, *labels], data=data)
            await execute_block(on_exit)

    async def send(self, data: BaseModel):
        await log(level=LogLevel.DATA, text="", labels=[Label.DATA, data.__class__.__name__],
                  with_attributes=self.with_attributes, data=data, context_id=self.uid,
                  parent_context_id=self.parent_uid, web_socket=self.web_socket)

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


CallableBlock = Callable[[Context], Union[Awaitable, None]]
CallableBlockException = Callable[[Exception, Context], Union[Awaitable, None]]
