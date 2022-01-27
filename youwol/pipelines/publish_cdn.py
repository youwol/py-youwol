import asyncio
import itertools
from pathlib import Path
from typing import Optional, cast, Mapping, List, Iterable

from fastapi import HTTPException

from youwol.backends.assets_gateway.models import DefaultDriveResponse
from youwol.environment.clients import LocalClients, RemoteClients
from youwol.environment.models_project import (
    PipelineStep, Project, Manifest, PipelineStepStatus, FlowId, ExplicitNone,
)
from youwol.environment.paths import PathsBook
from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.routers.environment.upload_assets.upload import upload_asset
from youwol_utils import encode_id, files_check_sum
from youwol_utils.context import Context
from youwol_utils.utils_paths import create_zip_file


async def create_cdn_zip(
        zip_path: Path,
        project: Project,
        flow_id: str,
        files: Iterable[Path],
        context: Context
        ):
    env = await context.get('env', YouwolEnvironment)
    paths: PathsBook = env.pathsBook
    artifacts_flow_path = paths.artifacts_flow(project_name=project.name, flow_id=flow_id)
    zip_files = [(f, '/'.join(f.relative_to(artifacts_flow_path).parts[2:])) for f in files]
    await context.info(text="create CDN zip: files recovered",
                       data={'files': [f"{name} -> {str(path)}" for path, name in zip_files]})
    create_zip_file(path=zip_path, files_to_zip=zip_files)


class PublishCdnLocalStep(PipelineStep):

    id = 'publish-local'

    packagedArtifacts: List[str]

    run: ExplicitNone = ExplicitNone()

    async def packaged_files(self, project: Project, flow_id: str, context: Context):

        files = await asyncio.gather(*[
            project.get_artifact_files(flow_id=flow_id, artifact_id=artifact_id, context=context)
            for artifact_id in self.packagedArtifacts
            ])
        return list(itertools.chain.from_iterable(files))

    async def get_sources(self, project: Project, flow_id: FlowId, context: Context) -> Iterable[Path]:

        return await self.packaged_files(project=project, flow_id=flow_id, context=context)

    async def get_status(self, project: Project, flow_id: str, last_manifest: Optional[Manifest], context: Context) \
            -> PipelineStepStatus:

        async with context.start(
                action="PublishCdnLocalStep.get_status"
        ) as ctx:
            env = await context.get('env', YouwolEnvironment)
            local_cdn = LocalClients.get_cdn_client(env=env)
            if not last_manifest:
                await ctx.info(text="No manifest found, the step has not yet been triggered")
                return PipelineStepStatus.none

            try:
                local_info = await local_cdn.get_package(
                    library_name=project.name,
                    version=project.version,
                    metadata=True,
                    headers=ctx.headers()
                )
            except HTTPException as e:
                await ctx.info(text="The package has not been published yet in the local cdn")
                if e.status_code == 404:
                    return PipelineStepStatus.none
                raise e
            files = await self.packaged_files(project, flow_id, context)
            src_files_fingerprint = files_check_sum(files)
            if last_manifest.fingerprint == local_info['fingerprint'] and \
                    last_manifest.cmdOutputs['src_files_fingerprint'] == src_files_fingerprint:
                return PipelineStepStatus.OK

            if last_manifest.fingerprint != local_info['fingerprint']:
                await context.info(
                    text="Mismatch between cdn-backend fingerprint and saved manifest's fingerprint",
                    data={
                        'cdn-backend fingerprint': local_info['fingerprint'],
                        "saved manifest's fingerprint": last_manifest.fingerprint
                    }
                )
            if last_manifest.cmdOutputs['src_files_fingerprint'] != src_files_fingerprint:
                await context.info(
                    text="Mismatch between actual src files fingerprint and saved manifest's src_files_fingerprint",
                    data={
                        'actual src files fingerprint': src_files_fingerprint,
                        "saved manifest's src_files_fingerprint": last_manifest.cmdOutputs['src_files_fingerprint']
                    }
                )

            return PipelineStepStatus.outdated

    async def execute_run(self, project: Project, flow_id: str, context: Context):

        async with context.start(
                action="PublishCdnLocalStep.execute_run"
        ) as ctx:

            env = await ctx.get('env', YouwolEnvironment)

            await ctx.info(text="create 'cdn.zip' in project")
            files = await self.packaged_files(project, flow_id, ctx)
            zip_path = project.path / 'cdn.zip'
            await create_cdn_zip(zip_path=zip_path, project=project, flow_id=flow_id, files=files, context=ctx)

            local_gtw = LocalClients.get_assets_gateway_client(env=env)
            local_treedb = LocalClients.get_treedb_client(env=env)
            asset_id = encode_id(project.id)
            try:
                item = await local_treedb.get_item(item_id=asset_id, headers=ctx.headers())
                folder_id = item['folderId']
            except HTTPException as e:
                if e.status_code == 404:
                    await ctx.info("The package has not been published yet, start creation")
                    drive: DefaultDriveResponse = await env.get_default_drive(context=ctx)
                    folder_id = drive.downloadFolderId
                else:
                    raise e

            data = {'file': zip_path.read_bytes(), 'content_encoding': 'identity'}
            resp = await local_gtw.put_asset_with_raw(kind='package', folder_id=folder_id, data=data,
                                                      headers=ctx.headers(), timeout=600)
            await ctx.info(text="Asset posted in assets_gtw", data=resp)
            local_cdn = LocalClients.get_cdn_client(env=env)
            resp = await local_cdn.get_package(library_name=project.name, version=project.version, metadata=True,
                                               headers=ctx.headers())
            await ctx.info(text="Package retrieved from local cdn", data=resp)
            resp['src_files_fingerprint'] = files_check_sum(files)
            base_path = env.pathsBook.artifacts_flow(project_name=project.name, flow_id=flow_id)
            resp['src_base_path'] = str(base_path)
            resp['src_files'] = [str(f.relative_to(base_path)) for f in files]
            return resp


class PublishCdnRemoteStep(PipelineStep):

    id = 'publish-remote'

    run: ExplicitNone = ExplicitNone()

    async def get_status(self, project: Project, flow_id: str, last_manifest: Optional[Manifest], context: Context) \
            -> PipelineStepStatus:

        async with context.start(
                action="PublishCdnRemoteStep.get_status"
        ) as ctx:
            if last_manifest and not last_manifest.succeeded:
                return PipelineStepStatus.KO

            env = await context.get('env', YouwolEnvironment)
            local_cdn = LocalClients.get_cdn_client(env=env)
            remote_gtw = await RemoteClients.get_assets_gateway_client(context=context)

            local_info, remote_info = await asyncio.gather(
                local_cdn.get_package(library_name=project.name, version=project.version, metadata=True,
                                      headers=ctx.headers()),
                remote_gtw.cdn_get_package(library_name=project.name, version=project.version, metadata=True,
                                           headers=ctx.headers()),
                return_exceptions=True
            )
            if isinstance(remote_info, HTTPException) and remote_info.status_code == 404:
                await ctx.info(text="Package not found in remote CDN => status is none")
                return PipelineStepStatus.none

            if isinstance(local_info, HTTPException) and local_info.status_code == 404:
                await ctx.info(text="Package not found in local CDN => status is outdated")
                return PipelineStepStatus.outdated

            if isinstance(remote_info, Exception) or isinstance(local_info, Exception):
                raise remote_info if isinstance(remote_info, Exception) else local_info

            local_info = cast(Mapping, local_info)
            remote_info = cast(Mapping, remote_info)
            local_fp, remote_fp = local_info['fingerprint'], remote_info['fingerprint']
            if local_fp == remote_fp:
                await ctx.info(text="Local CDN fingerprint match remote CDN fingerprint => status is OK")
                return PipelineStepStatus.OK

            await ctx.info(text="Local CDN fingerprint does not match remote CDN fingerprint => status is outdated")
            return PipelineStepStatus.outdated

    async def execute_run(self, project: Project, flow_id: str, context: Context):

        async with context.start(
                action="PublishCdnRemoteStep.execute_run"
        ) as ctx:
            env = await context.get('env', YouwolEnvironment)
            await upload_asset(body={'assetId': encode_id(project.id)}, context=ctx)
            # # No ideal solution to get back the fingerprint here:
            # # (i) this one is brittle if the source code of the CDN is not the same between local vs remote
            local_cdn = LocalClients.get_cdn_client(env=env)
            resp = await local_cdn.get_package(library_name=project.name, version=project.version, metadata=True,
                                               headers=ctx.headers())
            # # (ii) this one is brittle in terms of eventual consistency
            # # resp = await remote_gtw.cdn_get_package(library_name=project.name, version=project.version,
            # # metadata=True)
            return resp
