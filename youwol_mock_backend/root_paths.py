import base64
import datetime
from fastapi import APIRouter, Request as FastAPI_Request, Response as FastAPI_Response, status
from starlette.responses import JSONResponse
from typing import Dict, List

from .models import Handler, status_200_OK, status_204_NoContent, Request, Body

router = APIRouter(tags=['fake'])

handlers: Dict[str, Handler] = dict()


def ref(method: str, handler_id: str):
    return f"{method}:{handler_id}"


@router.put("/admin/{handler_id}")
async def setup_handler(handler: Handler, handler_id: str):
    if handler.response.status is None:
        if handler.response.body is None:
            handler.response.status = status_204_NoContent
        else:
            handler.response.status = status_200_OK

    method = handler.method
    handlers[ref(method, handler_id)] = handler
    return handler


@router.get("/healthz")
async def healthz():
    return JSONResponse(status_code=200, content={"status": "fake backend ok"})


@router.get("/admin/{handler_id}/{method}")
async def get_handler(handler_id: str, method: str):
    handler = handlers.get(ref(method, handler_id))
    return handler if handler is not None else FastAPI_Response(status_code=status.HTTP_404_NOT_FOUND)


@router.delete("/admin/{handler_id}/{method}")
async def remove_handler(handler_id: str, method: str):
    if handlers.get(ref(method, handler_id)) is None:
        return FastAPI_Response(status_code=status.HTTP_202_ACCEPTED)

    handlers.pop(ref(method, handler_id))
    return FastAPI_Response(status_code=status.HTTP_404_NOT_FOUND)


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


async def handle(method: str, handler_id: str, req: FastAPI_Request):
    handler = handlers.get(ref(method, handler_id))

    if handler is None:
        return FastAPI_Response(status_code=status.HTTP_404_NOT_FOUND)

    headers: Dict[str, List[str]] = dict()
    for key in req.headers.keys():
        headers[key] = req.headers.getlist(key)

    request = Request(
        timestamp=int(datetime.datetime.now().timestamp()),
        method=method,
        url=str(req.url),
        ip=req.client.host,
        headers=headers,
        body=Body(
            mimeType=req.headers.get("content-type"),
            contentBase64=base64.standard_b64encode(await req.body()).decode()
        ) if req.method != "GET" else None
    )

    handler.history.append(request)
    if len(handler.history) > handler.historySize:
        handler.history.pop(0)

    return FastAPI_Response(
        base64.standard_b64decode(handler.response.body.contentBase64),
        status_code=handler.response.status.code,
        media_type=handler.response.body.mimeType,
    ) if handler.response.body is not None else FastAPI_Response(status_code=handler.response.status.code)
