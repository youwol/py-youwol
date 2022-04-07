import asyncio
import inspect
import itertools
from dataclasses import dataclass, field
from typing import List, Any, Type, Dict, Callable, Union, Awaitable

import uvicorn
from fastapi import FastAPI, APIRouter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from youwol_utils import (YouWolException, youwol_exception_handler)
from youwol_utils.context import ContextLogger
from youwol_utils.middlewares.root_middleware import RootMiddleware

flatten = itertools.chain.from_iterable


@dataclass(frozen=True)
class FastApiRouter:
    router: APIRouter


@dataclass(frozen=True)
class FastApiMiddleware:
    middleware: Type[BaseHTTPMiddleware]
    args: Dict[str, Any]


@dataclass(frozen=True)
class FastApiApp:
    title: str
    description: str
    root_path: str
    base_path: str
    root_router: FastApiRouter
    http_port: int
    ctx_logger: ContextLogger
    middlewares: List[FastApiMiddleware] = field(default_factory=list)
    on_before_startup: Callable[[], Union[None, Awaitable[None]]] = None


def serve(
        app_data: FastApiApp
):

    app = FastAPI(
        title=app_data.title,
        description=app_data.description,
        root_path=app_data.root_path)

    @app.exception_handler(YouWolException)
    async def exception_handler(request: Request, exc: YouWolException):
        return await youwol_exception_handler(request, exc)

    for m in app_data.middlewares:
        app.add_middleware(m.middleware, **m.args)

    app.add_middleware(RootMiddleware, ctx_logger=app_data.ctx_logger)

    app.include_router(
        app_data.root_router.router,
        prefix=app_data.base_path,
        tags=[]
    )
    before = app_data.on_before_startup or (lambda: True)
    if inspect.iscoroutinefunction(before):
        asyncio.get_event_loop().run_until_complete(before())
    else:
        before()

    # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
    # noinspection PyTypeChecker
    uvicorn.run(app, host="0.0.0.0", port=app_data.http_port)
