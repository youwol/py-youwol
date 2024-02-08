# standard library
import itertools

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

# typing
from typing import Any

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
    Defines a router using the fast-api library.
    """

    router: APIRouter | Callable[[Context], APIRouter | Awaitable[APIRouter]]
    """
    Defines the router.
    """

    base_path: str | None = ""
    """
    Defines the base path from which the router is served.
    """

    __pydantic_model__ = create_model("FastApiRouter")


@dataclass(frozen=True)
class FastApiMiddleware:
    middleware: type[BaseHTTPMiddleware]
    args: dict[str, Any]
