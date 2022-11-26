import os
import socket
import sys
from pathlib import Path

import lockfile

from youwol.main_args import get_main_arguments
from youwol.shut_down import shutdown_daemon_script


def assert_python():
    print(f"Running with python:\n\t{sys.executable}\n\t{sys.version}")
    version_info = sys.version_info
    if not ((version_info.major == 3 and version_info.minor == 10) or
            (version_info.major == 3 and version_info.minor == 9) or
            (version_info.major == 3 and version_info.minor == 8) or
            (version_info.major == 3 and version_info.minor == 7)):
        print(f"""Your version of python is not compatible with py-youwol:
        Recommended: 3.9.x""")
        exit(1)


def assert_free_http_port(http_port: int):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    location = ("127.0.0.1", http_port)
    if a_socket.connect_ex(location) == 0:
        raise ValueError(f"The port {http_port} is already bound to a process")


if __name__ == "__main__":
    assert_python()
    assert_free_http_port(http_port=get_main_arguments().port)

    if get_main_arguments().daemonize:
        shutdown_script_path = Path().cwd() / "py-youwol.shutdown.sh"
        # noinspection PyPackageRequirements
        # Installing daemon fails on Windows -> not in requirements
        import daemon

        # noinspection PyUnresolvedReferences
        with open("py-youwol.log", "x") as log:
            with daemon.DaemonContext(pidfile=lockfile.FileLock("py-youwol"), stderr=log, stdout=log):
                from youwol.start import start
                shutdown_script_path.write_text(shutdown_daemon_script(pid=os.getpid()))
                # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
                # noinspection PyTypeChecker
                start(shutdown_script_path)
    else:
        from youwol.start import start
        start()
