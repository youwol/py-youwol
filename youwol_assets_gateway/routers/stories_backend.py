from fastapi import APIRouter, Depends
from starlette.requests import Request

from youwol_assets_gateway.routers.common import assert_read_permissions_from_raw_id, \
    assert_write_permissions_from_raw_id
from youwol_utils.context import Context
from youwol_assets_gateway.configurations import Configuration, get_configuration
from youwol_utils.http_clients.stories_backend import StoryResp, GetGlobalContentResp, PostGlobalContentBody

router = APIRouter()


@router.get(
    "/stories/{story_id}",
    response_model=StoryResp,
    summary="retrieve a story")
async def get_story(
        request: Request,
        story_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.get_story(story_id=story_id, headers=ctx.headers())


@router.get(
    "/stories/{story_id}/global-contents",
    response_model=GetGlobalContentResp,
    summary="retrieve a document's content")
async def get_global_content(
        request: Request,
        story_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.get_global_contents(story_id=story_id, headers=ctx.headers())


@router.post(
    "/stories/{story_id}/global-contents",
    summary="retrieve a document's content")
async def post_global_content(
        request: Request,
        story_id: str,
        body: PostGlobalContentBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.post_global_contents(story_id=story_id, body=body.dict(),
                                                                       headers=ctx.headers())

