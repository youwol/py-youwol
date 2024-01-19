# third parties
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
from watchdog.observers.winapi import close_directory_handle as close_directory_handle
from watchdog.observers.winapi import get_directory_handle as get_directory_handle
from watchdog.observers.winapi import read_events as read_events

WATCHDOG_TRAVERSE_MOVED_DIR_DELAY: int

class WindowsApiEmitter(EventEmitter):
    def __init__(self, event_queue, watch, timeout=...) -> None: ...
    def on_thread_start(self) -> None: ...
    def start(self) -> None: ...
    def on_thread_stop(self) -> None: ...
    def queue_events(self, timeout) -> None: ...

class WindowsApiObserver(BaseObserver):
    def __init__(self, timeout=...) -> None: ...
