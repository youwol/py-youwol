from typing import List, Optional

from aiohttp import ClientSession
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol.middlewares.models_dispatch import DispatchInfo, is_localhost_ws_listening
from youwol.utils.utils_low_level import redirect_request
from youwol_utils import Context, encode_id, YouWolException, youwol_exception_handler
from youwol_utils.context import Label


class CustomMiddleware(BaseModel):

    async def dispatch(self,
                       incoming_request: Request,
                       call_next: RequestResponseEndpoint,
                       context: Context
                       ) -> Optional[Response]:
        raise NotImplementedError("CustomMiddleware.switch not implemented")


class FlowSwitch(BaseModel):

    async def info(self) -> DispatchInfo:
        return DispatchInfo(name=self.__str__(), activated=True,
                            parameters={"description": "no description provided ('info' method not overriden)"})

    async def is_matching(self, incoming_request: Request, context: Context) -> bool:
        raise NotImplementedError("FlowSwitchMiddleware.is_matching not implemented")

    async def switch(self,
                     incoming_request: Request,
                     context: Context
                     ) -> Optional[Response]:
        raise NotImplementedError("AbstractDispatch.switch not implemented")


class FlowSwitcherMiddleware(CustomMiddleware):

    name: str
    oneOf: List[FlowSwitch]

    async def dispatch(self,
                       incoming_request: Request,
                       call_next: RequestResponseEndpoint,
                       context: Context
                       ) -> Optional[Response]:

        async with context.start(
                action=f'FlowSwitcher: {self.name}',
                with_labels=[Label.MIDDLEWARE]
        ) as ctx:  # type: Context

            async with ctx.start(action=f"Get status of {len(self.oneOf)} switches"
                                 ) as ctx_status:  # type: Context
                matches = [d for d in self.oneOf if await d.is_matching(incoming_request=incoming_request,
                                                                        context=ctx_status)]
            if len(matches) > 1:
                raise RuntimeError("Multiple flow-switches match the incoming request")

            if not matches:
                await ctx.info(f"No match from the flow-switcher")
                return await call_next(incoming_request)

            try:
                response = await matches[0].switch(incoming_request=incoming_request, context=ctx)
            except YouWolException as e:
                return await youwol_exception_handler(incoming_request, e)

            await ctx.info(f"Got response from a flow-switcher")
            return response


class CdnSwitch(FlowSwitch):
    packageName: str
    port: Optional[int]

    async def info(self):
        return DispatchInfo(
            name=self.packageName,
            activated=is_localhost_ws_listening(self.port),
            parameters={
                'package': self.packageName,
                'redirected to':  f'localhost:{self.port}'
            })

    async def is_matching(self, incoming_request: Request, context: Context):
        if incoming_request.method != "GET":
            return False

        encoded_id = encode_id(self.packageName)

        if not (incoming_request.url.path.startswith(f"/api/assets-gateway/raw/package/{encoded_id}") or
                incoming_request.url.path.startswith(f"/api/cdn-backend/resources/{encoded_id}")):
            await context.info(text=f"CdnSwitch[{self}]: URL not matching",
                               data={"url": incoming_request.url.path, "encoded_id": encoded_id})
            return False

        if not is_localhost_ws_listening(self.port):
            await context.info(text=f"CdnSwitch[{self}]: ws not listening")
            return False

        await context.info(text=f"CdnSwitch[{self}]: MATCHING")
        return True

    async def switch(self,
                     incoming_request: Request,
                     context: Context) -> Optional[Response]:

        rest_of_path = incoming_request.url.path.split('/')[-1]
        url = f"http://localhost:{self.port}/{rest_of_path}"
        await context.info(text=f"CdnSwitch[{self}] execution",
                           data={"origin": incoming_request.url.path,
                                 "destination": url})

        async with ClientSession(auto_decompress=False) as session:
            async with await session.get(url=url) as resp:
                if resp.status != 200:
                    await context.error(text=f"CdnSwitch[{self}]: \
                        Bad status response while dispatching", data={
                        "origin": incoming_request.url.path,
                        "destination": url,
                        "status": resp.status
                    })
                    return None
                content = await resp.read()
                return Response(content=content, headers={k: v for k, v in resp.headers.items()})

    def __str__(self):
        return f"serving cdn package '{self.packageName}' from local port '{self.port}'"


class RedirectSwitch(FlowSwitch):

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

    async def is_matching(self, incoming_request: Request, context: Context):

        if not incoming_request.url.path.startswith(self.origin):
            await context.info(text=f"RedirectSwitch[{self}]: URL not matching",
                               data={"url": incoming_request.url.path})
            return None

        if not self.is_listening():
            await context.info(f"RedirectSwitch[{self}]: destination not listening -> proceed with no dispatch")
            return None

    async def switch(self,
                     incoming_request: Request,
                     context: Context) -> Optional[Response]:

        headers = {
            **{k: v for k, v in incoming_request.headers.items()},
            **context.headers()
        }

        await context.info(text=f"RedirectSwitch[{self}] execution",
                           data={"origin": incoming_request.url.path,
                                 "destination": self.destination})

        resp = await redirect_request(
            incoming_request=incoming_request,
            origin_base_path=self.origin,
            destination_base_path=self.destination,
            headers=headers
        )
        await context.info(
            f"Got response from dispatch",
            data={
                "headers": {k: v for k, v in resp.headers.items()},
                "status": resp.status_code
            }
        )
        return resp

    def __str__(self):
        return f"redirecting '{self.origin}' to '{self.destination}'"
