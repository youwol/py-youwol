# standard library
import asyncio

from dataclasses import dataclass

# third parties
from aiohttp import FormData

# Youwol application
from youwol.app.environment import LocalClients, YouwolEnvironment

# Youwol utilities
from youwol.utils import Context, decode_id
from youwol.utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient

# relative
from .common import create_asset_local, is_asset_in_local
from .models import DownloadTask


async def sync_raw_data(
    asset_id: str, remote_gtw: AssetsGatewayClient, caller_context: Context
):
    async with caller_context.start(action="Sync. raw data of file") as ctx:
        env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)
        raw_id = decode_id(asset_id)
        data, info = await asyncio.gather(
            remote_gtw.get_files_backend_router().get(
                file_id=raw_id, headers=ctx.headers()
            ),
            remote_gtw.get_files_backend_router().get_info(
                file_id=raw_id, headers=ctx.headers()
            ),
        )
        metadata = info["metadata"]
        form_data = FormData()
        form_data.add_field(
            name="file",
            value=data,
            filename=metadata["fileName"],
            content_type=info["metadata"]["contentType"],
        )

        form_data.add_field("content_type", metadata["contentType"])
        form_data.add_field("content_encoding", metadata["contentEncoding"])
        form_data.add_field("file_id", raw_id)
        form_data.add_field("file_name", metadata["fileName"])

        resp = await LocalClients.get_files_client(env=env).upload(
            data=form_data, headers=ctx.headers()
        )
        return resp


@dataclass
class DownloadDataTask(DownloadTask):
    def download_id(self):
        return self.raw_id

    async def is_local_up_to_date(self, context: Context):
        return await is_asset_in_local(asset_id=self.asset_id, context=context)

    async def create_local_asset(self, context: Context):
        await create_asset_local(
            asset_id=self.asset_id,
            kind="data",
            sync_raw_data=sync_raw_data,
            context=context,
        )
