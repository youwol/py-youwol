# standard library
import os
import sys

from pathlib import Path

# third parties
import lockfile

# Youwol application
from youwol.app.main_args import get_main_arguments
from youwol.app.shut_down import shutdown_daemon_script


def assert_python():
    print(f"Running with python:\n\t{sys.executable}\n\t{sys.version}")
    version_info = sys.version_info
    if not (
        (version_info.major == 3 and version_info.minor == 10)
        or (version_info.major == 3 and version_info.minor == 9)
        or (version_info.major == 3 and version_info.minor == 8)
        or (version_info.major == 3 and version_info.minor == 7)
    ):
        print(
            """Your version of python is not compatible with py-youwol:
        Recommended: 3.9.x"""
        )
        exit(1)


def main():
    assert_python()

    if get_main_arguments().daemonize:
        shutdown_script_path = Path().cwd() / "py-youwol.shutdown.sh"
        # noinspection PyPackageRequirements
        # Installing daemon fails on Windows -> not in requirements
        # third parties
        import daemon

        # noinspection PyUnresolvedReferences
        with open("py-youwol.log", "x", encoding="UTF-8") as log:
            with daemon.DaemonContext(
                pidfile=lockfile.FileLock("py-youwol"), stderr=log, stdout=log
            ):
                # Youwol application
                from youwol.app.start import start

                shutdown_script_path.write_text(shutdown_daemon_script(pid=os.getpid()))
                # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
                # noinspection PyTypeChecker
                start(shutdown_script_path)
    else:
        # Youwol application
        from youwol.app.start import start

        start()


if __name__ == "__main__":
    main()