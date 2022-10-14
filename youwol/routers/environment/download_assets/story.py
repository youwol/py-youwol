from dataclasses import dataclass

from fastapi import HTTPException

from youwol.environment.clients import LocalClients, RemoteClients
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.download_assets.common import (
    create_asset_local
)
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils import Context
from youwol_utils.clients.stories.stories import StoriesClient


@dataclass
class DownloadStoryTask(DownloadTask):

    def download_id(self):
        return self.raw_id

    async def is_local_up_to_date(self, context: Context):

        env: YouwolEnvironment = await context.get('env', YouwolEnvironment)
        local_story: StoriesClient = LocalClients.get_stories_client(env=env)
        try:
            await local_story.get_story(story_id=self.raw_id, headers=context.headers())
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
        await create_asset_local(
            asset_id=self.asset_id,
            kind='story',
            default_owning_folder_id=default_drive.downloadFolderId,
            get_raw_data=lambda _ctx: remote_gtw.get_stories_backend_router().download_zip(
                story_id=self.raw_id,
                headers=_ctx.headers()),
            to_post_raw_data=lambda pack: {'file': pack},
            context=context
            )
