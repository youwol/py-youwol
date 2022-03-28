import itertools
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI, APIRouter
from starlette.requests import Request

from youwol_utils import (YouWolException, youwol_exception_handler)
from youwol_utils.context import ContextLogger
from youwol_utils.middlewares.root_middleware import RootMiddleware

flatten = itertools.chain.from_iterable


@dataclass(frozen=True)
class FastApiRouter:
    router: APIRouter


@dataclass(frozen=True)
class FastApiApp:
    title: str
    description: str
    root_path: str
    base_path: str
    root_router: FastApiRouter
    http_port: int
    ctx_logger: ContextLogger


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

    app.add_middleware(RootMiddleware, ctx_logger=app_data.ctx_logger)

    app.include_router(
        app_data.root_router.router,
        prefix=app_data.base_path,
        tags=[]
    )

    # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
    # noinspection PyTypeChecker
    uvicorn.run(app, host="0.0.0.0", port=app_data.http_port)
