from dataclasses import dataclass

from youwol.environment.clients import RemoteClients, LocalClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.download_assets import zip_project
from youwol.routers.environment.upload_assets.models import UploadTask
from youwol_utils import JSON
from youwol_utils.context import Context


@dataclass
class UploadFluxProjectTask(UploadTask):

    async def get_raw(self, context: Context) -> JSON:
        async with context.start(action="UploadFluxProjectTask.get_raw") as ctx:  # type: Context
            env = await context.get('env', YouwolEnvironment)
            flux_client = LocalClients.get_assets_gateway_client(env=env).get_flux_backend_router()
            data = await flux_client.get_project(project_id=self.raw_id, headers=ctx.headers())
            return data

    async def create_raw(self, data: JSON, folder_id: str, context: Context):

        async with context.start("UploadFluxProjectTask.create_raw") as ctx:  # type: Context
            data['projectId'] = self.raw_id
            zipped = zip_project(project=data)
            remote_gtw = await RemoteClients.get_assets_gateway_client(remote_host=self.remote_host, context=ctx)
            await remote_gtw.get_flux_backend_router().upload_project(
                project_id=self.raw_id,
                data={'file': zipped, 'content_encoding': 'identity'},
                params={'folder-id': folder_id},
                headers=ctx.headers()
                )

    async def update_raw(self, data: JSON, folder_id: str, context: Context):
        # <!> flux_client will be removed as it should not be available
        async with context.start("UploadFluxProjectTask.update_raw") as ctx:  # type: Context
            remote_gtw = await RemoteClients.get_assets_gateway_client(remote_host=self.remote_host, context=ctx)
            flux_client = remote_gtw.get_flux_backend_router()
            await flux_client.update_project(project_id=self.raw_id, body=data, headers=ctx.headers())
