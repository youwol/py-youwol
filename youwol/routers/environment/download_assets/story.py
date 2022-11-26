from dataclasses import dataclass

from aiohttp import FormData
from fastapi import HTTPException

from youwol.environment import LocalClients, YouwolEnvironment
from youwol.routers.environment.download_assets.common import (
    create_asset_local
)
from youwol.routers.environment.download_assets.models import DownloadTask
from youwol_utils import Context, decode_id
from youwol_utils.clients.assets_gateway.assets_gateway import AssetsGatewayClient
from youwol_utils.clients.stories.stories import StoriesClient


async def sync_raw_data(asset_id: str, remote_gtw: AssetsGatewayClient, caller_context: Context):

    async with caller_context.start(action="Sync. raw data of story") as ctx:  # type: Context

        env: YouwolEnvironment = await ctx.get('env', YouwolEnvironment)
        raw_id = decode_id(asset_id)
        story = await remote_gtw.get_stories_backend_router().download_zip(story_id=raw_id, headers=ctx.headers())

        form_data = FormData()
        form_data.add_field(name='file', value=story)

        resp = await LocalClients.get_stories_client(env=env).publish_story(data=form_data, headers=ctx.headers())
        return resp


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

        await create_asset_local(
            asset_id=self.asset_id,
            kind='story',
            sync_raw_data=sync_raw_data,
            context=context
            )
