# third parties
from fastapi import APIRouter, HTTPException
from starlette.requests import Request

# Youwol application
from youwol.app.environment import YouwolEnvironment

# Youwol utilities
from youwol.utils import Context, YouwolHeaders, redirect_request

router = APIRouter()


async def dispatch_impl(
    request: Request,
    backend_name: str,
    version_query: str,
    rest_of_path: str,
    context: Context,
):

    env = await context.get("env", YouwolEnvironment)
    await context.info(text=f"Dispatch to {rest_of_path}")
    backend = env.proxied_backends.get(name=backend_name, query_version=version_query)
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
        text=f"Redirecting request from '{request.url}' to '{destination}'",
        data={
            "origin": request.url.path,
            "destination": destination,
            "py_youwol_port": env.httpPort,
        },
    )

    resp = await redirect_request(
        incoming_request=request,
        origin_base_path=f"/backends/{backend_name}/{version_query}",
        destination_base_path=destination,
        headers=headers,
    )
    await context.info(
        "Got response from backend",
        data={
            "headers": dict(resp.headers.items()),
            "status": resp.status_code,
        },
    )

    return resp


@router.get(
    "/{backend_name}/{version_query}/{rest_of_path:path}", summary="Dispatch GET."
)
async def dispatch_get(
    request: Request, backend_name: str, version_query: str, rest_of_path: str
):
    """
    Dispatch.

    Parameters:
        request: incoming request
        backend_name: target backend's name
        version_query: semantic versioning query
        rest_of_path: the path on which the API call will be redirected

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
            rest_of_path=rest_of_path,
            context=ctx,
        )


@router.post(
    "/{backend_name}/{version_query}/{rest_of_path:path}", summary="Dispatch POST"
)
async def dispatch_post(
    request: Request, backend_name: str, version_query: str, rest_of_path: str
):
    """
    Dispatch.

    Parameters:
        request: incoming request
        backend_name: target backend's name
        version_query: semantic versioning query
        rest_of_path: the path on which the API call will be redirected

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
            rest_of_path=rest_of_path,
            context=ctx,
        )


@router.put(
    "/{backend_name}/{version_query}/{rest_of_path:path}", summary="Dispatch POST"
)
async def dispatch_put(
    request: Request, backend_name: str, version_query: str, rest_of_path: str
):
    """
    Dispatch.

    Parameters:
        request: incoming request
        backend_name: target backend's name
        version_query: semantic versioning query
        rest_of_path: the path on which the API call will be redirected

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
            rest_of_path=rest_of_path,
            context=ctx,
        )


@router.delete(
    "/{backend_name}/{version_query}/{rest_of_path:path}", summary="Dispatch POST"
)
async def dispatch_delete(
    request: Request, backend_name: str, version_query: str, rest_of_path: str
):
    """
    Dispatch.

    Parameters:
        request: incoming request
        backend_name: target backend's name
        version_query: semantic versioning query
        rest_of_path: the path on which the API call will be redirected

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
            rest_of_path=rest_of_path,
            context=ctx,
        )
