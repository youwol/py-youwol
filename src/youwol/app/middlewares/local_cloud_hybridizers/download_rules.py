# standard library
import asyncio
import base64

# typing
from typing import List, Optional

# third parties
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import LocalClients, RemoteClients, YouwolEnvironment
from youwol.app.routers.environment.download_assets.auto_download_thread import (
    AssetDownloadThread,
    get_assets_downloader,
)
from youwol.app.routers.router_remote import redirect_api_remote

# Youwol backends
from youwol.backends.cdn.utils_indexing import get_version_number

# Youwol utilities
from youwol.utils import YouwolHeaders, decode_id
from youwol.utils.context import Context
from youwol.utils.request_info_factory import url_match

# relative
from .abstract_local_cloud_dispatch import AbstractLocalCloudDispatch


class Download(AbstractLocalCloudDispatch):
    async def apply(
        self,
        incoming_request: Request,
        call_next: RequestResponseEndpoint,
        context: Context,
    ) -> Optional[Response]:
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
        async with context.start(
            action="Download.apply", muted_http_errors={404}
        ) as ctx:
            download_thread = await ctx.get("download_thread", AssetDownloadThread)
            is_downloading = download_thread.is_downloading(
                url=incoming_request.url.path, kind=kind, raw_id=raw_id, env=env
            )
            # if downloading => do not try fetching the asset from local-db (the asset can be in invalid state).
            if is_downloading:
                resp = await redirect_api_remote(incoming_request, ctx)
                resp.headers[YouwolHeaders.youwol_origin] = env.get_remote_info().host
                return resp

            resp = await call_next(incoming_request)
            if resp.status_code == 404:
                await ctx.info(
                    "Raw data can not be locally retrieved, proceed to remote platform"
                )
                headers = {
                    "Authorization": incoming_request.headers.get("authorization")
                }
                resp = await redirect_api_remote(incoming_request, ctx)
                resp.headers[YouwolHeaders.youwol_origin] = env.get_remote_info().host
                is_downloading = download_thread.is_downloading(
                    url=incoming_request.url.path, kind=kind, raw_id=raw_id, env=env
                )
                # if by the time the remote api call responded the asset is already downloading
                # => do not enqueue download
                if is_downloading:
                    return resp
                await ctx.info("~> schedule asset download")
                download_thread.enqueue_asset(
                    url=incoming_request.url.path,
                    kind=kind,
                    raw_id=raw_id,
                    context=ctx,
                    headers=headers,
                )
                return resp
            resp.headers[YouwolHeaders.youwol_origin] = incoming_request.url.hostname
            return resp


class UpdateApplication(AbstractLocalCloudDispatch):
    @staticmethod
    def retrieve_package_version_path(params: List[str]):
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
    ) -> Optional[Response]:
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

        async with context.start(
            action="UpdateApplication.apply", muted_http_errors={404}
        ) as ctx:  # type: Context
            if all([elem not in semver for elem in ["*", "^", "x", "latest"]]):
                await context.info(
                    "App with explicit version required -> proceed normally"
                )
                return await call_next(incoming_request)

            asset_id = base64.urlsafe_b64encode(str.encode(package_name)).decode()

            env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
            remote_assets_gtw = await RemoteClients.get_assets_gateway_client(
                env.get_remote_info().host
            )
            remote_cdn = remote_assets_gtw.get_cdn_backend_router()
            local_cdn = LocalClients.get_cdn_client(env=env)

            async with ctx.start(
                action=f"Recover local & remote latest version matching semver '{semver}'"
            ):
                version_info_local, version_info_remote = await asyncio.gather(
                    local_cdn.get_library_info(
                        library_id=asset_id,
                        semver=semver,
                        max_count=1,
                        headers=ctx.headers(),
                    ),
                    remote_cdn.get_library_info(
                        library_id=asset_id,
                        semver=semver,
                        max_count=1,
                        headers=ctx.headers(),
                    ),
                    return_exceptions=True,
                )

            if isinstance(version_info_local, BaseException) or isinstance(
                version_info_remote, BaseException
            ):
                await ctx.error(
                    f"Both local and remote versions request failed for {package_name}#{semver} "
                    f"... not good"
                )
                return await call_next(incoming_request)

            latest_local = version_info_local["versions"][0]
            latest_remote = version_info_remote["versions"][0]
            if get_version_number(latest_local) >= get_version_number(latest_remote):
                await ctx.info(
                    f"Local version {latest_local} of application up-to-date with remote"
                )
                return await call_next(incoming_request)

            await ctx.info(
                f"A newer version matching semver '{semver}' is available to download",
                data={"latest_remote": latest_remote, "latest_local": latest_local},
            )

            downloader = get_assets_downloader()

            if not downloader:
                # the downloader is initialized at start => there is no reason to pass by this branch
                await ctx.warning(
                    f"Assets downloader not available, proceed with no download by fetching "
                    f"{latest_local}"
                )
                return await call_next(incoming_request)

            await downloader.download_asset(
                url=f"/api/assets-gateway/cdn-backend/resources/{asset_id}/{latest_remote}",
                kind="package",
                raw_id=asset_id,
                context=ctx,
            )
            return await call_next(incoming_request)
