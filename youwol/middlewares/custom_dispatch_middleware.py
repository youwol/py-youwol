import asyncio
from typing import Optional, List, cast

from starlette.middleware.base import RequestResponseEndpoint, BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol_utils import to_json
from youwol_utils.context import Context


class CustomDispatchesMiddleware(BaseHTTPMiddleware):

    async def dispatch(self,
                       request: Request,
                       call_next: RequestResponseEndpoint,
                       ) -> Optional[Response]:

        context: Context = request.state.context
        async with context.start(action='Custom dispatch middleware') as ctx:
            env = await context.get('env', YouwolEnvironment)
            dispatches: List[AbstractDispatch] = env.customDispatches
            ctx.info('list of custom dispatch', data={'dispatches': [to_json(d) for d in dispatches]})
            responses = await asyncio.gather(*[
                d.apply(incoming_request=request, call_next=call_next, context=context) for d in dispatches
            ])
            resp = next((r for r in responses if r is not None), None)
            if resp:
                return cast(Response, resp)

            request.state.context = ctx
            return await call_next(request)
