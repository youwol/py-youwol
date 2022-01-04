import asyncio
from typing import List, Optional

from aiohttp import ClientSession, ClientConnectorError
from pydantic import BaseModel

from youwol_utils import encode_id, log_info
from .common import DispatchingRule
from youwol.context import Context


from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .redirect import redirect_request


class AbstractDispatch(BaseModel):

    async def is_matching(self, incoming_request: Request, context: Context) -> bool:
        raise NotImplementedError("AbstractDispatch.is_matching not implemented")

    async def dispatch(self, incoming_request: Request, context: Context):
        raise NotImplementedError("AbstractDispatch.dispatch not implemented")


class RedirectDispatch(AbstractDispatch):

    origin: str
    destination: str

    async def is_matching(self, incoming_request: Request, context: Context):
        return incoming_request.url.path.startswith(self.origin)

    async def dispatch(self, incoming_request: Request, context: Context):
        return await redirect_request(
            incoming_request=incoming_request,
            origin_base_path=self.origin,
            destination_base_path=self.destination,
        )

    def __str__(self):
        return f"redirecting '{self.origin}' to '{self.destination}'"


class CdnOverride(AbstractDispatch):

    package_name: str
    port: int

    async def is_matching(self, incoming_request: Request, context: Context) -> bool:
        if incoming_request.method != "GET":
            return False

        encoded_id = encode_id(self.package_name)

        # When serving a package through live server we intercept 2 routes:
        # - in any case the 'low-level' call to cdn-backend is intercepted
        # - the higher level call through assets-gateway is also intercepted such that permission call is skipped
        # (the package may not be published yet)
        if not(incoming_request.url.path.startswith(f"/api/assets-gateway/raw/package/{encoded_id}") or
               incoming_request.url.path.startswith(f"/api/cdn-backend/resources/{encoded_id}")):
            return False

        rest_of_path = incoming_request.url.path.split('/')[-1]
        url = f"http://localhost:{self.port}/{rest_of_path}"
        try:
            # Try to connect to a dev server
            async with ClientSession(auto_decompress=False) as session:
                async with await session.get(url=url) as resp:
                    return resp.status == 200
        except ClientConnectorError:
            return False

    async def dispatch(self, incoming_request: Request, context: Context):
        rest_of_path = incoming_request.url.path.split('/')[-1]
        url = f"http://localhost:{self.port}/{rest_of_path}"
        async with ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url) as resp:
                content = await resp.read()
                return Response(content=content, headers={k: v for k, v in resp.headers.items()})

    def __str__(self):
        return f"serving cdn package '{self.package_name}' from local port '{self.port}'"


class CustomDispatchesRule(DispatchingRule):

    @staticmethod
    async def get_dispatch(request: Request, context: Context) -> Optional[AbstractDispatch]:

        dispatches: List[AbstractDispatch] = context.config.customDispatches
        matches = await asyncio.gather(*[d.is_matching(incoming_request=request, context=context)
                                         for d in dispatches])
        return next((d for d, m in zip(dispatches, matches) if m), None)

    async def is_matching(self, request: Request, context: Context) -> bool:

        dispatch = await CustomDispatchesRule.get_dispatch(request=request, context=context)
        return dispatch is not None

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Response:

        dispatch = await CustomDispatchesRule.get_dispatch(request=request, context=context)
        log_info(f"Calling dispatch: {dispatch}")
        return await dispatch.dispatch(incoming_request=request, context=context)
