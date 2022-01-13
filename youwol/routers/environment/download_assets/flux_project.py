import json
from dataclasses import dataclass

from fastapi import HTTPException

from youwol.environment.clients import LocalClients, RemoteClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.download_assets.common import (
    create_asset_local
)
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils.clients.flux.flux import FluxClient


@dataclass
class DownloadFluxProjectTask(DownloadTask):

    def download_id(self):
        return self.raw_id

    async def is_local_up_to_date(self):

        env = await self.context.get('env', YouwolEnvironment)
        local_flux: FluxClient = LocalClients.get_flux_client(env=env)
        try:
            await local_flux.get_project(project_id=self.raw_id)
            return True
        except HTTPException as e:
            if e.status_code == 404:
                return False
            else:
                raise e

    async def create_local_asset(self):

        def to_saved_project(retrieved):
            retrieved['projectId'] = self.raw_id
            return json.dumps(retrieved).encode()

        env = await self.context.get('env', YouwolEnvironment)

        remote_gtw = await RemoteClients.get_assets_gateway_client(context=self.context)
        default_drive = await env.get_default_drive(context=self.context)
        await create_asset_local(
            asset_id=self.asset_id,
            kind='flux-project',
            default_owning_folder_id=default_drive.downloadFolderId,
            get_raw_data=lambda: remote_gtw.get_raw(kind='flux-project', raw_id=self.raw_id,
                                                    content_type="application/json"),
            to_post_raw_data=to_saved_project,
            context=self.context
            )
