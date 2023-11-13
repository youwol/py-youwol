# standard library
import logging

# third parties
from fastapi import FastAPI

# Youwol backends
from youwol.backends.common.backend_deployment import add_observability_routes

# relative
from .app import COEPHeaderMiddleware, CORSMiddleware, lifespan, router
from .deployment import ConfigurationFactory, WebpmDeployment

ConfigurationFactory.set_from_env()

app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
add_observability_routes(app=app, backend_deployment=WebpmDeployment(router))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["HEAD", "GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type, Content-Length"],
    allow_credentials=False,
    max_age=7200,
)
app.add_middleware(COEPHeaderMiddleware)
app.include_router(router)

logging.debug("Listing app routes:")
for route in app.routes:
    logging.debug("* Route %s", route)
