# third parties
from _typeshed import Incomplete
from watchdog.events import DirCreatedEvent as DirCreatedEvent
from watchdog.events import DirDeletedEvent as DirDeletedEvent
from watchdog.events import DirModifiedEvent as DirModifiedEvent
from watchdog.events import DirMovedEvent as DirMovedEvent
from watchdog.events import FileCreatedEvent as FileCreatedEvent
from watchdog.events import FileDeletedEvent as FileDeletedEvent
from watchdog.events import FileModifiedEvent as FileModifiedEvent
from watchdog.events import FileMovedEvent as FileMovedEvent
from watchdog.events import generate_sub_created_events as generate_sub_created_events
from watchdog.events import generate_sub_moved_events as generate_sub_moved_events
from watchdog.observers.api import DEFAULT_EMITTER_TIMEOUT as DEFAULT_EMITTER_TIMEOUT
from watchdog.observers.api import DEFAULT_OBSERVER_TIMEOUT as DEFAULT_OBSERVER_TIMEOUT
from watchdog.observers.api import BaseObserver as BaseObserver
from watchdog.observers.api import EventEmitter as EventEmitter
from watchdog.utils.dirsnapshot import DirectorySnapshot as DirectorySnapshot

logger: Incomplete

class FSEventsEmitter(EventEmitter):
    suppress_history: Incomplete
    def __init__(
        self, event_queue, watch, timeout=..., suppress_history: bool = ...
    ) -> None: ...
    def on_thread_stop(self) -> None: ...
    def queue_event(self, event) -> None: ...
    def queue_events(self, timeout, events) -> None: ...
    def events_callback(self, paths, inodes, flags, ids) -> None: ...
    pathnames: Incomplete
    def run(self) -> None: ...
    def on_thread_start(self) -> None: ...

class FSEventsObserver(BaseObserver):
    def __init__(self, timeout=...) -> None: ...
    def schedule(self, event_handler, path, recursive: bool = ...): ...
