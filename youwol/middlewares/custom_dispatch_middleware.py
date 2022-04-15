import asyncio
from typing import Optional, List, cast

from starlette.middleware.base import RequestResponseEndpoint, BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol_utils import to_json, YouWolException, youwol_exception_handler
from youwol_utils.context import Context, Label


class CustomDispatchesMiddleware(BaseHTTPMiddleware):

    async def dispatch(self,
                       request: Request,
                       call_next: RequestResponseEndpoint,
                       ) -> Optional[Response]:

        async with Context.from_request(request).start(
                action='Custom dispatch middleware',
                with_labels=[Label.MIDDLEWARE]
        ) as ctx:
            env = await ctx.get('env', YouwolEnvironment)
            dispatches: List[AbstractDispatch] = env.customDispatches
            await ctx.info('list of custom dispatch', data={'dispatches': [to_json(d) for d in dispatches]})

            try:
                responses = await asyncio.gather(*[
                    d.apply(incoming_request=request, call_next=call_next, context=ctx) for d in dispatches
                ])
            except YouWolException as e:
                return await youwol_exception_handler(request, e)

            index, resp = next(((i, r) for i, r in enumerate(responses) if r is not None), (-1, None))
            if resp:
                await ctx.info(f"Got response from dispatch '{dispatches[index]}'", data=dispatches[index])
                return cast(Response, resp)

            return await call_next(request)
