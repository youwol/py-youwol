# standard library
import itertools

from collections.abc import Awaitable
from dataclasses import dataclass

# typing
from typing import Any, Callable, Optional, Union

# third parties
from fastapi import APIRouter
from pydantic import BaseConfig, BaseModel, create_model
from starlette.middleware.base import BaseHTTPMiddleware

# Youwol utilities
from youwol.utils.context import Context

flatten = itertools.chain.from_iterable

BaseConfig.arbitrary_types_allowed = True


class FastApiRouter(BaseModel):
    """
    Define a router using the fast-api library.

    **Attributes**:

    - **router** an :class:`APIRouter` or a function returning an :class:`APIRouter` (eventually awaitable)
    Defines the :class:`APIRouter`, see fast-api documentation.

    - **base_path** :class:`str`
    Base path from which the router is served.

    *Default to empty string*"""

    router: Union[
        APIRouter, Callable[[Context], Union[APIRouter, Awaitable[APIRouter]]]
    ]
    base_path: Optional[str] = ""
    __pydantic_model__ = create_model("FastApiRouter")


@dataclass(frozen=True)
class FastApiMiddleware:
    middleware: type[BaseHTTPMiddleware]
    args: dict[str, Any]
