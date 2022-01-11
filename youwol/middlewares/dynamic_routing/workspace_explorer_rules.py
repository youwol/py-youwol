import asyncio
from typing import Union, TypeVar, List, Optional

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from youwol.environment.clients import RemoteClients, LocalClients
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.context import Context
from youwol.services.backs.assets_gateway.models import ChildrenResponse, ItemResponse, FolderResponse
from youwol.utils_low_level import JSON

PydanticType = TypeVar("PydanticType")


def cast_response(response: Union[JSON, BaseException], _type: PydanticType):
    if isinstance(response, Exception):
        raise response
    return _type(**response)


class GetChildrenDispatch(AbstractDispatch):

    @staticmethod
    async def is_matching(request: Request) -> bool:
        return request.method == "GET" \
               and request.url.path.startswith("/api/assets-gateway/tree/") \
               and "/folders/" in request.url.path and request.url.path.endswith('/children') \
               and "Python" not in request.headers.get('user-agent')

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if not await GetChildrenDispatch.is_matching(request=request):
            return None

        local_gtw = LocalClients.get_assets_gateway_client(context=context)
        remote_gtw = await RemoteClients.get_assets_gateway_client(context=context)
        folder_id = request.url.path.split('/api/assets-gateway/tree/folders/')[1].split('/')[0]

        local_resp, remote_resp = await asyncio.gather(
            local_gtw.get_tree_folder_children(folder_id=folder_id),
            remote_gtw.get_tree_folder_children(folder_id=folder_id),
            return_exceptions=True
            )
        if isinstance(remote_resp, Exception):
            return JSONResponse(local_resp)
        if isinstance(local_resp, Exception):
            return JSONResponse(remote_resp)
        local_children: ChildrenResponse = cast_response(local_resp, ChildrenResponse)
        remote_children: ChildrenResponse = cast_response(remote_resp, ChildrenResponse)
        local_ids = [c.treeId for c in local_children.items] + [c.folderId for c in local_children.folders]
        remote_ids = [c.treeId for c in remote_children.items] + [c.folderId for c in remote_children.folders]

        return JSONResponse({
            "items": [self.decorate_with_metadata(item, local_ids, remote_ids)
                      for item in local_children.items] +
                     [self.decorate_with_metadata(item, local_ids, remote_ids)
                      for item in remote_children.items if item.treeId not in local_ids],
            "folders": [self.decorate_with_metadata(folder, local_ids, remote_ids)
                        for folder in local_children.folders] +
                       [self.decorate_with_metadata(folder, local_ids, remote_ids)
                        for folder in remote_children.folders if folder.folderId not in local_ids],
            })

    @staticmethod
    def decorate_with_metadata(item: Union[ItemResponse, FolderResponse], local_ids: List[str], remote_ids: List[str]):
        tree_id = item.treeId if isinstance(item, ItemResponse) else item.folderId
        return {
            **item.dict(),
            **{
                'origin': {
                    'remote': tree_id in remote_ids,
                    'local': tree_id in local_ids
                    }
                }
            }


class GetPermissionsDispatch(AbstractDispatch):

    @staticmethod
    async def is_matching(request: Request) -> bool:
        return request.method == "GET" \
               and request.url.path.startswith("/api/assets-gateway/tree/") \
               and request.url.path.endswith('/permissions') \
               and "Python" not in request.headers.get('user-agent')

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if not await GetPermissionsDispatch.is_matching(request=request):
            return None

        local_gtw = LocalClients.get_assets_gateway_client(context=context)
        remote_gtw = await RemoteClients.get_assets_gateway_client(context=context)
        item_id = request.url.path.split('/api/assets-gateway/tree/')[1].split('/')[0]

        local_resp, remote_resp = await asyncio.gather(
            local_gtw.get_permissions(item_id=item_id),
            remote_gtw.get_permissions(item_id=item_id),
            return_exceptions=True
            )
        if isinstance(local_resp, Exception):
            return JSONResponse(remote_resp)

        return JSONResponse(local_resp)


class GetItemDispatch(AbstractDispatch):

    @staticmethod
    async def is_matching(request: Request) -> bool:
        return request.method == "GET" \
               and request.url.path.startswith('/api/assets-gateway/tree/items/') \
               and "Python" not in request.headers.get('user-agent')

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if not await GetItemDispatch.is_matching(request=request):
            return None

        local_gtw = LocalClients.get_assets_gateway_client(context=context)
        remote_gtw = await RemoteClients.get_assets_gateway_client(context=context)
        item_id = request.url.path.split('/api/assets-gateway/tree/items/')[1]

        local_resp, remote_resp = await asyncio.gather(
            local_gtw.get_tree_item(item_id=item_id),
            remote_gtw.get_tree_item(item_id=item_id),
            return_exceptions=True
            )
        if isinstance(local_resp, Exception):
            return JSONResponse(remote_resp)

        return JSONResponse(local_resp)
