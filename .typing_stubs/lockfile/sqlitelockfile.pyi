# third parties
from _typeshed import Incomplete

# relative
from . import AlreadyLocked as AlreadyLocked
from . import LockBase as LockBase
from . import LockTimeout as LockTimeout
from . import NotLocked as NotLocked
from . import NotMyLock as NotMyLock

unicode = str

class SQLiteLockFile(LockBase):
    testdb: Incomplete
    lock_file: Incomplete
    unique_name: Incomplete
    connection: Incomplete
    def __init__(
        self, path, threaded: bool = ..., timeout: Incomplete | None = ...
    ) -> None: ...
    def acquire(self, timeout: Incomplete | None = ...) -> None: ...
    def release(self) -> None: ...
    def is_locked(self): ...
    def i_am_locking(self): ...
    def break_lock(self) -> None: ...
