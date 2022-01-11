import asyncio
from typing import Optional, List
from starlette.requests import Request
from starlette.responses import Response

from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.context import Context
from starlette.middleware.base import RequestResponseEndpoint


class CustomDispatchesRule(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        dispatches: List[AbstractDispatch] = context.config.customDispatches
        responses = await asyncio.gather(*[
            d.apply(incoming_request=request, call_next=call_next, context=context) for d in dispatches
        ])
        return next((r for r in responses if r is not None), None)
