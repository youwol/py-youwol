# typing
from typing import Optional

# third parties
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request

# Youwol backends
from youwol.backends.cdn_sessions_storage.configurations import (
    Configuration,
    Constants,
    get_configuration,
)
from youwol.backends.cdn_sessions_storage.utils import get_path

# Youwol utilities
from youwol.utils import JSON, AnyDict
from youwol.utils.context import Context

router = APIRouter(tags=["cdn-sessions-storage"])


@router.get("/healthz")
async def healthz():
    return {"status": "cdn-sessions-storage ok"}


async def post_data_generic(
    request: Request,
    package: str,
    name: str,
    body: JSON,
    namespace: Optional[str] = None,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"name": name, "package": package}
    ) as ctx:
        await configuration.storage.post_json(
            path=get_path(
                request=request, package=package, name=name, namespace=namespace
            ),
            json=body,
            owner=Constants.default_owner,
            headers=ctx.headers(),
        )
        return {}


@router.post("/applications/{package}/{name}")
async def post_data_no_namespace(
    request: Request,
    package: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Create a new entry for the current user from a particular application or library.

    Parameters:
        request: Incoming request.
        package: Name of the package that post the data (the owner, without namespace).
        name: Name of the data.
        body: JSON data.
        configuration: Injected
            [Configuration](@yw-nav-class:youwol.backends.cdn_sessions_storage.configurations.Configuration).

    Returns:
        Empty JSON.
    """
    body = await request.json()
    return await post_data_generic(
        request=request,
        package=package,
        name=name,
        body=body,
        configuration=configuration,
    )


@router.post("/applications/{namespace}/{package}/{name}")
async def post_data_with_namespace(
    request: Request,
    namespace: str,
    package: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Create a new entry for the current user from a particular application or library.

    Parameters:
        request: Incoming request.
        namespace: Namespace of the package.
        package: Name of the package that post the data (the owner, without namespace).
        name: Name of the data.
        body: JSON data.
        configuration: Injected
            [Configuration](@yw-nav-class:youwol.backends.cdn_sessions_storage.configurations.Configuration).

    Returns:
        Empty JSON.
    """
    body = await request.json()
    return await post_data_generic(
        request=request,
        namespace=namespace,
        package=package,
        name=name,
        body=body,
        configuration=configuration,
    )


async def delete_data_generic(
    request: Request,
    package: str,
    name: str,
    namespace: Optional[str] = None,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"name": name, "package": package}
    ) as ctx:
        await configuration.storage.delete(
            path=get_path(
                request=request, package=package, name=name, namespace=namespace
            ),
            owner=Constants.default_owner,
            headers=ctx.headers(),
        )
        return {}


@router.delete("/applications/{package}/{name}")
async def delete_data_no_namespace(
    request: Request,
    package: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Delete an entry.

    Parameters:
        request: Incoming request.
        package: Name of the package that post the data (the owner, without namespace).
        name: Name of the data.
        configuration: Injected
            [Configuration](@yw-nav-class:youwol.backends.cdn_sessions_storage.configurations.Configuration).

    Returns:
        Empty JSON.
    """
    return await delete_data_generic(
        request=request, package=package, name=name, configuration=configuration
    )


@router.delete("/applications/{namespace}/{package}/{name}")
async def delete_data_with_namespace(
    request: Request,
    namespace: str,
    package: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict:
    """
    Delete an entry.

    Parameters:
        request: Incoming request.
        namespace: Namespace of the package.
        package: Name of the package that post the data (the owner, without namespace).
        name: Name of the data.
        configuration: Injected
            [Configuration](@yw-nav-class:youwol.backends.cdn_sessions_storage.configurations.Configuration).

    Returns:
        Empty JSON.
    """
    return await delete_data_generic(
        request=request,
        namespace=namespace,
        package=package,
        name=name,
        configuration=configuration,
    )


async def get_data_generic(
    request: Request,
    package: str,
    name: str,
    namespace: Optional[str] = None,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_attributes={"name": name, "package": package}
    ) as ctx:
        try:
            return await configuration.storage.get_json(
                path=get_path(
                    request=request, package=package, name=name, namespace=namespace
                ),
                owner=Constants.default_owner,
                headers=ctx.headers(),
            )
        except HTTPException as e:
            if e.status_code == 404:
                return {}


@router.get("/applications/{package}/{name}")
async def get_data_no_namespace(
    request: Request,
    package: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict | None:
    """
    Get an entry.

    Parameters:
        request: Incoming request.
        package: Name of the package that post the data (the owner, without namespace).
        name: Name of the data.
        configuration: Injected
            [Configuration](@yw-nav-class:youwol.backends.cdn_sessions_storage.configurations.Configuration).

    Returns:
        Empty JSON.
    """
    return await get_data_generic(
        request=request, package=package, name=name, configuration=configuration
    )


@router.get("/applications/{namespace}/{package}/{name}")
async def get_data_with_namespace(
    request: Request,
    namespace: str,
    package: str,
    name: str,
    configuration: Configuration = Depends(get_configuration),
) -> AnyDict | None:
    """
    Get an entry.

    Parameters:
        request: Incoming request.
        namespace: Namespace of the package.
        package: Name of the package that post the data (the owner, without namespace).
        name: Name of the data.
        configuration: Injected
            [Configuration](@yw-nav-class:youwol.backends.cdn_sessions_storage.configurations.Configuration).

    Returns:
        Empty JSON.
    """
    return await get_data_generic(
        request=request,
        namespace=namespace,
        package=package,
        name=name,
        configuration=configuration,
    )
