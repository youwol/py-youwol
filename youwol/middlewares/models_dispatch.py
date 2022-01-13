from typing import Optional

from aiohttp import ClientSession, ClientConnectorError
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol.utils_low_level import redirect_request
from youwol_utils import encode_id
from youwol_utils.context import Context


class AbstractDispatch(BaseModel):

    async def apply(self,
                    incoming_request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context) -> Optional[Response]:
        """
        If return a response => shortcut remaining of the processing pipeline.
        If return None => proceeds the remaining pipeline
        """
        raise NotImplementedError("AbstractDispatch.dispatch not implemented")


class RedirectDispatch(AbstractDispatch):

    origin: str
    destination: str

    async def apply(self,
                    incoming_request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context) -> Optional[Response]:

        if not incoming_request.url.path.startswith(self.origin):
            return None

        return await redirect_request(
            incoming_request=incoming_request,
            origin_base_path=self.origin,
            destination_base_path=self.destination,
        )

    def __str__(self):
        return f"redirecting '{self.origin}' to '{self.destination}'"


class CdnOverrideDispatch(AbstractDispatch):

    packageName: str
    port: int

    async def apply(self,
                    incoming_request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context) -> Optional[Response]:
        if incoming_request.method != "GET":
            return None

        encoded_id = encode_id(self.packageName)

        # When serving a package through live server we intercept 2 routes:
        # - in any case the 'low-level' call to cdn-backend is intercepted
        # - the higher level call through assets-gateway is also intercepted such that permission call is skipped
        # (the package may not be published yet)
        if not(incoming_request.url.path.startswith(f"/api/assets-gateway/raw/package/{encoded_id}") or
               incoming_request.url.path.startswith(f"/api/cdn-backend/resources/{encoded_id}")):
            return None

        rest_of_path = incoming_request.url.path.split('/')[-1]
        url = f"http://localhost:{self.port}/{rest_of_path}"
        try:
            # Try to connect to a dev server
            async with ClientSession(auto_decompress=False) as session:
                async with await session.get(url=url) as resp:
                    if resp.status != 200:
                        return None
                    return await self.dispatch(incoming_request=incoming_request)
        except ClientConnectorError:
            return None

    async def dispatch(self, incoming_request: Request) -> Response:
        rest_of_path = incoming_request.url.path.split('/')[-1]
        url = f"http://localhost:{self.port}/{rest_of_path}"
        async with ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url) as resp:
                content = await resp.read()
                return Response(content=content, headers={k: v for k, v in resp.headers.items()})

    def __str__(self):
        return f"serving cdn package '{self.packageName}' from local port '{self.port}'"
