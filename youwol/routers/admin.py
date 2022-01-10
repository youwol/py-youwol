from fastapi import APIRouter
from youwol.configurations import api_configuration

import youwol.routers.projects.router as projects
import youwol.routers.environment.router as environment
import youwol.routers.system.router as system
import youwol.routers.local_cdn.router as local_cdn
import youwol.routers.commands.router as commands
import youwol.routers.custom_commands.router as custom_commands


router = APIRouter()


router.include_router(system.router, prefix=api_configuration.base_path+"/system",
                      tags=["system"])
router.include_router(environment.router, prefix=api_configuration.base_path+"/environment",
                      tags=["environment"])
router.include_router(projects.router, prefix=api_configuration.base_path+"/projects",
                      tags=["projects"])
router.include_router(local_cdn.router, prefix=api_configuration.base_path+"/local-cdn",
                      tags=["local-cdn"])
router.include_router(commands.router, prefix=api_configuration.base_path+"/commands",
                      tags=["commands"])
router.include_router(custom_commands.router, prefix=api_configuration.base_path+"/custom-commands",
                      tags=["custom commands"])
