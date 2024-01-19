# third parties
from watchdog.events import DirCreatedEvent as DirCreatedEvent
from watchdog.events import DirDeletedEvent as DirDeletedEvent
from watchdog.events import DirModifiedEvent as DirModifiedEvent
from watchdog.events import DirMovedEvent as DirMovedEvent
from watchdog.events import FileCreatedEvent as FileCreatedEvent
from watchdog.events import FileDeletedEvent as FileDeletedEvent
from watchdog.events import FileModifiedEvent as FileModifiedEvent
from watchdog.events import FileMovedEvent as FileMovedEvent
from watchdog.observers.api import DEFAULT_EMITTER_TIMEOUT as DEFAULT_EMITTER_TIMEOUT
from watchdog.observers.api import DEFAULT_OBSERVER_TIMEOUT as DEFAULT_OBSERVER_TIMEOUT
from watchdog.observers.api import BaseObserver as BaseObserver
from watchdog.observers.api import EventEmitter as EventEmitter
from watchdog.utils.dirsnapshot import DirectorySnapshot as DirectorySnapshot
from watchdog.utils.dirsnapshot import DirectorySnapshotDiff as DirectorySnapshotDiff

class PollingEmitter(EventEmitter):
    def __init__(
        self, event_queue, watch, timeout=..., stat=..., listdir=...
    ) -> None: ...
    def on_thread_start(self) -> None: ...
    def queue_events(self, timeout) -> None: ...

class PollingObserver(BaseObserver):
    def __init__(self, timeout=...) -> None: ...

class PollingObserverVFS(BaseObserver):
    def __init__(self, stat, listdir, polling_interval: int = ...) -> None: ...
