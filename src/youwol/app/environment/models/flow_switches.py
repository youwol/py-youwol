# typing
from typing import Optional

# third parties
from aiohttp import ClientSession
from aiohttp.web_request import Request
from pydantic import BaseModel
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

# Youwol application
from youwol.app.environment.models.models_config import CustomMiddleware
from youwol.app.environment.youwol_environment import YouwolEnvironment

# Youwol utilities
from youwol.utils import (
    Context,
    Label,
    ResourcesNotFoundException,
    YouWolException,
    YouwolHeaders,
    encode_id,
    is_server_http_alive,
    redirect_request,
    youwol_exception_handler,
)


class DispatchInfo(BaseModel):
    """
    Summary of the state of a [FlowSwitch](@yw-nav-class:youwol.app.environment.models.models_config.FlowSwitch)
    (used as displayed info).
    """

    name: str
    """
    Name of the switch.
    """

    activated: bool
    """
    Whether the switch is actually applicable or not (e.g. dev-server listening or not).
    """

    parameters: dict[str, str] = {}
    """
    Some relevant parameters to display, as a dictionary using parameter's name as key.
    """


class FlowSwitch(BaseModel):
    """
    Abstract class used in
    [FlowSwitcherMiddleware](@yw-nav-class:youwol.app.environment.models.models_config.FlowSwitcherMiddleware),
     to provides the ability to interrupt the normal flow of a request by redirecting it to another target end-point.

    In youwol, it is implemented in:

    *  [CdnSwitch](@yw-nav-class:youwol.app.environment.models.models_config.CdnSwitch): redirect request to a package
    normally served from the CDN to a particular port from `localhost`.
    *  [RedirectSwitch](@yw-nav-class:youwol.app.environment.models.models_config.RedirectSwitch): redirect an HTTP call
    from a given destination to a particular port from `localhost`.

    Derived classes should provide implementation for the methods **info**, **is_matching** and **switch**.
    """

    async def info(self) -> DispatchInfo:
        """
        Get display info of the dispatch.
        """
        return DispatchInfo(
            name=str(self),
            activated=True,
            parameters={
                "description": "no description provided ('info' method not overriden)"
            },
        )

    async def is_matching(self, incoming_request: Request, context: Context) -> bool:
        """
        This method should return whether a particular request should be intercepted.

        Parameters:
            incoming_request: incoming [request](https://fastapi.tiangolo.com/reference/request/)
            context: current [context](@yw-nav-class:youwol.utils.context.Context)
        Return:
            `True` if the switch match against the request, `False` otherwise
        """
        raise NotImplementedError("FlowSwitchMiddleware.is_matching not implemented")

    async def switch(
        self, incoming_request: Request, context: Context
    ) -> Optional[Response]:
        """
        Implementation logic of the switch.

        Parameters:
            incoming_request: incoming [request](https://fastapi.tiangolo.com/reference/request/)
            context: current [context](@yw-nav-class:youwol.utils.context.Context)
        Return:
            The response
        """
        raise NotImplementedError("AbstractDispatch.switch not implemented")


class FlowSwitcherMiddleware(CustomMiddleware):
    """
    This middleware will eventually switch from an original targeted end-point to another destination if
    one, and only one, [oneOf](@yw-nav-attr:youwol.app.environment.models.models_config.FlowSwitcherMiddleware.oneOf)
     element match against the original request.

     Example:
        ```python hl_lines="5-7 9-16 22-29"
        from youwol.app.environment import (
            Configuration,
            Customization,
            CustomMiddleware,
            CdnSwitch,
            FlowSwitcherMiddleware,
            RedirectSwitch,
        )
        frontappSwitch = CdnSwitch(
            packageName="@youwol/foo-app",
            port=4001
        )
        backendSwitch = RedirectSwitch(
            origin="/api/foo-backend",
            destination=f"http://localhost:4002"
        )


        Configuration(
            customization=Customization(
                middlewares=[
                    FlowSwitcherMiddleware(
                        name="Frontend servers",
                        oneOf=[frontappSwitch],
                    ),
                    FlowSwitcherMiddleware(
                        name="Backend servers",
                        oneOf=[backendSwitch],
                    ),
                ],
            )
        )
        ```
        In the above snippet to FlowSwitcherMiddleware middleware are added:

        *  the first one ([CdnSwitch](@yw-nav-class:youwol.app.environment.models.models_config.CdnSwitch))
        redirect any request to the frontend application `@youwol/foo-app` (normally served from the CDN database)
         to a local dev-server serving on port `4001`.
        *  the second one ([RedirectSwitch](@yw-nav-class:youwol.app.environment.models.models_config.RedirectSwitch))
         redirect any request to `/api/foo-backend/**` to the destination `http://localhost:4002`.

    """

    name: str
    """
    Name of the middleware
    """

    oneOf: list[FlowSwitch]
    """
    The list of available 'switch'.
    """

    async def dispatch(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Optional[Response]:
        async with context.start(
            action=f"FlowSwitcher: {self.name}", with_labels=[Label.MIDDLEWARE]
        ) as ctx:
            async with ctx.start(
                action=f"Get status of {len(self.oneOf)} switches"
            ) as ctx_status:
                matches = [
                    d
                    for d in self.oneOf
                    if await d.is_matching(
                        incoming_request=incoming_request, context=ctx_status
                    )
                ]
            if len(matches) > 1:
                raise RuntimeError("Multiple flow-switches match the incoming request")

            if not matches:
                await ctx.info("No match from the flow-switcher")
                return await call_next(incoming_request)

            try:
                response = await matches[0].switch(
                    incoming_request=incoming_request, context=ctx
                )
            except YouWolException as e:
                return await youwol_exception_handler(incoming_request, e)

            await ctx.info("Got response from a flow-switcher")
            return response


class CdnSwitch(FlowSwitch):
    """
    This [FlowSwitch]((@yw-nav-class:youwol.app.environment.models.models_config.FlowSwitch) target request to elements
     in the  CDN database (frontend applications usually) and redirect it to particular port from `localhost`
     (usually on which a dev. server of the application is running).

    Each time a related resource from the targeted element is queried, it is actually retrieved from dev. server
    (and not from the CDN database).

    Example:
        Below is a typical example of usage of CdnSwitch within a
        [FlowSwitcherMiddleware](@yw-nav-class:youwol.app.environment.models.models_config.FlowSwitcherMiddleware):

        ```python hl_lines="5 14"
        from youwol.app.environment import (
            Configuration,
            Customization,
            CustomMiddleware,
            CdnSwitch,
            FlowSwitcherMiddleware
        )

        Configuration(
            customization=Customization(
                middlewares=[
                    FlowSwitcherMiddleware(
                        name="Frontend servers",
                        oneOf=[CdnSwitch(packageName="@youwol/foo-app", port=4001)],
                    )
                ],
            )
        )
        ```
        Each time a resource from `@youwol/foo-app` is queried, it will be redirected to `localhost:4001`.
    """

    packageName: str
    """
    The name of the targeted package.
    """

    port: int
    """
    Listening port of the dev-server.
    """

    async def info(self):
        return DispatchInfo(
            name=self.packageName,
            activated=is_server_http_alive(f"http://localhost:{self.port}"),
            parameters={
                "package": self.packageName,
                "redirected to": f"localhost:{self.port}",
            },
        )

    async def is_matching(self, incoming_request: Request, context: Context):
        if incoming_request.method != "GET":
            return False

        encoded_id = encode_id(self.packageName)

        if not (
            incoming_request.url.path.startswith(
                f"/api/assets-gateway/raw/package/{encoded_id}"
            )
            or incoming_request.url.path.startswith(
                f"/api/cdn-backend/resources/{encoded_id}"
            )
        ):
            await context.info(
                text=f"CdnSwitch[{self}]: URL not matching",
                data={"url": incoming_request.url.path, "encoded_id": encoded_id},
            )
            return False

        if not is_server_http_alive(f"http://localhost:{self.port}"):
            await context.info(text=f"CdnSwitch[{self}]: ws not listening")
            return False

        await context.info(text=f"CdnSwitch[{self}]: MATCHING")
        return True

    async def switch(
        self, incoming_request: Request, context: Context
    ) -> Optional[Response]:
        headers = context.headers(from_req_fwd=lambda header_keys: header_keys)

        asset_id = f"/{encode_id(self.packageName)}/"
        trailing_path = incoming_request.url.path.split(asset_id)[1]
        # the next '[1:]' skip the version of the package
        rest_of_path = "/".join(trailing_path.split("/")[1:])

        resp = await self._forward_request(rest_of_path=rest_of_path, headers=headers)

        if resp:
            return resp

        await context.error(
            text=f"CdnSwitch[{self}]: Error status while dispatching",
            data={"origin": incoming_request.url.path, "path": rest_of_path},
        )
        raise ResourcesNotFoundException(path=rest_of_path, detail="No resource found")

    async def _forward_request(
        self, rest_of_path: str, headers: dict[str, str]
    ) -> Optional[Response]:
        dest_url = f"http://localhost:{self.port}/{rest_of_path}"

        async with ClientSession(auto_decompress=False) as session:
            async with await session.get(url=dest_url, headers=headers) as resp:
                if resp.status < 400:
                    content = await resp.read()
                    return Response(
                        status_code=resp.status,
                        content=content,
                        headers=dict(resp.headers.items()),
                    )

    def __str__(self):
        return f"serving cdn package '{self.packageName}' from local port '{self.port}'"


class RedirectSwitch(FlowSwitch):
    """
    This [FlowSwitch](@yw-nav-class:youwol.app.environment.models.models_config.FlowSwitch) target requests with url
    that starts with a predefined 'origin' to a corresponding 'destination' (the rest of the path appended to it).

    Example:
        Below is a typical example of usage of RedirectSwitch within a
        [FlowSwitcherMiddleware](@yw-nav-class:youwol.app.environment.models.models_config.FlowSwitcherMiddleware):

        ```python hl_lines="5 8-11 18"
        from youwol.app.environment import (
            Configuration,
            Customization,
            CustomMiddleware,
            RedirectSwitch,
            FlowSwitcherMiddleware
        )
        redirect_switch = RedirectSwitch(
            origin="/api/foo-backend",
            destination=f"http://localhost:4002"
        )

        Configuration(
            customization=Customization(
                middlewares=[
                    FlowSwitcherMiddleware(
                        name="Frontend servers",
                        oneOf=[redirect_switch],
                    )
                ],
            )
        )
        ```
        Each time a request to `/api/foo-backend/**` is intercepted, it will be redirected to `localhost:4002`.
    """

    origin: str
    """
    Origin base path targeted.
    """

    destination: str
    """
    Corresponding destination, e.g. 'http://localhost:2001'
    """

    def is_listening(self):
        return is_server_http_alive(url=self.destination)

    async def info(self) -> DispatchInfo:
        return DispatchInfo(
            name=self.origin,
            activated=self.is_listening(),
            parameters={"from url": self.origin, "redirected to": self.destination},
        )

    async def is_matching(self, incoming_request: Request, context: Context):
        if not incoming_request.url.path.startswith(self.origin):
            await context.info(
                text=f"RedirectSwitch[{self}]: URL not matching",
                data={"url": incoming_request.url.path},
            )
            return False

        if not self.is_listening():
            await context.info(
                f"RedirectSwitch[{self}]: destination not listening -> proceed with no dispatch"
            )
            return False

        return True

    async def switch(
        self, incoming_request: Request, context: Context
    ) -> Optional[Response]:
        env = await context.get("env", YouwolEnvironment)
        headers = {
            **dict(incoming_request.headers.items()),
            **context.headers(),
            YouwolHeaders.py_youwol_port: str(env.httpPort),
        }

        await context.info(
            text=f"RedirectSwitch[{self}] execution",
            data={"origin": incoming_request.url.path, "destination": self.destination},
        )

        resp = await redirect_request(
            incoming_request=incoming_request,
            origin_base_path=self.origin,
            destination_base_path=self.destination,
            headers=headers,
        )
        await context.info(
            "Got response from dispatch",
            data={
                "headers": dict(resp.headers.items()),
                "status": resp.status_code,
            },
        )
        return resp

    def __str__(self):
        return f"redirecting '{self.origin}' to '{self.destination}'"
