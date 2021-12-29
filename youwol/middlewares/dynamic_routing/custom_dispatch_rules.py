import asyncio
from typing import List, Optional

from configuration import AbstractDispatch
from .common import DispatchingRule
from youwol.context import Context


from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class CustomDispatchesRule(DispatchingRule):

    @staticmethod
    async def get_dispatch(request: Request, context: Context) -> Optional[AbstractDispatch]:

        dispatches: List[AbstractDispatch] = context.config.userConfig.customDispatches
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
        return await dispatch.dispatch(incoming_request=request, context=context)
