from _typeshed import Incomplete
from lockfile.pidlockfile import PIDLockFile

class TimeoutPIDLockFile(PIDLockFile):
    acquire_timeout: Incomplete
    def __init__(self, path, acquire_timeout: Incomplete | None = ..., *args, **kwargs) -> None: ...
    def acquire(self, timeout: Incomplete | None = ..., *args, **kwargs) -> None: ...
