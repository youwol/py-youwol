import socket
from typing import Optional, Dict

from aiohttp import ClientSession
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol.utils.utils_low_level import redirect_request
from youwol_utils import encode_id
from youwol_utils.context import Context


class DispatchInfo(BaseModel):
    name: str
    activated: Optional[bool]
    parameters: Optional[Dict[str, str]]


class AbstractDispatch(BaseModel):

    async def info(self) -> DispatchInfo:
        return DispatchInfo(name=self.__str__(), activated=True,
                            parameters={"description": "no 'status' method defined"})

    async def apply(self,
                    incoming_request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context) -> Optional[Response]:
        """
        If return a response => shortcut remaining of the processing pipeline.
        If return None => proceeds the remaining pipeline
        """
        raise NotImplementedError("AbstractDispatch.dispatch not implemented")


def is_localhost_ws_listening(port: int):
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    location = ('localhost', port)
    return a_socket.connect_ex(location) == 0


class RedirectDispatch(AbstractDispatch):
    origin: str
    destination: str

    def is_listening(self):
        return is_localhost_ws_listening(int(self.destination.split(':')[-1]))

    async def info(self) -> DispatchInfo:
        return DispatchInfo(
            name=self.origin,
            activated=self.is_listening(),
            parameters={
                'from url': self.origin,
                'redirected to': self.destination
            })

    async def apply(self,
                    incoming_request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context) -> Optional[Response]:
        if not incoming_request.url.path.startswith(self.origin):
            return None

        if not self.is_listening():
            await context.info(f"Dispatch {self} not listening -> proceed with no dispatch")
            return None

        async with context.start(action=self.__str__()) as ctx:  # type: Context

            headers = {
                **{k: v for k, v in incoming_request.headers.items()},
                **ctx.headers()
            }
            await ctx.info(
                "incoming request",
                data={
                    "headers": headers,
                    "method": incoming_request.method,
                    "url": incoming_request.url.path
                }
            )
            resp = await redirect_request(
                incoming_request=incoming_request,
                origin_base_path=self.origin,
                destination_base_path=self.destination,
                headers=headers
            )
            await ctx.info(
                f"Got response from dispatch",
                data={
                    "headers": {k: v for k, v in resp.headers.items()},
                    "status": resp.status_code
                }
            )
            return resp

    def __str__(self):
        return f"redirecting '{self.origin}' to '{self.destination}'"


class CdnOverrideDispatch(AbstractDispatch):
    packageName: str
    port: int

    async def info(self):
        return DispatchInfo(
            name=self.packageName,
            activated=is_localhost_ws_listening(self.port),
            parameters={
                'package': self.packageName,
                'redirected to':  f'localhost:{self.port}'
            })

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
        if not (incoming_request.url.path.startswith(f"/api/assets-gateway/raw/package/{encoded_id}") or
                incoming_request.url.path.startswith(f"/api/cdn-backend/resources/{encoded_id}")):
            return None
        rest_of_path = incoming_request.url.path.split('/')[-1]
        url = f"http://localhost:{self.port}/{rest_of_path}"
        await context.info(text=f"CdnOverrideDispatch[{self}] matched",
                           data={"origin": incoming_request.url.path,
                                 "destination": url})
        if not is_localhost_ws_listening(self.port):
            await context.info(text=f"CdnOverrideDispatch[{self}] not listening")
            return None

        async with ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url) as resp:
                if resp.status != 200:
                    await context.error(text=f"CdnOverrideDispatch[{self}]: \
                        Bad status response while dispatching", data={
                        "origin": incoming_request.url.path,
                        "destination": url,
                        "status": resp.status
                    })
                    return None
                return await self.dispatch(incoming_request=incoming_request)

    async def dispatch(self, incoming_request: Request) -> Response:
        rest_of_path = incoming_request.url.path.split('/')[-1]
        url = f"http://localhost:{self.port}/{rest_of_path}"
        async with ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url) as resp:
                content = await resp.read()
                return Response(content=content, headers={k: v for k, v in resp.headers.items()})

    def __str__(self):
        return f"serving cdn package '{self.packageName}' from local port '{self.port}'"
