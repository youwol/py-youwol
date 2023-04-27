from _typeshed import Incomplete
from threading import Thread
from watchdog.events import DirCreatedEvent as DirCreatedEvent, DirDeletedEvent as DirDeletedEvent, DirModifiedEvent as DirModifiedEvent, DirMovedEvent as DirMovedEvent, FileCreatedEvent as FileCreatedEvent, FileDeletedEvent as FileDeletedEvent, FileModifiedEvent as FileModifiedEvent, FileMovedEvent as FileMovedEvent
from watchdog.observers.api import BaseObserver as BaseObserver, DEFAULT_EMITTER_TIMEOUT as DEFAULT_EMITTER_TIMEOUT, DEFAULT_OBSERVER_TIMEOUT as DEFAULT_OBSERVER_TIMEOUT, EventEmitter as EventEmitter

logger: Incomplete

class FSEventsQueue(Thread):
    def __init__(self, path) -> None: ...
    def run(self) -> None: ...
    def stop(self) -> None: ...
    def read_events(self): ...

class NativeEvent:
    path: Incomplete
    flags: Incomplete
    event_id: Incomplete
    is_created: Incomplete
    is_removed: Incomplete
    is_renamed: Incomplete
    is_modified: Incomplete
    is_change_owner: Incomplete
    is_inode_meta_mod: Incomplete
    is_finder_info_mod: Incomplete
    is_xattr_mod: Incomplete
    is_symlink: Incomplete
    is_directory: Incomplete
    def __init__(self, path, flags, event_id) -> None: ...

class FSEventsEmitter(EventEmitter):
    def __init__(self, event_queue, watch, timeout=...) -> None: ...
    def on_thread_stop(self) -> None: ...
    def queue_events(self, timeout) -> None: ...

class FSEventsObserver2(BaseObserver):
    def __init__(self, timeout=...) -> None: ...
