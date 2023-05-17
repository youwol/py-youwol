# standard library
import asyncio
import inspect
import itertools
import sys

from dataclasses import dataclass

# typing
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

# third parties
import uvicorn

from fastapi import APIRouter, FastAPI
from pydantic import BaseConfig, BaseModel, create_model
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Youwol utilities
from youwol.utils import YouWolException, log_info, youwol_exception_handler
from youwol.utils.context import Context, ContextReporter
from youwol.utils.middlewares.root_middleware import RootMiddleware

flatten = itertools.chain.from_iterable

BaseConfig.arbitrary_types_allowed = True


class FastApiRouter(BaseModel):
    """
    Define a router using the fast-api library.

    **Attributes**:

    - **router** an :class:`APIRouter` or a function returning an :class:`APIRouter` (eventually awaitable)
    Defines the :class:`APIRouter`, see fast-api documentation.

    - **base_path** :class:`str`
    Base path from which the router is served.

    *Default to empty string*"""

    router: Union[
        APIRouter, Callable[[Context], Union[APIRouter, Awaitable[APIRouter]]]
    ]
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


def select_configuration_from_command_line(
    configs_map: Dict[str, Callable[[], Awaitable[AppConfiguration]]]
) -> AppConfiguration:
    if len(sys.argv) < 2:
        raise RuntimeError(
            "The configuration name needs to be supplied as command line argument"
        )
    config_name = sys.argv[1]
    if config_name not in configs_map:
        raise RuntimeError(f"The configuration {config_name} is not known")

    log_info(f"Use '{config_name}' configuration")
    config = configs_map[config_name]
    selected_config: AppConfiguration = asyncio.get_event_loop().run_until_complete(
        config()
    )
    return selected_config


def serve(app_data: FastApiApp):
    app = FastAPI(
        title=app_data.title,
        description=app_data.description,
        root_path=app_data.server_options.root_path,
    )

    @app.exception_handler(YouWolException)
    async def exception_handler(request: Request, exc: YouWolException):
        return await youwol_exception_handler(request, exc)

    for m in app_data.server_options.middlewares:
        app.add_middleware(m.middleware, **m.args)

    app.add_middleware(
        RootMiddleware,
        logs_reporter=app_data.server_options.ctx_logger,
        data_reporter=app_data.server_options.ctx_logger,
    )

    app.include_router(
        app_data.root_router.router, prefix=app_data.server_options.base_path, tags=[]
    )
    before = app_data.server_options.on_before_startup or (lambda: True)
    if inspect.iscoroutinefunction(before):
        asyncio.get_event_loop().run_until_complete(before())
    else:
        before()

    # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
    # noinspection PyTypeChecker
    uvicorn.run(app, host="0.0.0.0", port=app_data.server_options.http_port)
