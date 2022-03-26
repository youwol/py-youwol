import json
from dataclasses import dataclass

from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.upload_assets.models import UploadTask
from youwol_utils import JSON
from youwol_utils.context import Context


@dataclass
class UploadFluxProjectTask(UploadTask):

    async def get_raw(self) -> JSON:
        env = await self.context.get('env', YouwolEnvironment)
        asset_gtw = LocalClients.get_assets_gateway_client(env=env)
        data = await asset_gtw.get_raw(kind='flux-project', raw_id=self.raw_id, content_type='application/json')
        return data

    async def create_raw(self, data: JSON, folder_id: str):

        async with self.context.start("UploadFluxProjectTask.create_raw") as ctx:  # type: Context
            data['projectId'] = self.raw_id
            remote_gtw = await RemoteClients.get_assets_gateway_client(context=ctx)
            await remote_gtw.put_asset_with_raw(
                kind='flux-project',
                folder_id=folder_id,
                data=json.dumps(data).encode(),
                headers=ctx.headers()
                )

    async def update_raw(self, data: JSON, folder_id: str):
        # <!> flux_client will be removed as it should not be available
        async with self.context.start("UploadFluxProjectTask.update_raw") as ctx:  # type: Context
            flux_client = await RemoteClients.get_flux_client(context=ctx)
            await flux_client.update_project(project_id=self.raw_id, body=data, headers=ctx.headers())
