# third parties
from _typeshed import Incomplete

PLATFORM_WINDOWS: str
PLATFORM_LINUX: str
PLATFORM_BSD: str
PLATFORM_DARWIN: str
PLATFORM_UNKNOWN: str

def get_platform_name(): ...

__platform__: Incomplete

def is_linux(): ...
def is_bsd(): ...
def is_darwin(): ...
def is_windows(): ...
