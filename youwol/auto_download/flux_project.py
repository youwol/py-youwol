import json
from dataclasses import dataclass
from fastapi import HTTPException
from auto_download.common import (
    create_asset_local
    )
from auto_download.models import DownloadTask

from youwol_utils.clients.flux.flux import FluxClient


@dataclass
class DownloadFluxProjectTask(DownloadTask):

    def download_id(self):
        return self.raw_id

    async def is_local_up_to_date(self):

        local_flux: FluxClient = self.context.config.localClients.flux_client
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

        remote_gtw = await self.context.config.get_assets_gateway_client(context=self.context)
        default_owning_folder_id = (await self.context.config.get_default_drive()).downloadFolderId
        await create_asset_local(
            asset_id=self.asset_id,
            kind='flux-project',
            default_owning_folder_id=default_owning_folder_id,
            get_raw_data=lambda: remote_gtw.get_raw(kind='flux-project', raw_id=self.raw_id,
                                                    content_type="application/json"),
            to_post_raw_data=to_saved_project,
            context=self.context
            )
