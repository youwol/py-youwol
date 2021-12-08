from fastapi import APIRouter
from youwol.configurations import configuration

import youwol.routers.packages.router as packages
import youwol.routers.backends.router as backends
import youwol.routers.environment.router as environment
import youwol.routers.upload.router_packages as upload_packages
import youwol.routers.upload.router_flux_apps as upload_flux_apps
import youwol.routers.upload.router_stories as upload_stories
import youwol.routers.upload.router_data as upload_data
import youwol.routers.download.router_packages as download_packages
import youwol.routers.download.router_flux_apps as download_flux_apps
import youwol.routers.system.router as system
import youwol.routers.local_cdn.router as local_cdn
import youwol.routers.commands.router as commands
import youwol.routers.custom_commands.router as custom_commands


router = APIRouter()


router.include_router(system.router, prefix=configuration.base_path+"/system",
                      tags=["system"])
router.include_router(environment.router, prefix=configuration.base_path+"/environment",
                      tags=["environment"])
router.include_router(packages.router, prefix=configuration.base_path+"/packages",
                      tags=["packages"])
router.include_router(backends.router, prefix=configuration.base_path+"/backends",
                      tags=["backends"])
router.include_router(local_cdn.router, prefix=configuration.base_path+"/local-cdn",
                      tags=["local-cdn"])
router.include_router(upload_packages.router, prefix=configuration.base_path+"/upload/packages",
                      tags=["upload packages"])
router.include_router(upload_flux_apps.router, prefix=configuration.base_path+"/upload/flux-apps",
                      tags=["upload flux apps"])
router.include_router(upload_stories.router, prefix=configuration.base_path+"/upload/stories",
                      tags=["upload stories"])
router.include_router(upload_data.router, prefix=configuration.base_path+"/upload/data",
                      tags=["upload data"])
router.include_router(download_packages.router, prefix=configuration.base_path+"/download/packages",
                      tags=["download packages"])
router.include_router(download_flux_apps.router, prefix=configuration.base_path+"/download/flux-apps",
                      tags=["download flux apps"])
router.include_router(commands.router, prefix=configuration.base_path+"/commands",
                      tags=["commands"])
router.include_router(custom_commands.router, prefix=configuration.base_path+"/custom-commands",
                      tags=["custom commands"])
