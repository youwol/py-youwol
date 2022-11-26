import os
from pathlib import Path

import lockfile

from youwol.main_args import get_main_arguments
from youwol.shut_down import shutdown_daemon_script
from youwol.utils.utils_low_level import assert_python

if __name__ == "__main__":
    assert_python()

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
