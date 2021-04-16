from fastapi import APIRouter
from dashboard.back.src.routers.admin.backs import restart
from env.utils import get_cached_environment, set_cache_environment
from global_configuration import GlobalConfiguration


router = APIRouter()


def get_current_environment():
    global_config = GlobalConfiguration()
    return get_cached_environment(global_config)


@router.get("/status",
            summary="status")
async def status():

    env = get_current_environment()

    return {
        'current': env,
        'available': ['full-local', 'local']
        }


@router.post("/{name}/switch", summary="execute action")
async def switch(name: str):

    env = get_current_environment()
    if env.name == name:
        return

    global_config = GlobalConfiguration()
    set_cache_environment(name, global_config)
    await restart()
