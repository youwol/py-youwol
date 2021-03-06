from fastapi import APIRouter, Depends, Query
from fastapi import Query as QueryParam
from starlette.requests import Request
from starlette.responses import Response

from youwol_assets_gateway.raw_stores import AssetMeta
from youwol_assets_gateway.routers.common import assert_read_permissions_from_raw_id, \
    assert_write_permissions_from_raw_id, create_asset, delete_asset, assert_write_permissions_folder_id
from youwol_utils.context import Context
from youwol_assets_gateway.configurations import Configuration, get_configuration
from youwol_utils.http_clients.assets_gateway import NewAssetResponse
from youwol_utils.http_clients.stories_backend import StoryResp, GetGlobalContentResp, PostGlobalContentBody, \
    MoveDocumentResp, MoveDocumentBody, GetDocumentResp, PostDocumentBody, PutDocumentBody, GetChildrenResp, \
    PostStoryBody, GetContentResp, PostContentBody, DeleteResp, PutStoryBody, PostPluginBody, PostPluginResponse

router = APIRouter(tags=["assets-gateway.stories-backend"])


@router.get("/healthz")
async def healthz(
        request: Request,
        configuration: Configuration = Depends(get_configuration)):
    async with Context.start_ep(
            request=request
    ) as ctx:
        return await configuration.stories_client.healthz(headers=ctx.headers())


@router.put(
    "/stories",
    response_model=NewAssetResponse,
    summary="create a new story")
async def put_story(
        request: Request,
        body: PutStoryBody,
        folder_id: str = Query(None, alias="folder-id"),
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        story = await configuration.stories_client.create_story(body=body.dict(), headers=ctx.headers())
        return await create_asset(
            kind="story",
            raw_id=story["storyId"],
            raw_response=story,
            folder_id=folder_id,
            metadata=AssetMeta(name=story["title"]),
            context=ctx,
            configuration=configuration
        )


@router.post(
    "/stories",
    response_model=NewAssetResponse,
    summary="publish a story from zip file")
async def publish_story(
        request: Request,
        folder_id: str = Query(None, alias="folder-id"),
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        form = await request.form()
        form = {
            'file': await form.get('file').read(),
            'content_encoding': form.get('content_encoding', 'identity')
        }
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        story = await configuration.stories_client.publish_story(data=form, headers=ctx.headers())
        return await create_asset(
            kind="story",
            raw_id=story["storyId"],
            raw_response=story,
            folder_id=folder_id,
            metadata=AssetMeta(name=story["title"]),
            context=ctx,
            configuration=configuration
        )


@router.delete(
    "/stories/{story_id}",
    response_model=DeleteResp,
    summary="delete a story with its children")
async def delete_story(
        request: Request,
        story_id: str,
        purge: bool = False,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        await configuration.stories_client.delete_story(story_id=story_id, headers=ctx.headers())
        if purge:
            await delete_asset(raw_id=story_id, configuration=configuration, context=ctx)
        else:
            # delete treedb item
            pass


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
    "/stories/{story_id}/documents/{document_id}/children",
    response_model=GetChildrenResp,
    summary="retrieve the children's list of a document")
async def get_children(
        request: Request,
        story_id: str,
        document_id: str,
        from_position: float = QueryParam(0, alias="from-position"),
        count: int = QueryParam(1000),
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.get_children(story_id=story_id, parent_document_id=document_id,
                                                               from_index=from_position, count=count,
                                                               headers=ctx.headers())


@router.put(
    "/stories/{story_id}/documents",
    response_model=GetDocumentResp,
    summary="create a new document")
async def put_document(
        request: Request,
        story_id: str,
        body: PutDocumentBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.create_document(story_id=story_id, body=body.dict(),
                                                                  headers=ctx.headers())


@router.get(
    "/stories/{story_id}/documents/{document_id}",
    response_model=GetDocumentResp,
    summary="retrieve a document")
async def get_document(
        request: Request,
        story_id: str,
        document_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.get_document(story_id=story_id, document_id=document_id,
                                                               headers=ctx.headers())


@router.post(
    "/stories/{story_id}/documents/{document_id}",
    response_model=GetDocumentResp,
    summary="update a document")
async def post_document(
        request: Request,
        story_id: str,
        document_id: str,
        body: PostDocumentBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.update_document(story_id=story_id, document_id=document_id,
                                                                  body=body.dict(), headers=ctx.headers())


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


@router.post(
    "/stories/{story_id}/documents/{document_id}/move",
    response_model=MoveDocumentResp,
    summary="update a document")
async def move_document(
        request: Request,
        story_id: str,
        document_id: str,
        body: MoveDocumentBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.move_document(story_id=story_id, document_id=document_id,
                                                                body=body.dict(), headers=ctx.headers())


@router.get(
    "/stories/{story_id}/download-zip",
    summary="create a new story")
async def download_zip(
        request: Request,
        story_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        content = await configuration.stories_client.download_zip(story_id=story_id, headers=ctx.headers())
        return Response(content=content, headers={'content-type': 'application/zip'})


@router.post(
    "/stories/{story_id}",
    response_model=StoryResp,
    summary="update story's metadata")
async def post_story(
        request: Request,
        story_id: str,
        body: PostStoryBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
        request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.update_story(story_id=story_id, body=body.dict(),
                                                               headers=ctx.headers())


@router.get(
    "/stories/{story_id}/contents/{content_id}",
    response_model=GetContentResp,
    summary="retrieve a document's content")
async def get_content(
        request: Request,
        story_id: str,
        content_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.get_content(story_id=story_id, content_id=content_id,
                                                              headers=ctx.headers())


@router.post(
    "/stories/{story_id}/contents/{content_id}",
    summary="update a document's content")
async def post_content(
        request: Request,
        story_id: str,
        content_id: str,
        body: PostContentBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.set_content(story_id=story_id, content_id=content_id,
                                                              body=body.dict(), headers=ctx.headers())


@router.delete(
    "/stories/{story_id}/documents/{document_id}",
    response_model=DeleteResp,
    summary="delete a document with its children")
async def delete_document(
        request: Request,
        story_id: str,
        document_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.delete_document(story_id=story_id, document_id=document_id,
                                                                  headers=ctx.headers())


@router.post(
    "/stories/{story_id}/plugins",
    response_model=PostPluginResponse,
    summary="update a document")
async def add_plugin(
        request: Request,
        story_id: str,
        body: PostPluginBody,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=story_id, configuration=configuration, context=ctx)
        return await configuration.stories_client.add_plugin(story_id=story_id, body=body.dict(),
                                                             headers=ctx.headers())
