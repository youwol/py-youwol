# typing
from typing import Optional

# third parties
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import DispatchInfo

# Youwol utilities
from youwol.utils.context import Context


class AbstractLocalCloudDispatch(BaseModel):
    """
    Abstract class that defines local/cloud dispatch behavior: some actions that requires
    HTTP call to the remote environment to proceed.
    """

    async def info(self) -> DispatchInfo:
        """
        Default implementation of a dispatch info.

        Return:
            The Dispatch information
        """
        return DispatchInfo(
            name=str(self),
            activated=True,
            parameters={"description": "no 'status' method defined"},
        )

    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Optional[Response]:
        """
        Interface definition of the virtual method.

        Parameters:
            incoming_request: The incoming request
            call_next: The ext endpoint in the chain
            context: Current context

        Return:
            The response after applying the dispatch, or `None` if the incoming request is not a match for the
            dispatch.
        """
        raise NotImplementedError("AbstractDispatch.dispatch not implemented")
