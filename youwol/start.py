import asyncio
import traceback
from pathlib import Path
from typing import Optional

import uvicorn

from youwol.environment.errors_handling import ConfigurationLoadingException
from youwol.environment.youwol_environment import YouwolEnvironmentFactory, print_invite, YouwolEnvironment
from youwol.fastapi_app import download_thread, fastapi_app, cleaner_thread
from youwol.main_args import get_main_arguments
from youwol.utils.utils_low_level import assert_py_youwol_starting_preconditions


def start(shutdown_script_path: Optional[Path] = None):
    uvicorn_log_level = 'info' if get_main_arguments().verbose else 'critical'

    try:
        env: YouwolEnvironment = asyncio.run(YouwolEnvironmentFactory.get())
    except ConfigurationLoadingException as e:
        print("Error while loading configuration")
        print(e)
        raise e

    try:
        assert_py_youwol_starting_preconditions(http_port=env.httpPort)
    except ValueError as e:
        print(f"Pre-conditions failed while starting py-youwol server: {e}")
        raise e

    try:
        download_thread.go()
    except BaseException as e:
        print("Error while starting download thread")
        print(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))
        raise e

    try:
        cleaner_thread.go()
    except BaseException as e:
        print("Error while starting download thread")
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
        download_thread.join()
        cleaner_thread.join()
        shutdown_script_path and shutdown_script_path.unlink(missing_ok=True)
