from fastapi import APIRouter, Depends, Query
from starlette.requests import Request
from starlette.responses import Response

from youwol_assets_gateway.raw_stores import AssetMeta
from youwol_assets_gateway.routers.common import assert_write_permissions_folder_id, \
    assert_read_permissions_from_raw_id, assert_write_permissions_from_raw_id, create_asset, delete_asset
from youwol_utils.context import Context
from youwol_assets_gateway.configurations import Configuration, get_configuration
from youwol_utils.http_clients.assets_gateway import NewAssetResponse
from youwol_utils.http_clients.flux_backend import Project, NewProject, EditMetadata, ProjectSnippet

router = APIRouter(tags=["assets-gateway.flux-backend"])


@router.post("/projects/create",
             summary="create a new project",
             response_model=NewAssetResponse)
async def new_project(
        request: Request,
        project_body: NewProject,
        folder_id: str = Query(None, alias="folder-id"),
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        project = await configuration.flux_client.create_project(body=project_body.dict(), headers=ctx.headers())
        return await create_asset(
            kind="flux-project",
            raw_id=project["projectId"],
            raw_response=project,
            folder_id=folder_id,
            metadata=AssetMeta(name=project_body.name),
            context=ctx,
            configuration=configuration
        )


@router.post("/projects/upload", summary="upload projects")
async def upload(
        request: Request,
        project_id: str = Query(None, alias="project-id"),
        folder_id: str = Query(None, alias="folder-id"),
        name: str = Query(None, alias="name"),
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        form = await request.form()
        form = {
            'file': await form.get('file').read(),
            'content_encoding': form.get('content_encoding', 'identity')
        }
        await assert_write_permissions_folder_id(folder_id=folder_id, context=ctx)
        project = await configuration.flux_client.upload_project(data=form, project_id=project_id,
                                                                 headers=ctx.headers())
        return await create_asset(
            kind="flux-project",
            raw_id=project["projectId"],
            raw_response=project,
            folder_id=folder_id,
            metadata=AssetMeta(name=name),
            context=ctx,
            configuration=configuration
        )


@router.get(
    "/projects/{project_id}/download-zip",
    summary="download a project as zip file")
async def download_zip(
        request: Request,
        project_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=project_id, configuration=configuration, context=ctx)
        content = await configuration.flux_client.download_zip(project_id=project_id, headers=ctx.headers())
        return Response(content=content, headers={'content-type': 'application/zip'})


@router.delete("/projects/{project_id}", summary="delete a project")
async def delete_project(
        request: Request,
        project_id: str,
        purge: bool = False,
        configuration: Configuration = Depends(get_configuration)):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=project_id, configuration=configuration, context=ctx)
        response = await configuration.flux_client.delete_project(project_id=project_id, headers=ctx.headers())
        if purge:
            await delete_asset(raw_id=project_id, configuration=configuration, context=ctx)

        return response


@router.get("/projects/{project_id}",
            response_model=Project,
            summary="retrieve a project")
async def get_project(
        request: Request,
        project_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=project_id, configuration=configuration, context=ctx)
        return await configuration.flux_client.get_project(
            project_id=project_id,
            headers=ctx.headers()
        )


@router.post("/projects/{project_id}", summary="post a project")
async def post_project(
        request: Request,
        project_id: str,
        project: Project,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=project_id, configuration=configuration, context=ctx)
        return await configuration.flux_client.update_project(
            project_id=project_id,
            body=project.dict(),
            headers=ctx.headers()
        )


@router.post("/projects/{project_id}/metadata", summary="edit metadata of a project")
async def post_metadata(
        request: Request,
        project_id: str,
        metadata_body: EditMetadata,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_write_permissions_from_raw_id(raw_id=project_id, configuration=configuration, context=ctx)
        return await configuration.flux_client.update_metadata(
            project_id=project_id,
            body=metadata_body.dict(),
            headers=ctx.headers()
        )


@router.get("/projects/{project_id}/metadata",
            response_model=ProjectSnippet,
            summary="retrieve the metadata of a project")
async def get_metadata(
        request: Request,
        project_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:
        await assert_read_permissions_from_raw_id(raw_id=project_id, configuration=configuration, context=ctx)
        return await configuration.flux_client.get_metadata(
            project_id=project_id,
            headers=ctx.headers()
        )