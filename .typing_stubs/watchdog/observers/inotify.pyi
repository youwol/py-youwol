from .inotify_buffer import InotifyBuffer as InotifyBuffer
from watchdog.events import DirCreatedEvent as DirCreatedEvent, DirDeletedEvent as DirDeletedEvent, DirModifiedEvent as DirModifiedEvent, DirMovedEvent as DirMovedEvent, FileClosedEvent as FileClosedEvent, FileCreatedEvent as FileCreatedEvent, FileDeletedEvent as FileDeletedEvent, FileModifiedEvent as FileModifiedEvent, FileMovedEvent as FileMovedEvent, generate_sub_created_events as generate_sub_created_events, generate_sub_moved_events as generate_sub_moved_events
from watchdog.observers.api import BaseObserver as BaseObserver, DEFAULT_EMITTER_TIMEOUT as DEFAULT_EMITTER_TIMEOUT, DEFAULT_OBSERVER_TIMEOUT as DEFAULT_OBSERVER_TIMEOUT, EventEmitter as EventEmitter

class InotifyEmitter(EventEmitter):
    def __init__(self, event_queue, watch, timeout=...) -> None: ...
    def on_thread_start(self) -> None: ...
    def on_thread_stop(self) -> None: ...
    def queue_events(self, timeout, full_events: bool = ...) -> None: ...

class InotifyFullEmitter(InotifyEmitter):
    def __init__(self, event_queue, watch, timeout=...) -> None: ...
    def queue_events(self, timeout, events: bool = ...) -> None: ...

class InotifyObserver(BaseObserver):
    def __init__(self, timeout=..., generate_full_events: bool = ...) -> None: ...