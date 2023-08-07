# third parties
from fastapi import FastAPI
from starlette.requests import Request

# Youwol backends
from youwol.backends.common import BackendDeployment, add_observability_routes

# Youwol utilities
from youwol.utils import (
    DeployedContextReporter,
    YouWolException,
    youwol_exception_handler,
)
from youwol.utils.middlewares.root_middleware import RootMiddleware


def get_fastapi_app(backend_deployment: BackendDeployment):
    app = FastAPI()
    add_observability_routes(app, backend_deployment)

    @app.exception_handler(YouWolException)
    async def exception_handler(request: Request, exc: YouWolException):
        return await youwol_exception_handler(request, exc)

    for m in backend_deployment.middlewares():
        app.add_middleware(m.middleware, **m.args)

    context_reporter = DeployedContextReporter()

    app.add_middleware(
        RootMiddleware,
        logs_reporter=context_reporter,
        data_reporter=context_reporter,
    )

    app.include_router(
        prefix=backend_deployment.prefix(), router=backend_deployment.router()
    )

    for route in app.routes:
        print(f"Route {route}")

    return app
