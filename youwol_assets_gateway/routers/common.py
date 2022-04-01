from fastapi import HTTPException
from youwol_assets_gateway.configurations import Configuration
from youwol_assets_gateway.utils import raw_id_to_asset_id
from youwol_utils.context import Context


async def assert_read_permissions_from_raw_id(raw_id: str, configuration: Configuration, context: Context):
    assets_db = configuration.assets_client
    asset_id = raw_id_to_asset_id(raw_id)
    permissions = await assets_db.get_permissions(asset_id=asset_id, headers=context.headers())
    if not permissions['read']:
        raise HTTPException(status_code=403, detail=f"Unauthorized to access {raw_id}")


async def assert_write_permissions_from_raw_id(raw_id: str, configuration: Configuration, context: Context):
    assets_db = configuration.assets_client
    asset_id = raw_id_to_asset_id(raw_id)
    permissions = await assets_db.get_permissions(asset_id=asset_id, headers=context.headers())
    if not permissions['write']:
        raise HTTPException(status_code=403, detail=f"Unauthorized to write {raw_id}")
