# standard library
from collections.abc import Generator

# third parties
from _typeshed import Incomplete
from watchdog.utils.patterns import match_any_paths as match_any_paths

EVENT_TYPE_MOVED: str
EVENT_TYPE_DELETED: str
EVENT_TYPE_CREATED: str
EVENT_TYPE_MODIFIED: str
EVENT_TYPE_CLOSED: str

class FileSystemEvent:
    event_type: Incomplete
    is_directory: bool
    is_synthetic: bool
    def __init__(self, src_path) -> None: ...
    @property
    def src_path(self): ...
    @property
    def key(self): ...
    def __eq__(self, event): ...
    def __ne__(self, event): ...
    def __hash__(self): ...

class FileSystemMovedEvent(FileSystemEvent):
    event_type = EVENT_TYPE_MOVED
    def __init__(self, src_path, dest_path) -> None: ...
    @property
    def dest_path(self): ...
    @property
    def key(self): ...

class FileDeletedEvent(FileSystemEvent):
    event_type = EVENT_TYPE_DELETED

class FileModifiedEvent(FileSystemEvent):
    event_type = EVENT_TYPE_MODIFIED

class FileCreatedEvent(FileSystemEvent):
    event_type = EVENT_TYPE_CREATED

class FileMovedEvent(FileSystemMovedEvent): ...

class FileClosedEvent(FileSystemEvent):
    event_type = EVENT_TYPE_CLOSED

class DirDeletedEvent(FileSystemEvent):
    event_type = EVENT_TYPE_DELETED
    is_directory: bool

class DirModifiedEvent(FileSystemEvent):
    event_type = EVENT_TYPE_MODIFIED
    is_directory: bool

class DirCreatedEvent(FileSystemEvent):
    event_type = EVENT_TYPE_CREATED
    is_directory: bool

class DirMovedEvent(FileSystemMovedEvent):
    is_directory: bool

class FileSystemEventHandler:
    def dispatch(self, event) -> None: ...
    def on_any_event(self, event) -> None: ...
    def on_moved(self, event) -> None: ...
    def on_created(self, event) -> None: ...
    def on_deleted(self, event) -> None: ...
    def on_modified(self, event) -> None: ...
    def on_closed(self, event) -> None: ...

class PatternMatchingEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        patterns: Incomplete | None = ...,
        ignore_patterns: Incomplete | None = ...,
        ignore_directories: bool = ...,
        case_sensitive: bool = ...,
    ) -> None: ...
    @property
    def patterns(self): ...
    @property
    def ignore_patterns(self): ...
    @property
    def ignore_directories(self): ...
    @property
    def case_sensitive(self): ...
    def dispatch(self, event) -> None: ...

class RegexMatchingEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        regexes: Incomplete | None = ...,
        ignore_regexes: Incomplete | None = ...,
        ignore_directories: bool = ...,
        case_sensitive: bool = ...,
    ) -> None: ...
    @property
    def regexes(self): ...
    @property
    def ignore_regexes(self): ...
    @property
    def ignore_directories(self): ...
    @property
    def case_sensitive(self): ...
    def dispatch(self, event) -> None: ...

class LoggingEventHandler(FileSystemEventHandler):
    logger: Incomplete
    def __init__(self, logger: Incomplete | None = ...) -> None: ...
    def on_moved(self, event) -> None: ...
    def on_created(self, event) -> None: ...
    def on_deleted(self, event) -> None: ...
    def on_modified(self, event) -> None: ...

def generate_sub_moved_events(
    src_dir_path, dest_dir_path
) -> Generator[Incomplete, None, None]: ...
def generate_sub_created_events(src_dir_path) -> Generator[Incomplete, None, None]: ...
