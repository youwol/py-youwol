# standard library
from pathlib import Path

# third parties
import custom_backend

# Youwol application
from youwol.app.environment import (
    Command,
    Configuration,
    CustomEndPoints,
    Customization,
)

# Youwol utilities
from youwol.utils.servers.fast_api import FastApiRouter

youwol_root = Path.home() / "Projects" / "youwol-open-source"

Configuration(
    customization=Customization(
        endPoints=CustomEndPoints(
            commands=[
                Command(
                    name="example", do_get=lambda ctx: ctx.info(text="GET:example")
                ),
                Command(
                    name="example",
                    do_post=lambda body, ctx: ctx.info(text="POST:example"),
                ),
                Command(
                    name="example", do_put=lambda ctx: ctx.info(text="PUT:example")
                ),
                Command(
                    name="example2",
                    do_delete=lambda ctx: ctx.info(text="DELETE:example2"),
                ),
            ],
            routers=[
                FastApiRouter(
                    router=custom_backend.get_router(
                        custom_backend.Configuration(some_property=42)
                    ),
                    base_path="/api/custom-backend",
                )
            ],
        )
    )
)
