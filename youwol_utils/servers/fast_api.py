import asyncio
import inspect
import itertools
import sys
from dataclasses import dataclass
from typing import List, Any, Type, Dict, Callable, Union, Awaitable, Optional, TypeVar, Generic

import uvicorn
from fastapi import FastAPI, APIRouter
from pydantic import BaseModel, BaseConfig, create_model
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from youwol_utils import (YouWolException, youwol_exception_handler, log_info)
from youwol_utils.context import ContextReporter, Context
from youwol_utils.middlewares.root_middleware import RootMiddleware

flatten = itertools.chain.from_iterable

BaseConfig.arbitrary_types_allowed = True


class FastApiRouter(BaseModel):
    router: Union[APIRouter, Callable[[Context], Union[APIRouter, Awaitable[APIRouter]]]]
    base_path: Optional[str] = ""
    __pydantic_model__ = create_model("FastApiRouter")


@dataclass(frozen=True)
class FastApiMiddleware:
    middleware: Type[BaseHTTPMiddleware]
    args: Dict[str, Any]


@dataclass(frozen=True)
class ServerOptions:
    root_path: str
    http_port: int
    base_path: str
    middlewares: List[FastApiMiddleware]
    ctx_logger: ContextReporter
    on_before_startup: Callable[[], Union[None, Awaitable[None]]] = None


T = TypeVar("T")


@dataclass(frozen=True)
class AppConfiguration(Generic[T]):
    server: ServerOptions
    service: T


@dataclass(frozen=True)
class FastApiApp:
    title: str
    description: str
    root_router: FastApiRouter
    server_options: ServerOptions


def select_configuration_from_command_line(configs_map: Dict[str, Callable[[], Awaitable[AppConfiguration]]]) \
        -> AppConfiguration:

    if len(sys.argv) < 2:
        raise RuntimeError("The configuration name needs to be supplied as command line argument")
    config_name = sys.argv[1]
    if config_name not in configs_map:
        raise RuntimeError(f"The configuration {config_name} is not known")

    log_info(f"Use '{config_name}' configuration")
    config = configs_map[config_name]
    selected_config: AppConfiguration = asyncio.get_event_loop().run_until_complete(config())
    return selected_config


def serve(
        app_data: FastApiApp
):

    app = FastAPI(
        title=app_data.title,
        description=app_data.description,
        root_path=app_data.server_options.root_path)

    @app.exception_handler(YouWolException)
    async def exception_handler(request: Request, exc: YouWolException):
        return await youwol_exception_handler(request, exc)

    for m in app_data.server_options.middlewares:
        app.add_middleware(m.middleware, **m.args)

    app.add_middleware(
        RootMiddleware,
        logs_reporter=app_data.server_options.ctx_logger,
        data_reporter=app_data.server_options.ctx_logger
    )

    app.include_router(
        app_data.root_router.router,
        prefix=app_data.server_options.base_path,
        tags=[]
    )
    before = app_data.server_options.on_before_startup or (lambda: True)
    if inspect.iscoroutinefunction(before):
        asyncio.get_event_loop().run_until_complete(before())
    else:
        before()

    # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
    # noinspection PyTypeChecker
    uvicorn.run(app, host="0.0.0.0", port=app_data.server_options.http_port)
