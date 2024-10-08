# standard library
import asyncio
import traceback

from pathlib import Path

# third parties
import uvicorn

# Youwol application
from youwol.app.environment.errors_handling import ConfigurationLoadingException
from youwol.app.environment.youwol_environment import (
    YouwolEnvironment,
    YouwolEnvironmentFactory,
    print_invite,
)

# Youwol utilities
from youwol.utils import is_server_http_alive

# relative
from .fastapi_app import fastapi_app
from .main_args import get_main_arguments


def assert_free_http_port(http_port: int):
    if is_server_http_alive(f"http://localhost:{http_port}"):
        raise ValueError(f"The port {http_port} is already bound to a process")


def start(shutdown_script_path: Path | None = None):
    uvicorn_log_level = "info" if get_main_arguments().verbose else "critical"

    try:
        env: YouwolEnvironment = asyncio.run(YouwolEnvironmentFactory.get())
    except ConfigurationLoadingException as e:
        print("Error while loading configuration")
        print("".join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))
        raise e

    assert_free_http_port(http_port=env.httpPort)

    print_invite(conf=env, shutdown_script_path=shutdown_script_path)

    try:
        # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
        # noinspection PyTypeChecker
        uvicorn.run(
            fastapi_app,
            # Not 'localhost' because backends running in containers need to be able to communicate with this server.
            host="0.0.0.0",
            port=env.httpPort,
            log_level=uvicorn_log_level,
        )
    except BaseException as e:
        print("".join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))
        raise e
    finally:
        if shutdown_script_path is not None:
            shutdown_script_path.unlink(missing_ok=True)
