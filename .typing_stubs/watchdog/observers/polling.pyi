from watchdog.events import DirCreatedEvent as DirCreatedEvent, DirDeletedEvent as DirDeletedEvent, DirModifiedEvent as DirModifiedEvent, DirMovedEvent as DirMovedEvent, FileCreatedEvent as FileCreatedEvent, FileDeletedEvent as FileDeletedEvent, FileModifiedEvent as FileModifiedEvent, FileMovedEvent as FileMovedEvent
from watchdog.observers.api import BaseObserver as BaseObserver, DEFAULT_EMITTER_TIMEOUT as DEFAULT_EMITTER_TIMEOUT, DEFAULT_OBSERVER_TIMEOUT as DEFAULT_OBSERVER_TIMEOUT, EventEmitter as EventEmitter
from watchdog.utils.dirsnapshot import DirectorySnapshot as DirectorySnapshot, DirectorySnapshotDiff as DirectorySnapshotDiff

class PollingEmitter(EventEmitter):
    def __init__(self, event_queue, watch, timeout=..., stat=..., listdir=...) -> None: ...
    def on_thread_start(self) -> None: ...
    def queue_events(self, timeout) -> None: ...

class PollingObserver(BaseObserver):
    def __init__(self, timeout=...) -> None: ...

class PollingObserverVFS(BaseObserver):
    def __init__(self, stat, listdir, polling_interval: int = ...) -> None: ...