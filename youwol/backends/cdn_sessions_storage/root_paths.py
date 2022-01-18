from starlette.requests import Request
from fastapi import APIRouter, Depends, HTTPException

from .configurations import Configuration, get_configuration
from .utils import get_path
from youwol_utils import generate_headers_downstream, JSON

router = APIRouter()


@router.get("/healthz")
async def healthz():
    return {"status": "cdn-sessions-storage ok"}


async def post_data_generic(
        request: Request,
        package: str,
        name: str,
        body: JSON,
        namespace: str = None,
        configuration: Configuration = Depends(get_configuration)
):
    """

    Args:
        request: incoming request
        package: name of the package (without include namespace)
        name: name of the data
        body: json data
        namespace: optional namespace of the package
        configuration: service's configuration

    Returns:
        empty response '{}'
    """
    headers = generate_headers_downstream(request.headers)
    await configuration.storage.post_json(
        path=get_path(request=request, package=package, name=name, namespace=namespace),
        json=body,
        owner=configuration.default_owner,
        headers=headers
    )
    return {}


@router.post("/applications/{package}/{name}")
async def post_data_no_namespace(
        request: Request,
        package: str,
        name: str,
        body: JSON,
        configuration: Configuration = Depends(get_configuration)
):
    return await post_data_generic(request=request, package=package, name=name, body=body,
                                   configuration=configuration)


@router.post("/applications/{namespace}/{package}/{name}")
async def post_data_with_namespace(
        request: Request,
        namespace: str,
        package: str,
        name: str,
        body: JSON,
        configuration: Configuration = Depends(get_configuration)
):
    return await post_data_generic(request=request, namespace=namespace, package=package, name=name, body=body,
                                   configuration=configuration)


async def get_data_generic(
        request: Request,
        package: str,
        name: str,
        namespace: str = None,
        configuration: Configuration = Depends(get_configuration)
):
    headers = generate_headers_downstream(request.headers)
    try:
        return await configuration.storage.get_json(
            path=get_path(request=request, package=package, name=name, namespace=namespace),
            owner=configuration.default_owner,
            headers=headers
        )
    except HTTPException as e:
        if e.status_code == 404:
            return {}


@router.get("/applications/{package}/{name}")
async def get_data_no_namespace(
        request: Request,
        package: str,
        name: str,
        configuration: Configuration = Depends(get_configuration)
):
    return await get_data_generic(request=request, package=package, name=name, configuration=configuration)


@router.get("/applications/{namespace}/{package}/{name}")
async def get_data_with_namespace(
        request: Request,
        namespace: str,
        package: str,
        name: str,
        configuration: Configuration = Depends(get_configuration)
):
    return await get_data_generic(request=request, namespace=namespace, package=package, name=name,
                                  configuration=configuration)
