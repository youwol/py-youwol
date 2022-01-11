import json
from dataclasses import dataclass

from youwol_utils import JSON
from youwol.configuration.clients import RemoteClients, LocalClients
from youwol.routers.environment.upload_assets.models import UploadTask


@dataclass
class UploadFluxProjectTask(UploadTask):

    async def get_raw(self) -> JSON:
        asset_gtw = LocalClients.get_assets_gateway_client(context=self.context)
        data = await asset_gtw.get_raw(kind='flux-project', raw_id=self.raw_id, content_type='application/json')
        return data

    async def create_raw(self, data: JSON, folder_id: str):
        data['projectId'] = self.raw_id
        remote_gtw = await RemoteClients.get_assets_gateway_client(context=self.context)
        await remote_gtw.put_asset_with_raw(
            kind='flux-project',
            folder_id=folder_id,
            data=json.dumps(data).encode()
            )

    async def update_raw(self, data: JSON, folder_id: str):
        # <!> flux_client will be removed as it should not be available
        flux_client = await RemoteClients.get_flux_client(context=self.context)
        await flux_client.update_project(project_id=self.raw_id, body=data)
