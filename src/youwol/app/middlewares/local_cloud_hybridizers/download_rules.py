# third parties
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment
from youwol.app.routers.environment.download_assets.auto_download_thread import (
    AssetsDownloader,
)
from youwol.app.routers.router_remote import redirect_api_remote

# Youwol utilities
from youwol.utils import YouwolHeaders, aiohttp_to_starlette_response, decode_id
from youwol.utils.context import Context
from youwol.utils.request_info_factory import url_match

# relative
from .abstract_local_cloud_dispatch import AbstractLocalCloudDispatch
from .common import package_latest_info


class Download(AbstractLocalCloudDispatch):
    """
    Dispatch handling automatic download in the local drive for resources that are not found locally.
    If the resource is found locally, it returns the response.
    If the resource is not found locally:
    *  it redirects the request to the remote environment
    *  if the previous step succeeded, it adds in the download queue a task to download the corresponding asset.

    """

    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Response | None:
        """
        This dispatch match the endpoints:
         *  `GET:/api/assets-gateway/assets-backend/assets/*/files/**`
         *  `GET:/api/assets-gateway/stories-backend/stories/**`
         *  `GET:/api/assets-gateway/flux-backend/projects/**`
         *  `GET:/api/assets-gateway/files-backend/files/**`
         *  `GET:/api/assets-gateway/cdn-backend/resources/**`
         *  `GET:/api/assets-gateway/raw/package/**`
         *  `GET:/api/assets-gateway/raw/flux-project/**`

        It returns `None` otherwise.

        Parameters:
            incoming_request: The incoming request.
            call_next: The next endpoint in the chain.
            context: The current context.

        Return:
            The local or remote response. Side effects: the target asset eventually queued for download (in dedicated
            thread).
        """
        # Caution: download should be triggered only when fetching raw data of the asset
        # not metadata (e.g. do not catch /assets-backend/assets/**).
        patterns = [
            (
                "custom-asset",
                "GET:/api/assets-gateway/assets-backend/assets/*/files/**",
            ),
            ("story", "GET:/api/assets-gateway/stories-backend/stories/*/**"),
            ("flux-project", "GET:/api/assets-gateway/flux-backend/projects/*/**"),
            ("data", "GET:/api/assets-gateway/files-backend/files/*/**"),
            ("package", "GET:/api/assets-gateway/cdn-backend/resources/*/**"),
            # This is a deprecated end points
            ("package", "GET:/api/assets-gateway/raw/package/*/**"),
            ("flux-project", "GET:/api/assets-gateway/raw/flux-project/*/**"),
        ]
        matches = [
            (kind, url_match(incoming_request, pattern)) for kind, pattern in patterns
        ]
        match = next(((kind, match[1]) for kind, match in matches if match[0]), None)
        if not match:
            return None
        kind, params = match
        raw_id = params[0][0] if len(params[0]) == 2 else params[0]
        if kind == "custom-asset":
            # In case of 'assets-gateway/assets-backend/assets/*/**', first param is actually the asset_id
            asset_id = raw_id
            raw_id = decode_id(asset_id)
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)

        def apply_from_remote_headers(response: Response):
            response.headers[YouwolHeaders.youwol_origin] = env.get_remote_info().host
            if match[0] == "package":
                response.headers.update({"cache-control": "no-cache, no-store"})

        async with context.start(action="Download.apply") as ctx:
            assets_downloader = await ctx.get("assets_downloader", AssetsDownloader)
            is_downloading = assets_downloader.is_downloading(
                url=incoming_request.url.path, kind=kind, raw_id=raw_id, env=env
            )
            # if downloading => do not try fetching the asset from local-db (the asset can be in invalid state).
            if is_downloading:
                await ctx.info("~> Resource is already downloading")
                resp = await redirect_api_remote(incoming_request, ctx)
                apply_from_remote_headers(resp)
                return resp

            resp = await call_next(incoming_request)
            if resp.status_code == 404:
                await ctx.info(
                    "Raw data can not be locally retrieved, proceed to remote platform"
                )
                resp = await redirect_api_remote(incoming_request, ctx)
                apply_from_remote_headers(resp)
                is_downloading = assets_downloader.is_downloading(
                    url=incoming_request.url.path, kind=kind, raw_id=raw_id, env=env
                )
                # if by the time the remote api call responded the asset is already downloading
                # => do not enqueue download
                if is_downloading:
                    await ctx.info("~> Resource is already downloading")
                    return resp
                await ctx.info("~> schedule asset download")
                await assets_downloader.enqueue_asset(
                    url=incoming_request.url.path, kind=kind, raw_id=raw_id, context=ctx
                )
                return resp
            resp.headers[YouwolHeaders.youwol_origin] = incoming_request.url.hostname
            return resp


class UpdateApplication(AbstractLocalCloudDispatch):
    """
    Dispatch handling automatic upgrade of application if a newer version w/ target semantic versioning is available
     in remote environment w/ local one.
    """

    @staticmethod
    def retrieve_package_version_path(params: list[str]):
        if params[0].startswith("@"):
            # e.g. @bar/foo/latest/dist/bundle.js
            package_name = f"{params[0]}/{params[1]}"
            version = params[2]
            rest_of_path = params[3:]
        else:
            # e.g. /foo/latest/dist/bundle.js
            package_name = params[0]
            version = params[1]
            rest_of_path = params[2:]
        version = version if version != "latest" else "*"
        return package_name, version, rest_of_path

    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Response | None:
        """
        This dispatch match the endpoint `GET:/applications/**`, it returns `None` otherwise.

        Parameters:
            incoming_request: The incoming request.
            call_next: The next endpoint in the chain.
            context: The current context.

        Return:
            The latest version available in remote or local environments for the application that match
            the semver query. If returned from the remote environment, the dispatch
            [Download](@yw-nav-class:youwol.app.middlewares.local_cloud_hybridizers.download_rules.Download)
             will later trigger local download of the corresponding asset.
        """

        match, params = url_match(incoming_request, "GET:/applications/**")
        if not match:
            return None
        package_name, semver, rest_of_path = self.retrieve_package_version_path(
            params[0]
        )

        if len(rest_of_path) > 0:
            # The application download is triggered only on the initial GET, e.g. 'applications/foo/latest'
            # and not e.g. 'applications/foo/latest/dist/bundle.js'
            return None

        async with context.start(action="UpdateApplication.apply") as ctx:
            if all(elem not in semver for elem in ["*", "^", "x", "~"]):
                await context.info(
                    "App with explicit version required -> proceed normally"
                )
                return await call_next(incoming_request)
            env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
            download_info = await package_latest_info(
                package_name=package_name, semver=semver, context=ctx
            )

            if not download_info.download_needed:
                return await call_next(incoming_request)

            # Forward the same request except for the version that is now fixed to the resolved one.
            # It will then be intercepted by the 'Download' AbstractLocalCloudDispatch to fetch the entry point &
            # proceed with the package download.
            resp = (
                await LocalClients.get_assets_gateway_client(env)
                .get_cdn_backend_router()
                .get_resource(
                    library_id=download_info.asset_id,
                    version=download_info.latest_remote,
                    rest_of_path="",
                    headers=ctx.headers(),
                    custom_reader=aiohttp_to_starlette_response,
                )
            )
            return resp
