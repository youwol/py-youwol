# third parties
from fastapi import APIRouter

# Youwol application
from youwol.app.environment import api_configuration
from youwol.app.routers import router_remote

# relative
from .custom_commands import router as custom_commands
from .environment import router as environment
from .local_cdn import router as local_cdn
from .projects import router as projects
from .system import router as system

router = APIRouter(tags=["admin"])

router.include_router(
    system.router, prefix=api_configuration.base_path + "/system", tags=["admin.system"]
)
router.include_router(
    environment.router,
    prefix=api_configuration.base_path + "/environment",
    tags=["admin.environment"],
)
router.include_router(
    projects.router,
    prefix=api_configuration.base_path + "/projects",
    tags=["admin.projects"],
)
router.include_router(
    local_cdn.router,
    prefix=api_configuration.base_path + "/local-cdn",
    tags=["admin.local-cdn"],
)
router.include_router(
    custom_commands.router,
    prefix=api_configuration.base_path + "/custom-commands",
    tags=["admin.custom commands"],
)

router.include_router(
    router_remote.router, prefix=api_configuration.base_path + "/remote"
)
