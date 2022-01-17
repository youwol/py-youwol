import asyncio
import collections.abc
import itertools
import os
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends
from starlette.requests import Request

from youwol.environment.models_project import Project, Manifest
from youwol.environment.paths import PathsBook
from youwol.environment.projects_loader import ProjectLoader
from youwol.environment.youwol_environment import yw_config, YouwolEnvironment
from youwol.exceptions import CommandException
from youwol.routers.commons import Label
from youwol.routers.projects.dependencies import resolve_project_dependencies
from youwol.routers.projects.implementation import (
    create_artifacts, get_status, get_project_step, get_project_flow_steps, format_artifact_response
)
from youwol.routers.projects.models import (
    PipelineStepStatusResponse, PipelineStatusResponse, ArtifactsResponse, ProjectStatusResponse, CdnResponse,
    CdnVersionResponse, )
from youwol.web_socket import WebSocketsStore
from youwol_utils import decode_id
from youwol_utils.context import ContextFactory
from youwol_utils.utils_paths import parse_json
from youwol_utils.utils_paths import write_json

router = APIRouter()
flatten = itertools.chain.from_iterable


@router.get("/{project_id}/flows/{flow_id}/steps/{step_id}",
            response_model=PipelineStepStatusResponse,
            summary="status")
async def pipeline_step_status(
        request: Request,
        project_id: str,
        flow_id: str,
        step_id: str
        ) -> PipelineStepStatusResponse:

    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )

    async with context.start(
            action="Get pipeline status",
            with_labels=[str(Label.PIPELINE_STEP_STATUS_PENDING)],
            with_attributes={
                'projectId': project_id,
                'flowId': flow_id,
                'stepId': step_id
                }
            ) as ctx:

        project, step = await get_project_step(project_id=project_id, step_id=step_id, context=ctx)
        response = await get_status(project=project, flow_id=flow_id, step=step, context=ctx)
        await ctx.send(response)
        return response


@router.get("/{project_id}",
            response_model=ProjectStatusResponse,
            summary="status")
async def project_status(
        request: Request,
        project_id: str,
        config: YouwolEnvironment = Depends(yw_config)
        ):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )

    async with context.start(
            action="Get project status",
            with_attributes={
                'projectId': project_id
                }
            ) as ctx:
        projects = await ProjectLoader.get_projects(await context.get("env", YouwolEnvironment), context)
        project: Project = next(p for p in projects if p.id == project_id)

        workspace_dependencies = await resolve_project_dependencies(project=project, context=context)
        await ctx.info("Project dependencies retrieved", data=workspace_dependencies)
        response = ProjectStatusResponse(
            projectId=project_id,
            projectName=project.name,
            workspaceDependencies=workspace_dependencies
            )
        await cdn_status(request=request, project_id=project_id, config=config)
        await ctx.send(response)
        return response


@router.get("/{project_id}/flows/{flow_id}",
            response_model=PipelineStatusResponse,
            summary="status")
async def flow_status(
        request: Request,
        project_id: str,
        flow_id: str
        ):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )
    async with context.start(
            action=f"Get flow '{flow_id}' status",
            with_attributes={
                'projectId': project_id,
                'flowId': flow_id
                }
            ) as ctx:

        project, flow, steps = await get_project_flow_steps(project_id=project_id, flow_id=flow_id, context=ctx)
        steps_status = await asyncio.gather(*[
            pipeline_step_status(request=request, project_id=project_id, flow_id=flow_id, step_id=step.id)
            for step in steps
            ])
        response = PipelineStatusResponse(projectId=project_id, steps=[s for s in steps_status])
        await ctx.send(response)
        return response


@router.get("/{project_id}/flows/{flow_id}/artifacts",
            response_model=ArtifactsResponse,
            summary="status")
async def project_artifacts(
        request: Request,
        project_id: str,
        flow_id: str
        ):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )

    env = await context.get('env', YouwolEnvironment)
    async with context.start(
            action="Get project's artifact",
            with_attributes={
                'projectId': project_id,
                'flowId': flow_id
                }
            ) as ctx:

        paths: PathsBook = env.pathsBook

        project, flow, steps = await get_project_flow_steps(project_id=project_id, flow_id=flow_id, context=ctx)
        eventual_artifacts = [(a, s, paths.artifact(project_name=project.name, flow_id=flow_id, step_id=s.id,
                                                    artifact_id=a.id))
                              for s in steps for a in s.artifacts]

        actual_artifacts = [format_artifact_response(project=project, flow_id=flow_id, step=s, artifact=a,
                                                     env=env)
                            for a, s, path in eventual_artifacts if path.exists() and path.is_dir()]

        response = ArtifactsResponse(artifacts=actual_artifacts)
        await ctx.send(response)
        return response


@router.post("/{project_id}/flows/{flow_id}/steps/{step_id}/run",
             summary="status")
async def run_pipeline_step(
        request: Request,
        project_id: str,
        flow_id: str,
        step_id: str
        ):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )

    env = await context.get('env', YouwolEnvironment)
    projects = await ProjectLoader.get_projects(env, context)
    paths: PathsBook = env.pathsBook

    def refresh_status_downstream_steps():
        """
        Downstream steps may depend on this guy => request status on them.
        Shortcut => request status on all the steps of the flow (not only subsequent)
        """
        _project: Project = next(p for p in projects if p.id == project_id)
        steps = _project.get_flow_steps(flow_id=flow_id)
        return asyncio.gather(*[
            pipeline_step_status(request=request, project_id=project_id, flow_id=flow_id, step_id=_step.id)
            for _step in steps
            ])

    async with context.start(
            action="Run pipeline-step",
            with_labels=[str(Label.RUN_PIPELINE_STEP), str(Label.PIPELINE_STEP_RUNNING)],
            with_attributes={
                'projectId': project_id,
                'flowId': flow_id,
                'stepId': step_id
                },
            on_exit=lambda _ctx: refresh_status_downstream_steps()
            ) as ctx:
        project, step = await get_project_step(project_id, step_id, ctx)
        error_run = None
        try:
            outputs = await step.execute_run(project, flow_id, ctx)
            outputs = outputs or []
            succeeded = True
        except CommandException as e:
            outputs = e.outputs
            error_run = e
            succeeded = False
        except Exception as e:
            error_run = e
            outputs = [str(e)]
            succeeded = False

        if isinstance(outputs, collections.abc.Mapping) and 'fingerprint' in outputs:
            await ctx.info(text="'sources' attribute not provided => expect fingerprint from run's output",
                           data={'run-output': outputs})
            fingerprint = outputs['fingerprint']
            files = []
        else:
            await ctx.info(text="'sources' attribute provided => fingerprint computed from it")
            fingerprint, files = await step.get_fingerprint(project=project, flow_id=flow_id, context=ctx)

        path = paths.artifacts_step(project_name=project.name, flow_id=flow_id, step_id=step.id)
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=False)

        manifest = Manifest(succeeded=succeeded if succeeded is not None else False,
                            fingerprint=fingerprint,
                            creationDate=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            cmdOutputs=outputs,
                            files=[str(f) for f in files])

        write_json(manifest.dict(), path / "manifest.json")
        await ctx.info(text="Manifest updated", data=manifest)

        if not succeeded:
            raise error_run

        await create_artifacts(project=project, flow_id=flow_id, step=step, fingerprint=fingerprint, context=ctx)


@router.get("/{project_id}/cdn",
            response_model=CdnResponse,
            summary="status")
async def cdn_status(
        request: Request,
        project_id: str,
        config: YouwolEnvironment = Depends(yw_config)
        ):
    context = ContextFactory.get_instance(
        request=request,
        web_socket=WebSocketsStore.userChannel
    )

    async with context.start(
            action="Get local cdn status",
            with_attributes={'event': 'CdnResponsePending', 'projectId': project_id}
            ) as ctx:

        data = parse_json(config.pathsBook.local_cdn_docdb)['documents']
        data = [d for d in data if d["library_name"] == decode_id(project_id)]

        def format_version(doc):
            storage_cdn_path = config.pathsBook.local_cdn_storage
            folder_path = storage_cdn_path / doc['path']
            bundle_path = folder_path / doc['bundle']
            files_count = sum([len(files) for r, d, files in os.walk(folder_path)])
            bundle_size = bundle_path.stat().st_size
            return CdnVersionResponse(
                name=doc['library_name'],
                version=doc['version'],
                versionNumber=doc['version_number'],
                filesCount=files_count,
                bundleSize=bundle_size,
                path=folder_path,
                namespace=doc['namespace']
                )

        response = CdnResponse(
            name=decode_id(project_id),
            versions=[format_version(d) for d in data]
            )
        await ctx.send(response)
        return response
