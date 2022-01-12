from typing import Callable, Union, Awaitable, Any, Optional

from pydantic import BaseModel

from youwol_utils.context import Context

JSON = Any


class Command(BaseModel):
    name: str
    do_get: Optional[Callable[[Context], Union[Awaitable[JSON], JSON]]] = None
    do_post: Optional[Callable[[JSON, Context], Union[Awaitable[JSON], JSON]]] = None
    do_put: Optional[Callable[[JSON, Context], Union[Awaitable[JSON], JSON]]] = None
    do_delete: Optional[Callable[[Context], Union[Awaitable[JSON], JSON]]] = None
