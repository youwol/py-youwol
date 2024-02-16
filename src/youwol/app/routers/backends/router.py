# third parties
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from starlette.requests import Request

# Youwol application
from youwol.app.environment import YouwolEnvironment
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

    env = await context.get("env", YouwolEnvironment)
    backend = await ensure_running(
        request=request,
        backend_name=backend_name,
        version_query=version_query,
        timeout=10,
        context=context,
    )
    backend.endpoint_ctx_id.append(context.parent_uid)
    if not backend:
        return HTTPException(
            status_code=404,
            detail=f"No proxied backends match the query '{backend_name}#{version_query}",
        )

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
async def dispatch_get(request: Request, backend_name: str, version_query: str):
    """
    Dispatch.

    Parameters:
        request: incoming request
        backend_name: target backend's name
        version_query: semantic versioning query

    Return:
        The response
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
async def dispatch_post(request: Request, backend_name: str, version_query: str):
    """
    Dispatch.

    Parameters:
        request: incoming request
        backend_name: target backend's name
        version_query: semantic versioning query

    Return:
        The response
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
async def dispatch_put(request: Request, backend_name: str, version_query: str):
    """
    Dispatch.

    Parameters:
        request: incoming request
        backend_name: target backend's name
        version_query: semantic versioning query

    Return:
        The response
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
async def dispatch_delete(request: Request, backend_name: str, version_query: str):
    """
    Dispatch.

    Parameters:
        request: incoming request
        backend_name: target backend's name
        version_query: semantic versioning query

    Return:
        The response
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
