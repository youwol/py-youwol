from fastapi import APIRouter, Depends
from starlette.requests import Request

from youwol_utils import (HTTPException)
from youwol_utils.context import Context
from ..configurations import Configuration, get_configuration
from ..utils import raw_id_to_asset_id

router = APIRouter()


@router.get("/explorer/{library_id}/{version}/{rest_of_path:path}",
            summary="delete a specific version")
async def get_explorer(
        request: Request,
        library_id: str,
        rest_of_path: str,
        version: str,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            action=f'get explorer data',
            request=request,
            with_attributes={"libraryId": library_id, version: 'version'}
    ) as ctx:

        assets_db = configuration.assets_client
        asset_id = raw_id_to_asset_id(library_id)
        permissions = await assets_db.get_permissions(asset_id=asset_id, headers=ctx.headers())
        if not permissions['read']:
            raise HTTPException(status_code=401, detail=f"Unauthorized to access {library_id}")

        cdn_client = configuration.cdn_client
        return await cdn_client.get_explorer(library_id=library_id,
                                             version=version,
                                             folder_path=rest_of_path,
                                             headers=ctx.headers())
