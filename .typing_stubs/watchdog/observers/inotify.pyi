# third parties
from watchdog.events import DirCreatedEvent as DirCreatedEvent
from watchdog.events import DirDeletedEvent as DirDeletedEvent
from watchdog.events import DirModifiedEvent as DirModifiedEvent
from watchdog.events import DirMovedEvent as DirMovedEvent
from watchdog.events import FileClosedEvent as FileClosedEvent
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

# relative
from .inotify_buffer import InotifyBuffer as InotifyBuffer

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
