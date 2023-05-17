from .aiter_utils import AsyncExitStack as AsyncExitStack, anext as anext
from .core import streamcontext as streamcontext
from _typeshed import Incomplete

class TaskGroup:
    def __init__(self) -> None: ...
    async def __aenter__(self): ...
    async def __aexit__(self, *args) -> None: ...
    def create_task(self, coro): ...
    async def wait_any(self, tasks): ...
    async def wait_all(self, tasks): ...
    async def cancel_task(self, task) -> None: ...

class StreamerManager:
    tasks: Incomplete
    streamers: Incomplete
    group: Incomplete
    stack: Incomplete
    def __init__(self) -> None: ...
    async def __aenter__(self): ...
    async def __aexit__(self, *args): ...
    async def enter_and_create_task(self, aiter): ...
    def create_task(self, streamer) -> None: ...
    async def wait_single_event(self, filters): ...
    async def clean_streamer(self, streamer) -> None: ...
    async def clean_streamers(self, streamers) -> None: ...
