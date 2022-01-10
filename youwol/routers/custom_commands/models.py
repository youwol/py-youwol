from typing import Callable, Union, Awaitable, Any

from pydantic import BaseModel

from youwol.context import Context

JSON = Any


class Command(BaseModel):
    name: str
    onTriggered: Callable[[JSON, Context], Union[Awaitable[JSON], JSON]]
