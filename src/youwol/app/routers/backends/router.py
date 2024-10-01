# third parties
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response

# Youwol application
from youwol.app.environment import YouwolEnvironment
from youwol.app.environment.proxied_backends import DEFAULT_PARTITION_ID
from youwol.app.routers.backends.implementation import ensure_running

# Youwol utilities
from youwol.utils import Context, YouwolHeaders, redirect_request

router = APIRouter()


class BackendResponse(BaseModel):
    name: str
    version: str
    url: str
    method: str
    statusCode: int


async def dispatch_impl(
    request: Request,
    backend_name: str,
    version_query: str,
    context: Context,
):
    """
    Implementation for dispatch on `/backends/{NAME}/{SEMVER}/rest/of/path`, whatever the request's method.

    Main steps:
    *  retrieves an eventual `partition_id`
        from :meth:`headers <youwol.utils.utils.YouwolHeaders.get_backends_partition>`.
    *  ensure the target backend is running, see :func:`youwol.app.routers.backends.implementation.ensure_running`.
    Retrieves the proxied backend :class:`information <youwol.app.environment.proxied_backends.ProxiedBackend>`.
    *  redirect the request.

    Parameters:
        request: Incoming request.
        backend_name: Target backend's name.
        version_query: Semantic versioning query.
        context: Current execution context.

    Returns:
        The response.
    """
    env = await context.get("env", YouwolEnvironment)
    partition_id = YouwolHeaders.get_backends_partition(request, DEFAULT_PARTITION_ID)
    backend = await ensure_running(
        request=request,
        partition_id=partition_id,
        backend_name=backend_name,
        version_query=version_query,
        # If the service is not already started (no explicit webpm-client install already executed),
        # the default configuration will be used.
        config=None,
        # Timeout for the server to respond (in second).
        # E.g., on macOS python backends take time to listen on the first run.
        timeout=20,
        context=context,
    )
    if not backend:
        return HTTPException(
            status_code=404,
            detail=f"No proxied backends match the query '{backend_name}#{version_query}@{partition_id}",
        )

    backend.endpoint_ctx_id.append(context.parent_uid)

    headers = {
        **dict(request.headers.items()),
        **context.headers(),
        YouwolHeaders.py_youwol_port: str(env.httpPort),
    }
    destination = f"http://localhost:{backend.port}"
    await context.info(
        text=f"Redirecting to {destination}",
        data={
            "origin": request.url.path,
            "destination": destination,
            "py_youwol_port": env.httpPort,
        },
    )
    origin_base_path = f"/backends/{backend_name}/{version_query}"
    resp = await redirect_request(
        incoming_request=request,
        origin_base_path=f"/backends/{backend_name}/{version_query}",
        destination_base_path=destination,
        headers=headers,
    )
    await context.send(
        BackendResponse(
            name=backend.name,
            version=backend.version,
            statusCode=resp.status_code,
            url=request.url.path.replace(origin_base_path, f"localhost:{backend.port}"),
            method=request.method,
        )
    )

    return resp


@router.get(
    "/{backend_name}/{version_query}/{rest_of_path:path}", summary="Dispatch GET."
)
async def dispatch_get(
    request: Request, backend_name: str, version_query: str
) -> Response:
    """
    Dispatch `GET` requests.

    Parameters:
        request: Incoming request.
        backend_name: Target backend's name.
        version_query: Semantic versioning query.

    Returns:
        The response.
    """

    async with Context.start_ep(
        request=request,
    ) as ctx:
        return await dispatch_impl(
            request=request,
            backend_name=backend_name,
            version_query=version_query,
            context=ctx,
        )


@router.post(
    "/{backend_name}/{version_query}/{rest_of_path:path}", summary="Dispatch POST"
)
async def dispatch_post(
    request: Request, backend_name: str, version_query: str
) -> Response:
    """
    Dispatch `POST` requests.

    Parameters:
        request: Incoming request.
        backend_name: Target backend's name.
        version_query: Semantic versioning query.

    Returns:
        The response.
    """

    async with Context.start_ep(
        request=request,
    ) as ctx:
        return await dispatch_impl(
            request=request,
            backend_name=backend_name,
            version_query=version_query,
            context=ctx,
        )


@router.put(
    "/{backend_name}/{version_query}/{rest_of_path:path}", summary="Dispatch POST"
)
async def dispatch_put(
    request: Request, backend_name: str, version_query: str
) -> Response:
    """
    Dispatch `PUT` requests.

    Parameters:
        request: Incoming request.
        backend_name: Target backend's name.
        version_query: Semantic versioning query.

    Returns:
        The response.
    """

    async with Context.start_ep(
        request=request,
    ) as ctx:
        return await dispatch_impl(
            request=request,
            backend_name=backend_name,
            version_query=version_query,
            context=ctx,
        )


@router.delete(
    "/{backend_name}/{version_query}/{rest_of_path:path}", summary="Dispatch POST"
)
async def dispatch_delete(
    request: Request, backend_name: str, version_query: str
) -> Response:
    """
    Dispatch `DELETE` requests.

    Parameters:
        request: Incoming request.
        backend_name: Target backend's name.
        version_query: Semantic versioning query.

    Returns:
        The response.
    """

    async with Context.start_ep(
        request=request,
    ) as ctx:
        return await dispatch_impl(
            request=request,
            backend_name=backend_name,
            version_query=version_query,
            context=ctx,
        )
