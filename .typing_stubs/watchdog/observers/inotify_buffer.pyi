# third parties
from _typeshed import Incomplete
from watchdog.observers.inotify_c import Inotify as Inotify
from watchdog.utils import BaseThread as BaseThread
from watchdog.utils.delayed_queue import DelayedQueue as DelayedQueue

logger: Incomplete

class InotifyBuffer(BaseThread):
    delay: float
    def __init__(self, path, recursive: bool = ...) -> None: ...
    def read_event(self): ...
    def on_thread_stop(self) -> None: ...
    def close(self) -> None: ...
    def run(self) -> None: ...
