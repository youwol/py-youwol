# third parties
from _typeshed import Incomplete
from watchdog.events import PatternMatchingEventHandler as PatternMatchingEventHandler
from watchdog.utils import echo as echo
from watchdog.utils.process_watcher import ProcessWatcher as ProcessWatcher

logger: Incomplete
echo_events: Incomplete

class Trick(PatternMatchingEventHandler):
    @classmethod
    def generate_yaml(cls): ...

class LoggerTrick(Trick):
    def on_any_event(self, event) -> None: ...
    def on_modified(self, event) -> None: ...
    def on_deleted(self, event) -> None: ...
    def on_created(self, event) -> None: ...
    def on_moved(self, event) -> None: ...

class ShellCommandTrick(Trick):
    shell_command: Incomplete
    wait_for_process: Incomplete
    drop_during_process: Incomplete
    process: Incomplete
    def __init__(
        self,
        shell_command: Incomplete | None = ...,
        patterns: Incomplete | None = ...,
        ignore_patterns: Incomplete | None = ...,
        ignore_directories: bool = ...,
        wait_for_process: bool = ...,
        drop_during_process: bool = ...,
    ) -> None: ...
    def on_any_event(self, event) -> None: ...
    def is_process_running(self): ...

class AutoRestartTrick(Trick):
    command: Incomplete
    stop_signal: Incomplete
    kill_after: Incomplete
    process: Incomplete
    process_watcher: Incomplete
    def __init__(
        self,
        command,
        patterns: Incomplete | None = ...,
        ignore_patterns: Incomplete | None = ...,
        ignore_directories: bool = ...,
        stop_signal=...,
        kill_after: int = ...,
    ) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def on_any_event(self, event) -> None: ...
