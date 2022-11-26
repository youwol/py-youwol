from dataclasses import dataclass

from aiohttp import FormData
from fastapi import HTTPException

import youwol_flux_backend
from youwol.environment import LocalClients, YouwolEnvironment
from youwol.routers.environment.download_assets.common import (
    create_asset_local
)
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils import Context, decode_id
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.flux.flux import FluxClient


async def sync_raw_data(asset_id: str, remote_gtw: AssetsGatewayClient, caller_context: Context):

    async with caller_context.start(action="Sync. raw data of flux-project") as ctx:  # type: Context

        env: YouwolEnvironment = await ctx.get('env', YouwolEnvironment)
        raw_id = decode_id(asset_id)
        project = await remote_gtw.get_flux_backend_router() \
            .get_project(project_id=raw_id, headers=ctx.headers())

        zip_bytes = youwol_flux_backend.zip_project(project=project)
        form_data = FormData()
        form_data.add_field(name='file', value=zip_bytes, content_type="application/octet-stream")

        await LocalClients.get_flux_client(env) \
            .upload_project(data=form_data, project_id=raw_id, params={'name': project['name']},
                            headers=ctx.headers())


@dataclass
class DownloadFluxProjectTask(DownloadTask):

    def download_id(self):
        return self.raw_id

    async def is_local_up_to_date(self, context: Context):

        env: YouwolEnvironment = await context.get('env', YouwolEnvironment)
        local_flux: FluxClient = LocalClients.get_flux_client(env=env)
        try:
            await local_flux.get_project(project_id=self.raw_id, headers=context.headers())
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            else:
                raise e

    async def create_local_asset(self, context: Context):

        await create_asset_local(
            asset_id=self.asset_id,
            kind='flux-project',
            sync_raw_data=sync_raw_data,
            context=context
            )
