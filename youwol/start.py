import asyncio
import traceback
from pathlib import Path
from typing import Optional

import uvicorn

from youwol.environment.errors_handling import ConfigurationLoadingException
from youwol.environment.youwol_environment import YouwolEnvironmentFactory, print_invite, YouwolEnvironment
from youwol.fastapi_app import download_thread, fastapi_app, cleaner_thread
from youwol.main_args import get_main_arguments
from youwol.routers.projects import ProjectLoader
from youwol_utils import is_server_http_alive


def assert_free_http_port(http_port: int):
    if is_server_http_alive(f"http://localhost:{http_port}"):
        raise ValueError(f"The port {http_port} is already bound to a process")


def start(shutdown_script_path: Optional[Path] = None):
    uvicorn_log_level = 'info' if get_main_arguments().verbose else 'critical'

    try:
        env: YouwolEnvironment = asyncio.run(YouwolEnvironmentFactory.get())
    except ConfigurationLoadingException as e:
        print("Error while loading configuration")
        print(e)
        raise e

    assert_free_http_port(http_port=env.httpPort)

    try:
        download_thread.go()
    except BaseException as e:
        print("Error while starting download thread")
        print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        raise e

    try:
        cleaner_thread.go()
    except BaseException as e:
        print("Error while starting cleaner thread")
        print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        raise e

    print_invite(conf=env, shutdown_script_path=shutdown_script_path)

    try:
        # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
        # noinspection PyTypeChecker
        uvicorn.run(fastapi_app, host="localhost", port=env.httpPort, log_level=uvicorn_log_level)
    except BaseException as e:
        print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        raise e
    finally:
        env.backends_configuration.persist_no_sql_data()
        download_thread.join()
        cleaner_thread.join()
        ProjectLoader.stop()
        shutdown_script_path and shutdown_script_path.unlink(missing_ok=True)
