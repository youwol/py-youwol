# standard library
from abc import ABC, abstractmethod

# third parties
from fastapi import APIRouter, FastAPI
from prometheus_client import start_http_server
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import BaseRoute, Route

# Youwol
import youwol

# Youwol utilities
from youwol.utils.servers.fast_api import FastApiMiddleware


class BackendDeployment(ABC):
    @abstractmethod
    def router(self) -> APIRouter:
        raise NotImplementedError()

    def version(self) -> str:
        return youwol.__version__

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    async def ready(self) -> bool:
        return True

    async def started(self) -> bool:
        return True

    async def alive(self) -> bool:
        return True

    def prefix(self) -> str:
        return ""

    def middlewares(self) -> list[FastApiMiddleware]:
        return []


class ProbeFailure(RuntimeError):
    def __init__(self, msg: str):
        super().__init__(msg)
        self.__msg = msg

    def msg(self):
        return self.__msg


class ProbeResponseContent(BaseModel):
    status: str


class VersionResponseContent(BaseModel):
    name: str
    version: str


probe_response_content_ok = ProbeResponseContent(status="ok")


class ObservablitiyRoutes:
    def __init__(self, backend_deployment: BackendDeployment):
        self.__backend_deployment = backend_deployment

    def route_version(self, _):
        return JSONResponse(
            status_code=200,
            content=VersionResponseContent(
                name=self.__backend_deployment.name(),
                version=self.__backend_deployment.version(),
            ).dict(),
        )

    async def route_readiness(self, _):
        try:
            await self.__backend_deployment.ready()
            return JSONResponse(
                status_code=200, content=probe_response_content_ok.dict()
            )
        except ProbeFailure as e:
            return JSONResponse(status_code=503, content=e.msg())

    async def route_started(self, _):
        try:
            await self.__backend_deployment.started()
            return JSONResponse(
                status_code=200, content=probe_response_content_ok.dict()
            )
        except ProbeFailure as e:
            return JSONResponse(status_code=503, content=e.msg())

    async def route_liveness(self, _):
        try:
            await self.__backend_deployment.alive()
            return JSONResponse(
                status_code=200, content=probe_response_content_ok.dict()
            )
        except ProbeFailure as e:
            return JSONResponse(status_code=503, content=e.msg())

    def __as_routes(self) -> list[BaseRoute]:
        return [
            Route("/version", self.route_version),
            Route("/readiness", self.route_readiness),
            Route("/liveness", self.route_liveness),
            Route("/startup", self.route_started),
        ]

    def app(self) -> FastAPI:
        return FastAPI(routes=self.__as_routes())


def add_observability_routes(app: FastAPI, backend_deployment: BackendDeployment):
    header_server_value = f"{backend_deployment.name()} {backend_deployment.version()}"

    @app.middleware("http")
    async def add_server_header(request: Request, call_next: RequestResponseEndpoint):
        response = await call_next(request)
        response.headers["server"] = header_server_value
        return response

    app_ = ObservablitiyRoutes(backend_deployment=backend_deployment).app()
    start_http_server(8001)
    app.mount(
        path="/observability",
        app=app_,
    )
