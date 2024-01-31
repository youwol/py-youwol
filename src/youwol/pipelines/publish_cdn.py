# standard library
import asyncio
import glob
import itertools
import json

from collections.abc import Iterable, Mapping
from pathlib import Path

# typing
from typing import Optional, cast

# third parties
from fastapi import HTTPException
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import (
    CloudEnvironment,
    LocalClients,
    PathsBook,
    RemoteClients,
    YouwolEnvironment,
    get_standard_youwol_env,
)
from youwol.app.routers.environment.upload_assets.package import UploadPackageOptions
from youwol.app.routers.environment.upload_assets.upload import upload_asset
from youwol.app.routers.local_cdn import download_package
from youwol.app.routers.projects.models_project import (
    BrowserApp,
    ExplicitNone,
    FlowId,
    Manifest,
    PipelineStep,
    PipelineStepStatus,
    Project,
)

# Youwol utilities
from youwol.utils import encode_id, files_check_sum, to_json
from youwol.utils.context import Context
from youwol.utils.http_clients.tree_db_backend import DefaultDriveResponse
from youwol.utils.utils_paths import create_zip_file


async def create_cdn_zip(
    zip_path: Path,
    project: Project,
    flow_id: str,
    files: Iterable[Path],
    context: Context,
):
    async with context.start(action="create_cdn_zip") as ctx:
        env = await context.get("env", YouwolEnvironment)
        paths: PathsBook = env.pathsBook
        artifacts_flow_path = paths.artifacts_flow(
            project_name=project.name, flow_id=flow_id
        )

        def arc_name(path: Path):
            """
            CDN files can be:
            *  related to an artifacts, under `artifacts_flow_path`
            *  related to a project file, under `project.path`
            """
            try:
                return path.relative_to(artifacts_flow_path).parts[2:]
            except ValueError:
                return path.relative_to(project.path).parts

        zip_files = [(f, "/".join(arc_name(f))) for f in files]
        await ctx.info(
            text="create CDN zip: files recovered",
            data={"files": [f"{name} -> {str(path)}" for path, name in zip_files]},
        )

        yw_metadata = to_json(project.pipeline.target)
        await ctx.info(text="Append target metadata", data=yw_metadata)
        create_zip_file(
            path=zip_path,
            files_to_zip=zip_files,
            with_data=[(".yw_metadata.json", json.dumps(yw_metadata))],
        )


async def publish_browser_app_metadata(
    package: str,
    version: str,
    target: BrowserApp,
    env: YouwolEnvironment,
    context: Context,
):
    async with context.start(action="publish_browser_app_metadata") as ctx:
        client = LocalClients.get_cdn_sessions_storage_client(env=env)
        settings = await client.get(
            package="@youwol/platform-essentials", key="settings", headers=ctx.headers()
        )
        if "browserApplications" not in settings:
            settings["browserApplications"] = []
        settings["browserApplications"] = [
            s for s in settings["browserApplications"] if s["package"] != package
        ]
        settings["browserApplications"].append(
            {"package": package, "version": version, **to_json(target)}
        )
        await ctx.info(
            text="user settings of @youwol/platform-essentials", data=settings
        )
        await client.post(
            package="@youwol/platform-essentials",
            key="settings",
            body=settings,
            headers=ctx.headers(),
        )


async def get_default_drive(context: Context) -> DefaultDriveResponse:
    env: YouwolEnvironment = await context.get("env", YouwolEnvironment)

    if env.cache_py_youwol.get("default-drive"):
        return env.cache_py_youwol.get("default-drive")

    default_drive = (
        await LocalClients.get_assets_gateway_client(env)
        .get_treedb_backend_router()
        .get_default_user_drive(headers=context.headers())
    )

    env.cache_py_youwol["default-drive"] = DefaultDriveResponse(**default_drive)
    return DefaultDriveResponse(**default_drive)


class PublishCdnLocalStep(PipelineStep):
    """
    Publishes a list of artifacts and eventually additional assets in the local ecosystem.
    """

    id: str = "cdn-local"
    """
    ID of the step.

    Warning:
        Flows usually reference this ID, in common scenarios it should not be modified.
    """

    packagedArtifacts: list[str]
    """
    A list of artifact's IDs to include in the package.
    """
    packagedFolders: list[str] = []
    """
    A list of folder's paths to include in the package (in addition to the artifacts).
    """

    run: ExplicitNone = ExplicitNone()

    async def packaged_files(self, project: Project, flow_id: str, context: Context):
        flatten = itertools.chain.from_iterable
        files_artifacts = await asyncio.gather(
            *[
                project.get_artifact_files(
                    flow_id=flow_id, artifact_id=artifact_id, context=context
                )
                for artifact_id in self.packagedArtifacts
            ]
        )
        files_folders = [
            Path(p)
            for folder in self.packagedFolders
            for p in glob.glob(f"{project.path / folder}/*.*")
        ]
        return list(flatten(files_artifacts)) + files_folders

    async def get_sources(
        self, project: Project, flow_id: FlowId, context: Context
    ) -> Iterable[Path]:
        return await self.packaged_files(
            project=project, flow_id=flow_id, context=context
        )

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        """
        Retrieves the status of the step:
        *  if the step has never been run, it is `PipelineStepStatus.none`.
        *  if the package has never been published in the local ecosystem, it is `PipelineStepStatus.none`.
        *  if the fingerprint computed from the project & the one corresponding to the published package are
        equal, it is `PipelineStepStatus.OK`.
        *  otherwise it is `PipelineStepStatus.outdated`.

        Parameters:
            project: Project for which the step is executed.
            flow_id: ID of the flow associated.
            last_manifest: manifest from the last execution.
            context: Current context.

        Return:
            Manifest of the execution
        """
        async with context.start(action="PublishCdnLocalStep.get_status") as ctx:
            env = await context.get("env", YouwolEnvironment)
            local_cdn = LocalClients.get_cdn_client(env=env)
            if not last_manifest:
                await ctx.info(
                    text="No manifest found, the step has not yet been triggered"
                )
                return PipelineStepStatus.none

            try:
                local_lib_info = await local_cdn.get_library_info(
                    library_id=encode_id(project.publishName),
                    headers=ctx.headers(),
                )
            except HTTPException as e:
                await ctx.info(
                    text="The package has not been published yet in the local cdn"
                )
                if e.status_code == 404:
                    return PipelineStepStatus.none
                raise e

            if project.version not in local_lib_info["versions"]:
                return PipelineStepStatus.none

            local_version_info = await local_cdn.get_version_info(
                library_id=encode_id(project.publishName),
                version=project.version,
                headers=ctx.headers(),
            )
            files = await self.packaged_files(project, flow_id, context)
            src_files_fingerprint = files_check_sum(files)
            if (
                last_manifest.fingerprint == local_version_info["fingerprint"]
                and last_manifest.cmdOutputs["srcFilesFingerprint"]
                == src_files_fingerprint
            ):
                return PipelineStepStatus.OK

            if last_manifest.fingerprint != local_version_info["fingerprint"]:
                await context.info(
                    text="Mismatch between cdn-backend fingerprint and saved manifest's fingerprint",
                    data={
                        "cdn-backend fingerprint": local_version_info["fingerprint"],
                        "saved manifest's fingerprint": last_manifest.fingerprint,
                    },
                )
                return PipelineStepStatus.outdated

            if last_manifest.cmdOutputs["srcFilesFingerprint"] != src_files_fingerprint:
                await context.info(
                    text="Mismatch between actual src files fingerprint and saved manifest's srcFilesFingerprint",
                    data={
                        "actual src files fingerprint": src_files_fingerprint,
                        "saved manifest's srcFilesFingerprint": last_manifest.cmdOutputs[
                            "srcFilesFingerprint"
                        ],
                    },
                )

            return PipelineStepStatus.outdated

    async def execute_run(self, project: Project, flow_id: str, context: Context):
        """
        Trigger step execution.

        Parameters:
            project: Project for which the step is executed.
            flow_id: ID of the flow associated.
            context: Current context.

        Return:
            Manifest of the execution
        """
        async with context.start(action="PublishCdnLocalStep.execute_run") as ctx:
            env: YouwolEnvironment = await ctx.get("env", YouwolEnvironment)

            await ctx.info(text="create 'cdn.zip' in project")
            files = await self.packaged_files(project, flow_id, ctx)
            zip_path = project.path / "cdn.zip"
            await create_cdn_zip(
                zip_path=zip_path,
                project=project,
                flow_id=flow_id,
                files=files,
                context=ctx,
            )

            local_treedb = LocalClients.get_treedb_client(env=env)
            local_cdn = LocalClients.get_gtw_cdn_client(env=env)
            local_asset = LocalClients.get_gtw_assets_client(env=env)
            package_id = encode_id(project.publishName)
            asset_id = encode_id(package_id)

            folder_id = await self._retrieve_publish_folder_id(
                asset_id=asset_id, project_name=project.name, context=ctx
            )
            # If the folder_id is coming from the remote env & the user do not belong to it, the next publish will fail.
            resp = await local_cdn.publish(
                zip_content=zip_path.read_bytes(),
                params={"folder-id": folder_id},
                headers=ctx.headers(),
                timeout=60000,
            )
            await ctx.info(text="Asset posted in assets_gtw", data=resp)

            target = project.pipeline.target
            if isinstance(target, BrowserApp):
                await publish_browser_app_metadata(
                    package=project.publishName,
                    version=project.version,
                    target=target,
                    env=env,
                    context=ctx,
                )

            [resp, asset, access, explorer_item] = await asyncio.gather(
                local_cdn.get_version_info(
                    library_id=package_id,
                    version=project.version,
                    headers=ctx.headers(),
                ),
                local_asset.get_asset(asset_id=asset_id, headers=ctx.headers()),
                local_asset.get_access_info(asset_id=asset_id, headers=ctx.headers()),
                local_treedb.get_item(item_id=asset_id, headers=ctx.headers()),
            )
            await ctx.info(text="Package retrieved from local cdn", data=resp)
            resp["srcFilesFingerprint"] = files_check_sum(files)
            base_path = env.pathsBook.artifacts_flow(
                project_name=project.name, flow_id=flow_id
            )
            resp["srcBasePath"] = str(base_path)
            resp["srcFiles"] = [str(f) for f in files]
            resp["asset"] = asset
            resp["access"] = access
            resp["explorerItem"] = explorer_item
            return resp

    @staticmethod
    async def _retrieve_publish_folder_id(
        project_name: str, asset_id: str, context: Context
    ):
        """
        Retrieve the parent folder id to publish the package, it eventually creates the asset.
        Rules are as follows:
        *  if a parent folder for the asset can be found locally, it is used
        *  if not and the asset exists in the twin remote environment, the asset is downloaded in local and the parent
         folder is retrieved
        *  if none of the above, the `download` folder of the user's private drive is used.

        :param project_name: name of the project
        :param asset_id: corresponding asset_id
        :param context: context
        :return:
        """
        async with context.start(
            action="PublishCdnLocalStep._retrieve_publish_folder_id"
        ) as ctx:
            env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
            local_treedb = LocalClients.get_treedb_client(env=env)
            try:
                item = await local_treedb.get_item(
                    item_id=asset_id,
                    headers=ctx.headers(),
                )
                folder_id = item["folderId"]
                await ctx.info(
                    "Found item in explorer, proceed by publishing packages",
                    {"folderId": folder_id},
                )
            except HTTPException as e:
                if e.status_code == 404:
                    succeeded = await PublishCdnLocalStep._try_download_package(
                        package_name=project_name, context=ctx
                    )
                    if not succeeded:
                        await ctx.info(
                            "The package can not be downloaded from remote environment => "
                            "publish package in 'download' folder of default drive"
                        )
                        drive: DefaultDriveResponse = await get_default_drive(
                            context=ctx
                        )
                        folder_id = drive.downloadFolderId
                    else:
                        await ctx.info(
                            "The package has been found in remote environment, location & metadata downloaded"
                        )
                        item = await local_treedb.get_item(
                            item_id=asset_id, headers=ctx.headers()
                        )
                        folder_id = item["folderId"]
                else:
                    raise e
            return folder_id

    @staticmethod
    async def _try_download_package(package_name, context: Context) -> bool:
        async with context.start(
            action="PublishCdnLocalStep._try_download_package"
        ) as ctx:
            await ctx.info(
                "The package has not been published yet, start creation. Attempt to download latest version "
                "from remote environment..."
            )
            # At first publication in local env, attempt to download the asset to get it with consistent
            # locations & metadata as defined in the remote environment
            try:
                await download_package(
                    package_name=package_name,
                    version="latest",
                    check_update_status=False,
                    context=ctx,
                )
            except HTTPException as e:
                if e.status_code == 404:
                    return False
                raise

            return True


class CdnTarget(BaseModel):
    """
    Specifies a remote CDN target to publish.
    """

    cloudTarget: CloudEnvironment
    """
    The cloud target.
    """

    name: str
    """
    Name of the target (display name).
    """

    authId: str
    """
    Authentication ID to use (should be available in the cloud target).
    """


async def create_sub_pipelines_publish_cdn(
    start_step: str, targets: list[CdnTarget], context: Context
):
    steps = [
        PublishCdnRemoteStep(id=f"cdn_{cdn_target.name}", cdnTarget=cdn_target)
        for cdn_target in targets
    ]
    dags = [f"{start_step} > cdn_{cdn_target.name}" for cdn_target in targets]
    await context.info(
        text="Cdn pipelines created",
        data={"targets:": targets, "steps": steps, "dags": dags},
    )
    return steps, dags


class PublishCdnRemoteStep(PipelineStep):
    """
    Publishes a package published in the local ecosystem into a remote ecosystem.
    """

    id: str = "cdn-remote"
    """
    ID of the step.

    Warning:
        Flows usually reference this ID, in common scenarios it should not be modified.
    """
    cdnTarget: CdnTarget
    """
    The specification of the remote ecosystem to publish the package into.
    """
    run: ExplicitNone = ExplicitNone()

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        """
        Retrieves the status of the step:
        *  if the local and remote published package's fingerprint are equal, it is `PipelineStepStatus.OK`.
        *  otherwise it is `PipelineStepStatus.outdated`.

        Parameters:
            project: Project for which the step is executed.
            flow_id: ID of the flow associated.
            last_manifest: manifest from the last execution.
            context: Current context.

        Return:
            Manifest of the execution
        """
        async with context.start(action="PublishCdnRemoteStep.get_status") as ctx:
            env = await context.get("env", YouwolEnvironment)
            local_cdn = LocalClients.get_cdn_client(env=env)
            remote_gtw = await RemoteClients.get_assets_gateway_client(
                cloud_environment=self.cdnTarget.cloudTarget,
                auth_id=self.cdnTarget.authId,
                tokens_storage=env.tokens_storage,
            )
            remote_cdn = remote_gtw.get_cdn_backend_router()
            library_id = encode_id(project.publishName)
            headers = ctx.headers()

            local_info, remote_info = await asyncio.gather(
                local_cdn.get_version_info(
                    library_id=library_id,
                    version=project.version,
                    headers=headers,
                ),
                remote_cdn.get_version_info(
                    library_id=library_id, version=project.version, headers=headers
                ),
                return_exceptions=True,
            )
            if (
                isinstance(remote_info, HTTPException)
                and remote_info.status_code == 404
            ):
                await ctx.info(text="Package not found in remote CDN => status is none")
                return PipelineStepStatus.none

            if isinstance(local_info, HTTPException) and local_info.status_code == 404:
                await ctx.info(
                    text="Package not found in local CDN => status is outdated"
                )
                return PipelineStepStatus.outdated

            if isinstance(remote_info, Exception):
                await ctx.error(text=f"Error retrieving remote info: {remote_info}")
                return PipelineStepStatus.KO

            if isinstance(local_info, Exception):
                await ctx.error(text=f"Error retrieving local info {local_info}")
                return PipelineStepStatus.KO

            local_info = cast(Mapping, local_info)
            remote_info = cast(Mapping, remote_info)
            local_fp, remote_fp = local_info["fingerprint"], remote_info["fingerprint"]
            if local_fp == remote_fp:
                await ctx.info(
                    text="Local CDN fingerprint match remote CDN fingerprint => status is OK"
                )
                return PipelineStepStatus.OK

            await ctx.info(
                text="Local CDN fingerprint does not match remote CDN fingerprint => status is outdated"
            )
            return PipelineStepStatus.outdated

    async def execute_run(self, project: Project, flow_id: str, context: Context):
        """
        Trigger step execution.

        Parameters:
            project: Project for which the step is executed.
            flow_id: ID of the flow associated.
            context: Current context.

        Return:
            Manifest of the execution
        """
        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)

        async with context.start(
            action="PublishCdnRemoteStep.execute_run",
        ) as ctx:
            options = UploadPackageOptions(versions=[project.version])
            package_id = encode_id(project.publishName)
            remote_assets_gtw = await RemoteClients.get_assets_gateway_client(
                cloud_environment=self.cdnTarget.cloudTarget,
                auth_id=self.cdnTarget.authId,
                tokens_storage=env.tokens_storage,
            )
            await upload_asset(
                remote_assets_gtw=remote_assets_gtw,
                asset_id=encode_id(package_id),
                options=options,
                context=ctx,
            )
            # # No ideal solution to get back the fingerprint here:
            # # (i) this one is brittle if the source code of the CDN is not the same between local vs remote
            local_cdn = LocalClients.get_cdn_client(env=env)
            resp = await local_cdn.get_version_info(
                library_id=encode_id(project.publishName),
                version=project.version,
                headers=ctx.headers(),
            )
            # # (ii) this one is brittle in terms of eventual consistency
            # # resp = await remote_gtw.cdn_get_package(library_name=project.name, version=project.version,
            # # metadata=True)
            return resp


class Environment(BaseModel):
    cdnTargets: list[CdnTarget] = [
        CdnTarget(
            name="youwol",
            cloudTarget=get_standard_youwol_env(env_id="youwol.com"),
            authId="browser",
        ),
    ]
