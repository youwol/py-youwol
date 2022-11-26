from fastapi import APIRouter

import youwol.routers.custom_commands.router as custom_commands
import youwol.routers.environment.router as environment
import youwol.routers.local_cdn.router as local_cdn
import youwol.routers.projects.router as projects
import youwol.routers.system.router as system
from youwol.environment import api_configuration
from youwol.routers import router_remote

router = APIRouter(tags=["admin"])

router.include_router(system.router, prefix=api_configuration.base_path + "/system",
                      tags=["admin.system"])
router.include_router(environment.router, prefix=api_configuration.base_path + "/environment",
                      tags=["admin.environment"])
router.include_router(projects.router, prefix=api_configuration.base_path + "/projects",
                      tags=["admin.projects"])
router.include_router(local_cdn.router, prefix=api_configuration.base_path + "/local-cdn",
                      tags=["admin.local-cdn"])
router.include_router(custom_commands.router, prefix=api_configuration.base_path + "/custom-commands",
                      tags=["admin.custom commands"])

router.include_router(router_remote.router, prefix=api_configuration.base_path + "/remote")
