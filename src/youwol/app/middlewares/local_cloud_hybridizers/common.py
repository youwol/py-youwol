# standard library
import asyncio
import base64

# typing
from typing import NamedTuple

# Youwol application
from youwol.app.environment import LocalClients, RemoteClients
from youwol.app.environment.models import YouwolEnvironment

# Youwol backends
from youwol.backends.cdn.utils_indexing import get_version_number

# Youwol utilities
from youwol.utils import JSON, Context


class PackageLatestVersionInfo(NamedTuple):
    """
    Object containing information about latest version of a package.
    """

    package_name: str
    """
    Package's name.
    """
    asset_id: str
    """
    Asset's ID
    """
    download_needed: bool
    """
    Whether it should be downloaded (*i.e.* the latest version in remote is not available in local).
    """
    latest_local: str
    """
    Latest local version.
    """
    latest_remote: str
    """
    Latest remote version.
    """


async def package_latest_info(
    package_name: str, semver: str, context: Context
) -> PackageLatestVersionInfo:
    """
    Evaluates whether a newer version of a specified package is available for download,
    by comparing the latest versions available in both local and remote environments against a given semantic version.

    This function fetches the latest version information for a specified package from both local and remote sources,
    compares these versions, and determines if downloading the newer version is necessary. It utilizes an execution
    context for logging and state management throughout the process.

    Parameters:
        package_name: The name of the package for which to check available versions.
        semver: The semantic versioning filter to apply when searching for the package versions.
        context: The execution context object.

    Return:
        An object containing information about the package request

    Raises: This function handles exceptions internally and logs warnings through the provided context object.
        It is designed to proceed with execution unless critical errors occur, in which case it may raise
        environment-specific or network-related exceptions not explicitly caught within the function.

    Example:
    <code-snippet language="python">
    context = Context()
    package_info = await package_request_info("my-package", "^1.0.0", context)
    if package_info.download_needed:
       print(f"Newer version available: {package_info.latest_remote}")
    else:
       print("Package is up-to-date.")
    </code-snippet>

    """

    async def compare_latest_versions(
        latest_local: str | None,
        latest_remote: str | None,
        ctx_inner: Context,
    ):
        if not latest_remote and not latest_local:
            # not necessarily an error, e.g. maybe a latter middleware will handle this case
            await ctx_inner.warning(
                f"Application '{package_name}#{semver}' not found in remote or local environments, proceed normally."
            )
            return False

        if latest_local and not latest_remote:
            await ctx_inner.info(
                f"{package_name} not available in remote environment, proceed normally."
            )
            return False

        if latest_local and get_version_number(latest_local) >= get_version_number(
            latest_remote
        ):
            await ctx_inner.info(
                f"Local version {latest_local} of {package_name} up-to-date or above w/ remote, proceed normally."
            )
            return False

        return True

    def retrieve_latest_version(resp: JSON | BaseException):
        return (
            resp["versions"][0]
            if not isinstance(resp, BaseException) and len(resp["versions"]) > 0
            else None
        )

    async with context.start(action="download_package_needed") as ctx:

        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)

        asset_id = base64.urlsafe_b64encode(str.encode(package_name)).decode()

        remote_assets_gtw = await RemoteClients.get_twin_assets_gateway_client(env=env)
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
        local_latest = retrieve_latest_version(version_info_local)
        remote_latest = retrieve_latest_version(version_info_remote)
        needed = await compare_latest_versions(
            latest_local=retrieve_latest_version(version_info_local),
            latest_remote=retrieve_latest_version(version_info_remote),
            ctx_inner=ctx,
        )
        if needed:
            await ctx.info(
                f"A newer version of '{package_name}#{semver}' is available to download",
                data={
                    "latest_remote": remote_latest,
                    "latest_local": local_latest or "No matching local version",
                },
            )
        return PackageLatestVersionInfo(
            package_name=package_name,
            asset_id=asset_id,
            download_needed=needed,
            latest_local=local_latest,
            latest_remote=remote_latest,
        )
