# standard library
import asyncio
import traceback

from pathlib import Path

# typing
from typing import Optional

# third parties
import uvicorn

# Youwol application
from youwol.app.environment.errors_handling import ConfigurationLoadingException
from youwol.app.environment.youwol_environment import (
    YouwolEnvironment,
    YouwolEnvironmentFactory,
    print_invite,
)
from youwol.app.routers.projects import ProjectLoader

# Youwol utilities
from youwol.utils import is_server_http_alive

# relative
from .fastapi_app import cleaner_thread, download_thread, fastapi_app
from .main_args import get_main_arguments


def assert_free_http_port(http_port: int):
    if is_server_http_alive(f"http://localhost:{http_port}"):
        raise ValueError(f"The port {http_port} is already bound to a process")


def start(shutdown_script_path: Optional[Path] = None):
    uvicorn_log_level = "info" if get_main_arguments().verbose else "critical"

    try:
        env: YouwolEnvironment = asyncio.run(YouwolEnvironmentFactory.get())
    except ConfigurationLoadingException as e:
        print("Error while loading configuration")
        print("".join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))
        raise e

    assert_free_http_port(http_port=env.httpPort)

    try:
        download_thread.go()
    except BaseException as e:
        print("Error while starting download thread")
        print("".join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))
        raise e

    try:
        cleaner_thread.go()
    except BaseException as e:
        print("Error while starting cleaner thread")
        print("".join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))
        raise e

    print_invite(conf=env, shutdown_script_path=shutdown_script_path)

    try:
        # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
        # noinspection PyTypeChecker
        uvicorn.run(
            fastapi_app,
            host="localhost",
            port=env.httpPort,
            log_level=uvicorn_log_level,
        )
    except BaseException as e:
        print("".join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))
        raise e
    finally:
        download_thread.join()
        cleaner_thread.join()
        ProjectLoader.stop()
        if shutdown_script_path is not None:
            shutdown_script_path.unlink(missing_ok=True)
