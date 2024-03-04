# standard library
from pathlib import Path

# third parties
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request

# Youwol application
from youwol.app.environment import (
    CdnSwitch,
    Configuration,
    Customization,
    CustomMiddleware,
    FlowSwitcherMiddleware,
    RedirectSwitch,
)

# Youwol utilities
from youwol.utils.context import Context, Label

youwol_root = Path.home() / "Projects" / "youwol-open-source"


class HelloMiddleware(CustomMiddleware):
    name = "HelloMiddleware"

    async def dispatch(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ):
        async with context.start(
            action="HelloMiddleware.dispatch", with_labels=[Label.MIDDLEWARE]
        ) as ctx:  # type: Context
            await ctx.info("Hello")
            return await call_next(incoming_request)


portsBookBacks = {"foo-backend": 4001}

portsBookFronts = {"@youwol/foo-app": 3000}


Configuration(
    customization=Customization(
        middlewares=[
            # Hello middleware will be called first
            HelloMiddleware(),
            # Eventually the request's processing flow will be re-routed to a front live-server
            FlowSwitcherMiddleware(
                name="Frontend servers",
                oneOf=[
                    CdnSwitch(packageName=name, port=port)
                    for name, port in portsBookFronts.items()
                ],
            ),
            # If no catch from the last middleware, eventually the request's processing flow will be re-routed
            # to a back live-server
            FlowSwitcherMiddleware(
                name="Backend servers",
                oneOf=[
                    RedirectSwitch(
                        origin=f"/api/{name}", destination=f"http://localhost:{port}"
                    )
                    for name, port in portsBookBacks.items()
                ],
            ),
        ],
    )
)
