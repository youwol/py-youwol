from _typeshed import Incomplete
from watchdog.utils import BaseThread as BaseThread

logger: Incomplete

class ProcessWatcher(BaseThread):
    popen_obj: Incomplete
    process_termination_callback: Incomplete
    def __init__(self, popen_obj, process_termination_callback) -> None: ...
    def run(self) -> None: ...
