import asyncio
from typing import Optional, List

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol_utils.context import Context


class CustomDispatchesRule(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        env = await context.get('env', YouwolEnvironment)
        dispatches: List[AbstractDispatch] = env.customDispatches
        responses = await asyncio.gather(*[
            d.apply(incoming_request=request, call_next=call_next, context=context) for d in dispatches
        ])
        return next((r for r in responses if r is not None), None)
