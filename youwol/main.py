import asyncio
import os
from pathlib import Path

import daemon
import lockfile
import uvicorn

from youwol.environment.youwol_environment import YouwolEnvironmentFactory, YouwolEnvironment
from youwol.fastapi_app import download_thread, fastapi_app
from youwol.main_args import get_main_arguments
from youwol.utils.utils_low_level import assert_python, shutdown_daemon_script


def main():
    print("Starting")
    shutdown_script_path = Path().cwd() / "py-youwol.shutdown.sh"
    assert_python()
    try:
        uvicorn_log_level = 'info' if get_main_arguments().verbose else 'critical'
        env: YouwolEnvironment = asyncio.run(YouwolEnvironmentFactory.get())
        download_thread.go(env)
        # print_invite(conf=env, shutdown_script_path=shutdown_script_path if get_main_arguments().daemonize else None)

        if get_main_arguments().daemonize:
            print("Daemonizing")
            with daemon.DaemonContext(pidfile=lockfile.FileLock("py-youwol")):
                shutdown_script_path.write_text(shutdown_daemon_script(pid=os.getpid()))
                # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
                # noinspection PyTypeChecker
                uvicorn.run(fastapi_app, host="localhost", port=env.httpPort, log_level=uvicorn_log_level)
        else:
            # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
            # noinspection PyTypeChecker
            uvicorn.run(fastapi_app, host="localhost", port=env.httpPort, log_level=uvicorn_log_level)
    except Exception as e:
        print(e)
        exit()
    finally:
        download_thread.join()
        shutdown_script_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
