# standard library
import base64
import datetime

# third parties
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request as FastAPI_Request
from fastapi import Response as FastAPI_Response
from fastapi import status

# relative
from ...utils.servers.request import get_real_client_ip
from .models import Body, Handler, Request, status_200_OK, status_204_NoContent

router = APIRouter(tags=["mock"])

handlers: dict[str, Handler] = {}


async def auth_middleware(request: FastAPI_Request) -> None:
    if "memberof" not in request.state.user_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if (
        "/youwol-users/youwol-devs/youwol-admins"
        not in request.state.user_info["memberof"]
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


router_admin = APIRouter(
    tags=["mock", "admin"], dependencies=[Depends(auth_middleware)]
)


def ref(method: str, handler_id: str, public: bool):
    return f"{method}:{handler_id}{(':public' if public else '')}"


@router_admin.put("/pub/{handler_id}")
async def setup_handler_public(handler: Handler, handler_id: str):
    return await setup_handler(handler, handler_id, True)


@router_admin.get("/pub/{handler_id}/{method}")
async def get_handler_public(handler_id: str, method: str):
    return await get_handler(handler_id, method, True)


@router_admin.delete("/pub/{handler_id}/{method}")
async def remove_handler_public(handler_id: str, method: str):
    return await remove_handler(handler_id, method, True)


@router_admin.put("/{handler_id}")
async def setup_handler(handler: Handler, handler_id: str, public=False):
    if handler.response.status is None:
        if handler.response.body is None:
            handler.response.status = status_204_NoContent
        else:
            handler.response.status = status_200_OK

    previous_handler = handlers.pop(ref(handler.method, handler_id, public), None)
    if previous_handler is not None and handler.history is None:
        handler.history = previous_handler.history

    handlers[ref(handler.method, handler_id, public)] = handler
    return handler


@router_admin.get("/{handler_id}/{method}")
async def get_handler(handler_id: str, method: str, public=False):
    handler = handlers.get(ref(method, handler_id, public))
    return (
        handler
        if handler is not None
        else FastAPI_Response(status_code=status.HTTP_404_NOT_FOUND)
    )


@router_admin.delete("/{handler_id}/{method}")
async def remove_handler(handler_id: str, method: str, public=False):
    if handlers.get(ref(method, handler_id, public)) is None:
        return FastAPI_Response(status_code=status.HTTP_404_NOT_FOUND)

    return handlers.pop(ref(method, handler_id, public))


router.include_router(prefix="/admin", router=router_admin)


@router.get("/pub/{handler_id}")
async def handle_public_get(handler_id: str, request: FastAPI_Request):
    return await handle_public("GET", handler_id, request)


@router.put("/pub/{handler_id}")
async def handle_public_put(handler_id: str, request: FastAPI_Request):
    return await handle_public("PUT", handler_id, request)


@router.post("/pub/{handler_id}")
async def handle_public_post(handler_id: str, request: FastAPI_Request):
    return await handle_public("POST", handler_id, request)


@router.delete("/pub/{handler_id}")
async def handle_public_delete(handler_id: str, request: FastAPI_Request):
    return await handle_public("DELETE", handler_id, request)


@router.get("/{handler_id}")
async def handle_get(handler_id: str, request: FastAPI_Request):
    return await handle("GET", handler_id, request)


@router.put("/{handler_id}")
async def handle_put(handler_id: str, request: FastAPI_Request):
    return await handle("PUT", handler_id, request)


@router.post("/{handler_id}")
async def handle_post(handler_id: str, request: FastAPI_Request):
    return await handle("POST", handler_id, request)


@router.delete("/{handler_id}")
async def handle_delete(handler_id: str, request: FastAPI_Request):
    return await handle("DELETE", handler_id, request)


async def handle_public(method: str, handler_id: str, req: FastAPI_Request):
    return await handle(method, handler_id, req, public=True)


async def handle(method: str, handler_id: str, req: FastAPI_Request, public=False):
    handler = handlers.get(ref(method, handler_id, public))

    if handler is None:
        return FastAPI_Response(status_code=status.HTTP_404_NOT_FOUND)

    if handler.history is None:
        handler.history = []
    elif len(handler.history) == handler.historyCapacity:
        handler.history.pop(0)

    handler.history.append(
        Request(
            timestamp=int(datetime.datetime.now().timestamp()),
            method=method,
            url=str(req.url),
            ip=get_real_client_ip(req),
            headers={k: req.headers.getlist(k) for k in req.headers.keys()},
            body=(
                Body(
                    mimeType=req.headers.get("content-type"),
                    contentBase64=base64.standard_b64encode(await req.body()).decode(),
                )
                if req.method != "GET"
                else None
            ),
            auth=None if public else str(req.state.user_info),
        )
    )

    return (
        FastAPI_Response(
            base64.standard_b64decode(handler.response.body.contentBase64),
            status_code=handler.response.status.code,
            media_type=handler.response.body.mimeType,
        )
        if handler.response.body is not None
        else FastAPI_Response(status_code=handler.response.status.code)
    )
