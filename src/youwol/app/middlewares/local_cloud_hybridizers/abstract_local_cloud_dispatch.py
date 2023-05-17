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
    async def info(self) -> DispatchInfo:
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
        If return a response => shortcut remaining of the processing pipeline.
        If return None => proceeds the remaining pipeline
        """
        raise NotImplementedError("AbstractDispatch.dispatch not implemented")
