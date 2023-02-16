import asyncio
import itertools
import json
from pathlib import Path
from typing import Optional, cast, Mapping, List, Iterable

from fastapi import HTTPException
from pydantic import BaseModel

from youwol.environment import CloudEnvironment, LocalClients, RemoteClients, PathsBook, YouwolEnvironment
from youwol.middlewares import JwtProviderPyYouwol

from youwol_utils.http_clients.tree_db_backend import DefaultDriveResponse
from youwol.routers.projects.models_project import (
    PipelineStep, Project, Manifest, PipelineStepStatus, FlowId, ExplicitNone, BrowserApp,
)
from youwol.routers.environment.upload_assets.package import UploadPackageOptions
from youwol.routers.environment.upload_assets.upload import upload_asset
from youwol_utils import encode_id, files_check_sum, to_json, YouwolHeaders
from youwol_utils.context import Context
from youwol_utils.utils_paths import create_zip_file


async def create_cdn_zip(
        zip_path: Path,
        project: Project,
        flow_id: str,
        files: Iterable[Path],
        context: Context
        ):
    async with context.start(action="create_cdn_zip") as ctx:  # type: Context
        env = await context.get('env', YouwolEnvironment)
        paths: PathsBook = env.pathsBook
        artifacts_flow_path = paths.artifacts_flow(project_name=project.name, flow_id=flow_id)
        zip_files = [(f, '/'.join(f.relative_to(artifacts_flow_path).parts[2:])) for f in files]
        await ctx.info(text="create CDN zip: files recovered",
                       data={'files': [f"{name} -> {str(path)}" for path, name in zip_files]})

        yw_metadata = to_json(project.pipeline.target)
        await ctx.info(text="Append target metadata", data=yw_metadata)
        create_zip_file(path=zip_path, files_to_zip=zip_files,
                        with_data=[('.yw_metadata.json', json.dumps(yw_metadata))])


async def publish_browser_app_metadata(package: str, version: str, target: BrowserApp, env: YouwolEnvironment,
                                       context: Context):

    async with context.start(action="publish_browser_app_metadata") as ctx:
        client = LocalClients.get_cdn_sessions_storage_client(env=env)
        settings = await client.get(package="@youwol/platform-essentials", key="settings", headers=ctx.headers())
        if 'browserApplications' not in settings:
            settings['browserApplications'] = []
        settings['browserApplications'] = [s for s in settings['browserApplications'] if s['package'] != package]
        settings['browserApplications'].append(
            {
                "package": package,
                "version": version,
                **to_json(target)
            }
        )
        await ctx.info(text="user settings of @youwol/platform-essentials", data=settings)
        await client.post(package="@youwol/platform-essentials", key="settings", body=settings, headers=ctx.headers())


async def get_default_drive(context: Context) -> DefaultDriveResponse:
    env: YouwolEnvironment = await context.get('env', YouwolEnvironment)

    if env.cache_py_youwol.get("default-drive"):
        return env.cache_py_youwol.get("default-drive")

    default_drive = await LocalClients \
        .get_assets_gateway_client(env).get_treedb_backend_router() \
        .get_default_user_drive(headers=context.headers())

    env.cache_py_youwol["default-drive"] = DefaultDriveResponse(**default_drive)
    return DefaultDriveResponse(**default_drive)


class PublishCdnLocalStep(PipelineStep):

    id = 'cdn-local'

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
        ) as ctx:  # type: Context
            env = await context.get('env', YouwolEnvironment)
            local_cdn = LocalClients.get_cdn_client(env=env)
            if not last_manifest:
                await ctx.info(text="No manifest found, the step has not yet been triggered")
                return PipelineStepStatus.none

            try:
                local_lib_info = await local_cdn.get_library_info(
                    library_id=encode_id(project.publishName),
                    headers={**ctx.headers(), YouwolHeaders.muted_http_errors: "404"},
                )
            except HTTPException as e:
                await ctx.info(text="The package has not been published yet in the local cdn")
                if e.status_code == 404:
                    return PipelineStepStatus.none
                raise e

            if project.version not in local_lib_info['versions']:
                return PipelineStepStatus.none

            local_version_info = await local_cdn.get_version_info(
                library_id=encode_id(project.publishName),
                version=project.version,
                headers=ctx.headers()
            )
            files = await self.packaged_files(project, flow_id, context)
            src_files_fingerprint = files_check_sum(files)
            if last_manifest.fingerprint == local_version_info['fingerprint'] and \
                    last_manifest.cmdOutputs['srcFilesFingerprint'] == src_files_fingerprint:
                return PipelineStepStatus.OK

            if last_manifest.fingerprint != local_version_info['fingerprint']:
                await context.info(
                    text="Mismatch between cdn-backend fingerprint and saved manifest's fingerprint",
                    data={
                        'cdn-backend fingerprint': local_version_info['fingerprint'],
                        "saved manifest's fingerprint": last_manifest.fingerprint
                    }
                )
            if last_manifest.cmdOutputs['srcFilesFingerprint'] != src_files_fingerprint:
                await context.info(
                    text="Mismatch between actual src files fingerprint and saved manifest's srcFilesFingerprint",
                    data={
                        'actual src files fingerprint': src_files_fingerprint,
                        "saved manifest's srcFilesFingerprint": last_manifest.cmdOutputs['srcFilesFingerprint']
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

            local_treedb = LocalClients.get_treedb_client(env=env)
            local_cdn = LocalClients.get_gtw_cdn_client(env=env)
            package_id = encode_id(project.publishName)
            asset_id = encode_id(package_id)
            try:
                item = await local_treedb.get_item(
                    item_id=asset_id,
                    headers={**ctx.headers(), YouwolHeaders.muted_http_errors: "404"})
                folder_id = item['folderId']
            except HTTPException as e:
                if e.status_code == 404:
                    await ctx.info("The package has not been published yet, start creation")
                    drive: DefaultDriveResponse = await get_default_drive(context=ctx)
                    folder_id = drive.downloadFolderId
                else:
                    raise e

            resp = await local_cdn.publish(zip_content=zip_path.read_bytes(), params={"folder-id": folder_id},
                                           headers=ctx.headers(), timeout=60000)
            await ctx.info(text="Asset posted in assets_gtw", data=resp)

            target = project.pipeline.target
            if isinstance(target, BrowserApp):
                await publish_browser_app_metadata(package=project.publishName, version=project.version, target=target,
                                                   env=env, context=ctx)

            resp = await local_cdn.get_version_info(library_id=encode_id(project.publishName), version=project.version,
                                                    headers=ctx.headers())
            await ctx.info(text="Package retrieved from local cdn", data=resp)
            resp['srcFilesFingerprint'] = files_check_sum(files)
            base_path = env.pathsBook.artifacts_flow(project_name=project.name, flow_id=flow_id)
            resp['srcBasePath'] = str(base_path)
            resp['srcFiles'] = [str(f.relative_to(base_path)) for f in files]
            return resp


class CdnTarget(BaseModel):

    cloudTarget: CloudEnvironment
    name: str
    authId: str


class PublishCdnRemoteStep(PipelineStep):

    id = 'cdn-remote'
    cdnTarget: CdnTarget
    run: ExplicitNone = ExplicitNone()

    async def get_access_token(self, context: Context):

        try:
            authentication = next(auth for auth in self.cdnTarget.cloudTarget.authentications
                                  if auth.authId == self.cdnTarget.authId)
        except StopIteration as e:
            await context.error(text=f"Can no find auth {self.cdnTarget.authId} in cloud target's authentications",
                                data={"cloud target": self.cdnTarget.cloudTarget})
            raise e

        token = await JwtProviderPyYouwol.get_auth_token(
            auth_provider=self.cdnTarget.cloudTarget.authProvider,
            authentication=authentication,
            context=context
        )

        return f"Bearer {token}"

    async def get_status(self, project: Project, flow_id: str, last_manifest: Optional[Manifest], context: Context) \
            -> PipelineStepStatus:

        access_token = await self.get_access_token(context=context)

        async with context.start(
                action="PublishCdnRemoteStep.get_status",
                with_headers={
                    "Authorization": access_token,
                }
        ) as ctx:

            env = await context.get('env', YouwolEnvironment)
            local_cdn = LocalClients.get_cdn_client(env=env)
            remote_gtw = await RemoteClients.get_assets_gateway_client(remote_host=self.cdnTarget.cloudTarget.host)
            remote_cdn = remote_gtw.get_cdn_backend_router()
            library_id = encode_id(project.publishName)
            headers = {**ctx.headers(), YouwolHeaders.muted_http_errors: "404"}

            local_info, remote_info = await asyncio.gather(
                local_cdn.get_version_info(library_id=library_id, version=project.version, headers=headers),
                remote_cdn.get_version_info(library_id=library_id, version=project.version, headers=headers),
                return_exceptions=True
            )
            if isinstance(remote_info, HTTPException) and remote_info.status_code == 404:
                await ctx.info(text="Package not found in remote CDN => status is none")
                return PipelineStepStatus.none

            if isinstance(local_info, HTTPException) and local_info.status_code == 404:
                await ctx.info(text="Package not found in local CDN => status is outdated")
                return PipelineStepStatus.outdated

            if isinstance(remote_info, Exception):
                await ctx.error(text=f"Error retrieving remote info: {remote_info}")
                return PipelineStepStatus.KO

            if isinstance(local_info, Exception):
                await ctx.error(text=f"Error retrieving local info {local_info}")
                return PipelineStepStatus.KO

            local_info = cast(Mapping, local_info)
            remote_info = cast(Mapping, remote_info)
            local_fp, remote_fp = local_info['fingerprint'], remote_info['fingerprint']
            if local_fp == remote_fp:
                await ctx.info(text="Local CDN fingerprint match remote CDN fingerprint => status is OK")
                return PipelineStepStatus.OK

            await ctx.info(text="Local CDN fingerprint does not match remote CDN fingerprint => status is outdated")
            return PipelineStepStatus.outdated

    async def execute_run(self, project: Project, flow_id: str, context: Context):

        env: YouwolEnvironment = await context.get('env', YouwolEnvironment)

        access_token = await self.get_access_token(context=context)

        async with context.start(
                action="PublishCdnRemoteStep.execute_run",
                with_headers={
                    "Authorization": access_token
                }
        ) as ctx:
            options = UploadPackageOptions(versions=[project.version])
            package_id = encode_id(project.publishName)
            await upload_asset(remote_host=self.cdnTarget.cloudTarget.host, asset_id=encode_id(package_id),
                               options=options, context=ctx)
            # # No ideal solution to get back the fingerprint here:
            # # (i) this one is brittle if the source code of the CDN is not the same between local vs remote
            local_cdn = LocalClients.get_cdn_client(env=env)
            resp = await local_cdn.get_version_info(library_id=encode_id(project.publishName), version=project.version,
                                                    headers=ctx.headers())
            # # (ii) this one is brittle in terms of eventual consistency
            # # resp = await remote_gtw.cdn_get_package(library_name=project.name, version=project.version,
            # # metadata=True)
            return resp
