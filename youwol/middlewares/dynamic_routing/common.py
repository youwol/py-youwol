from abc import ABC, abstractmethod
from starlette.responses import Response
from starlette.requests import Request

from starlette.middleware.base import RequestResponseEndpoint
from context import Context


class DispatchingRule(ABC):

    @abstractmethod
    async def is_matching(self, request: Request, context: Context) -> bool:
        pass

    @abstractmethod
    async def apply(self, request: Request, call_next: RequestResponseEndpoint, context: Context) -> Response:
        pass
