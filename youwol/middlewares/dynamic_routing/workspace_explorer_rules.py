import asyncio
from typing import Union, TypeVar, List, Optional

from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from youwol.backends.assets_gateway.models import ChildrenResponse, ItemResponse, FolderResponse
from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.middlewares.models_dispatch import AbstractDispatch
from youwol.routers.commons import ensure_local_path
from youwol.utils.utils_low_level import JSON
from youwol_utils.context import Context
from youwol_utils.request_info_factory import url_match

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
               and ('user-agent' in request.headers
                    and "Python" not in request.headers.get('user-agent')
                    # => for now, until for browser request
                    )

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if not await GetChildrenDispatch.is_matching(request=request):
            return None

        env = await context.get('env', YouwolEnvironment)
        local_gtw = LocalClients.get_assets_gateway_client(env=env)
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
               and ('user-agent' in request.headers and "Python" not in request.headers.get('user-agent'))

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:

        if not await GetPermissionsDispatch.is_matching(request=request):
            return None

        async with context.start(action="GetPermissionsDispatch.apply") as ctx:

            env = await ctx.get('env', YouwolEnvironment)
            local_gtw = LocalClients.get_assets_gateway_client(env=env)
            remote_gtw = await RemoteClients.get_assets_gateway_client(context=ctx)
            item_id = request.url.path.split('/api/assets-gateway/tree/')[1].split('/')[0]

            local_resp, remote_resp = await asyncio.gather(
                local_gtw.get_permissions(item_id=item_id),
                remote_gtw.get_permissions(item_id=item_id),
                return_exceptions=True
                )
            if isinstance(local_resp, Exception):
                await ctx.info("Asset not found in local store, return remote data")
                return JSONResponse(remote_resp)

            await ctx.info("Asset found in local store, return local data")
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

        async with context.start(action="GetItemDispatch.apply") as ctx:
            env = await ctx.get('env', YouwolEnvironment)
            local_gtw = LocalClients.get_assets_gateway_client(env=env)
            remote_gtw = await RemoteClients.get_assets_gateway_client(context=ctx)
            item_id = request.url.path.split('/api/assets-gateway/tree/items/')[1]

            local_resp, remote_resp = await asyncio.gather(
                local_gtw.get_tree_item(item_id=item_id),
                remote_gtw.get_tree_item(item_id=item_id),
                return_exceptions=True
            )
            if isinstance(local_resp, Exception):
                await ctx.info("Asset not found in local store, return remote data")
                return JSONResponse(remote_resp)

            await ctx.info("Asset found in local store, return local data")
            return JSONResponse(local_resp)


class MoveBorrowInRemoteFolderDispatch(AbstractDispatch):

    async def apply(self,
                    request: Request,
                    call_next: RequestResponseEndpoint,
                    context: Context
                    ) -> Optional[Response]:
        env = await context.get('env', YouwolEnvironment)
        match, replaced = url_match(request=request, pattern='POST:/api/assets-gateway/tree/*/*')
        if not match or replaced[-1] not in ['move', 'borrow']:
            return None

        async with context.start(action="MoveBorrowInRemoteFolderDispatch.apply") as ctx:
            body = await request.json()
            folder_id = body["destinationFolderId"]
            await ensure_local_path(folder_id=folder_id, env=env, context=ctx)
            gtw = LocalClients.get_assets_gateway_client(env=env)
            # Ideally we would like to proceed to call_next(request), it is not possible because the body of the
            # request has already been fetched (and would result in a fast api getting stuck trying to parse it again)
            headers = {**ctx.headers(), 'py-youwol-local-only': 'true'}
            if replaced[-1] == "move":
                resp = await gtw.move_tree_item(tree_id=replaced[0], body=body, headers=headers)
                return JSONResponse(resp)

            resp = await gtw.borrow_tree_item(tree_id=replaced[0], body=body, headers=headers)
            return JSONResponse(resp)
