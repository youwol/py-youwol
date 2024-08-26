# typing

# third parties
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import CdnSwitch, YouwolEnvironment

# Youwol backends
import youwol.backends.cdn as cdn_backend

# Youwol utilities
from youwol.utils import Context, ResourcesNotFoundException, encode_id


class WebpackDevServerSwitch(CdnSwitch):
    """
    CDN resource are stored in the CDN database: each time a related resource is queried, it is retrieved from here.
    The class WebpackDevServerSwitch can alter this behavior for a particular package,
     and serve the resources using a running webpack's dev-server.

    **Attributes**:

    - **packageName** :class:`str`
    Name of the targeted package.

    - **port** :class:`int`
    Listening port of the dev-server.

    - **notServedResources** :class: `List[str]`
    Paths of resources (or folder of resources) that exists in the CDN database but are not part of
    the webpack dev-server scope. This is typically artifacts included  into the CDN database during the publication
    step (which may not exist in the project's working directory).

    Default to `[".yw_metadata.json", "dist/docs", "coverage"]`."""

    packageName: str
    port: int
    notServedResources: list[str] = [
        ".yw_metadata.json",
        "dist/docs",
        "coverage",
        "dist/bundle-analysis.html",
    ]

    async def switch(
        self, incoming_request: Request, context: Context
    ) -> Response | None:
        headers = context.headers(from_req_fwd=lambda header_keys: header_keys)
        asset_id = f"/{encode_id(self.packageName)}/"
        trailing_path = incoming_request.url.path.split(asset_id)[1]
        return await dispatch_dev_server(
            package=self.packageName,
            version=trailing_path.split("/")[0],
            request=incoming_request,
            # the next '[1:]' skip the version of the package
            target=trailing_path.split("/")[1:],
            fwd_request=lambda rest_of_path: self._forward_request(
                rest_of_path, headers
            ),
            context=context,
        )


async def dispatch_dev_server(
    package: str,
    version: str,
    request: Request,
    target: list[str],
    fwd_request,
    context: Context,
) -> Response:

    # for webpack dev server, there are three kinds of resources:
    #   - the one built by webpack (dynamic): they are served from the 'root'
    #     For instance: '/dist/bundles.js will be served at localhost:xxxx/bundle.js
    #     In this case we only care about the last part of the url
    #   - the static assets, they are served 'normally'
    #     For instance: '/dist/assets/foo.png' will be served at localhost:xxxx/dist/assets/foo.png
    #     In this case we care about last part of the url after the asset_id
    #     The static case is tested before the dynamic one as usually there are a limited set of dynamic resources
    #   - the resources that are not part of the project's working folder but explicitly listed in
    #   'notServedResources': they are directly fetched from the CDN database.
    #   Maybe extends 'notServedResources' to include patterns like '/dist/docs/**'

    not_server_resources: list[str] = [
        ".yw_metadata.json",
        "dist/docs",
        "coverage",
        "dist/bundle-analysis.html",
    ]

    env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
    rest_of_path_static = "/".join(target) if target else ""
    rest_of_path_dynamic = target[-1] if target else ""
    not_served_match = next(
        (p for p in not_server_resources if rest_of_path_static.startswith(p)),
        None,
    )
    if not_served_match:
        await context.info(
            text="Match to fetch from CDN DB ",
            data={"trailing_path": rest_of_path_static},
        )

        return await cdn_backend.get_resource(
            request=request,
            library_id=encode_id(package),
            version=version,
            rest_of_path=rest_of_path_static,
            configuration=env.backends_configuration.cdn_backend,
        )
    resp = await fwd_request(rest_of_path=rest_of_path_static)
    if resp:
        await context.info(
            text="Got response for static asset",
            data={"trailing_path": rest_of_path_static},
        )
        return resp

    resp = await fwd_request(rest_of_path=rest_of_path_dynamic)
    if resp:
        await context.info(
            text="Got response for dynamic asset",
            data={"trailing_path": rest_of_path_static},
        )
        return resp

    await context.error(
        text="Error status while dispatching",
        data={
            "origin": request.url.path,
            "paths tested": [rest_of_path_static, rest_of_path_dynamic],
        },
    )
    raise ResourcesNotFoundException(
        path=f"{rest_of_path_dynamic} or ${rest_of_path_dynamic}",
        detail="No resource found",
    )
