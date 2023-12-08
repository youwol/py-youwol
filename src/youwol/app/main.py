# standard library
import os
import sys

from pathlib import Path

# third parties
import lockfile

# Youwol application
from youwol.app.main_args import get_main_arguments
from youwol.app.shut_down import shutdown_daemon_script
from youwol.app.wrapper import ensure_venv_python_in_path


def assert_python():
    print(f"Running with python:\n\t{sys.executable}\n\t{sys.version}")
    version_info = sys.version_info
    if not (
        (version_info.major == 3 and version_info.minor == 10)
        or (version_info.major == 3 and version_info.minor == 11)
        or (version_info.major == 3 and version_info.minor == 12)
        or (version_info.major == 3 and version_info.minor == 9)
    ):
        print(
            """Your version of python is not compatible with py-youwol:
        Recommended: 3.12.x"""
        )
        sys.exit(1)


def main():
    assert_python()
    ensure_venv_python_in_path()
    if get_main_arguments().daemonize:
        shutdown_script_path = Path().cwd() / "py-youwol.shutdown.sh"
        # noinspection PyPackageRequirements
        # Installing daemon fails on Windows -> not in requirements
        # third parties
        import daemon  # pylint: disable=import-outside-toplevel

        # noinspection PyUnresolvedReferences
        with open("py-youwol.log", "x", encoding="UTF-8") as log:
            with daemon.DaemonContext(
                pidfile=lockfile.FileLock("py-youwol"), stderr=log, stdout=log
            ):
                shutdown_script_path.write_text(shutdown_daemon_script(pid=os.getpid()))
                # app: incorrect type. More here: https://github.com/tiangolo/fastapi/issues/3927
                # noinspection PyTypeChecker
                # Youwol application
                from youwol.app.start import (  # pylint: disable=import-outside-toplevel
                    start,
                )

                start(shutdown_script_path)
    else:
        # Youwol application
        from youwol.app.start import start  # pylint: disable=import-outside-toplevel

        start()


if __name__ == "__main__":
    main()
