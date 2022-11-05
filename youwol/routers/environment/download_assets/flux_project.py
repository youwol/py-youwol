import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from aiohttp import FormData
from fastapi import HTTPException

from youwol.environment.clients import LocalClients, RemoteClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.download_assets.common import (
    create_asset_local
)
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils import Context, write_json
from youwol_utils.clients.flux.flux import FluxClient


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

        env: YouwolEnvironment = await context.get('env', YouwolEnvironment)

        remote_gtw = await RemoteClients.get_assets_gateway_client(remote_host=env.selectedRemote, context=context)
        default_drive = await env.get_default_drive(context=context)

        async def get_raw_data(ctx_get_raw: Context):
            project = await remote_gtw.get_flux_backend_router()\
                .get_project(project_id=self.raw_id, headers=ctx_get_raw.headers())
            return project

        async def post_raw_data(folder_id: str, raw_data, ctx: Context):
            project = raw_data
            zip_bytes = zip_project(project=project)
            form_data = FormData()
            form_data.add_field(name='file', value=zip_bytes, content_type="application/json")

            resp = await LocalClients \
                .get_assets_gateway_client(env=env) \
                .get_flux_backend_router()\
                .upload_project(data=form_data,
                                project_id=self.raw_id,
                                params={
                                  'folder-id': folder_id,
                                  'name': project['name']
                                },
                                headers=ctx.headers()
                                )
            return resp

        await create_asset_local(
            asset_id=self.asset_id,
            kind='flux-project',
            default_owning_folder_id=default_drive.downloadFolderId,
            get_raw_data=get_raw_data,
            post_raw_data=post_raw_data,
            context=context
            )
