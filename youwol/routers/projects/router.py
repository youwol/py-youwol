import asyncio
import collections.abc
import itertools
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from starlette.requests import Request

from configuration import Project
from configuration.paths import PathsBook
from context import Context, CommandException
from models import Label
from routers.projects.implementation import (
    run, create_artifacts,
    get_status, Manifest, get_project_step, get_project_flow_steps, format_artifact_response,
    )

from utils_paths import write_json
from youwol.web_socket import WebSocketsCache

from routers.projects.models import (
    PipelineStepStatusResponse, PipelineStatusResponse, ArtifactsResponse, ProjectStatusResponse,
    )
from youwol.configuration.youwol_configuration import YouwolConfiguration
from youwol.configuration.youwol_configuration import yw_config

router = APIRouter()
flatten = itertools.chain.from_iterable


@router.get("/{project_id}/flows/{flow_id}/steps/{step_id}",
            response_model=PipelineStepStatusResponse,
            summary="status")
async def pipeline_step_status(
        request: Request,
        project_id: str,
        flow_id: str,
        step_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ) -> PipelineStepStatusResponse:
    context = Context(request=request, config=config, web_socket=WebSocketsCache.userChannel)
    response: Optional[PipelineStepStatusResponse] = None
    async with context.start(
            action="Get pipeline status",
            labels=[Label.INFO],
            succeeded_data=lambda _ctx: ('PipelineStepStatusResponse', response),
            with_attributes={
                'event': 'PipelineStatusPending',
                'projectId': project_id,
                'flowId': flow_id,
                'stepId': step_id
                }
            ) as ctx:

        project, step = await get_project_step(project_id=project_id, step_id=step_id, context=ctx)
        response = await get_status(project=project, flow_id=flow_id, step=step, context=ctx)
        return response


@router.get("/{project_id}",
            response_model=ProjectStatusResponse,
            summary="status")
async def project_status(
        request: Request,
        project_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(request=request, config=config, web_socket=WebSocketsCache.userChannel)
    response: Optional[ProjectStatusResponse] = None
    async with context.start(
            action="Get project status",
            labels=[Label.INFO],
            succeeded_data=lambda _ctx: ('ProjectStatusResponse', response),
            with_attributes={
                'projectId': project_id
                }
            ) as ctx:
        project: Project = next(p for p in context.config.projects if p.id == project_id)
        dependencies = await project.get_ordered_dependencies(ctx)
        response = ProjectStatusResponse(
            projectId=project_id,
            projectName=project.name,
            orderedDependencies=[d.name for d in dependencies]
            )
        return response


@router.get("/{project_id}/flows/{flow_id}",
            response_model=PipelineStatusResponse,
            summary="status")
async def flow_status(
        request: Request,
        project_id: str,
        flow_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(request=request, config=config, web_socket=WebSocketsCache.userChannel)
    response: Optional[PipelineStatusResponse] = None
    async with context.start(
            action=f"Get flow '{flow_id}' status",
            labels=[Label.INFO],
            succeeded_data=lambda _ctx: ('PipelineStatusResponse', response),
            with_attributes={
                'projectId': project_id,
                'flowId': flow_id
                }
            ) as ctx:

        project, flow, steps = await get_project_flow_steps(project_id=project_id, flow_id=flow_id, context=ctx)
        steps_status = await asyncio.gather(*[
            pipeline_step_status(request=request, project_id=project_id, flow_id=flow_id,
                                 step_id=step.id, config=config)
            for step in steps
            ])
        response = PipelineStatusResponse(projectId=project_id, steps=[s for s in steps_status])
        return response


@router.get("/{project_id}/flows/{flow_id}/artifacts",
            response_model=ArtifactsResponse,
            summary="status")
async def project_artifacts(
        request: Request,
        project_id: str,
        flow_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(request=request, config=config, web_socket=WebSocketsCache.userChannel)
    response: Optional[ArtifactsResponse] = None
    async with context.start(
            action="Get project's artifact",
            labels=[Label.INFO],
            succeeded_data=lambda _ctx: ('ArtifactsResponse', response),
            with_attributes={
                'projectId': project_id,
                'flowId': flow_id
                }
            ) as ctx:

        paths: PathsBook = ctx.config.pathsBook

        project, flow, steps = await get_project_flow_steps(project_id=project_id, flow_id=flow_id, context=ctx)
        eventual_artifacts = [(a, s, paths.artifact(project_name=project.name, flow_id=flow_id, step_id=s.id,
                                                    artifact_id=a.id))
                              for s in steps for a in s.artifacts]

        actual_artifacts = [format_artifact_response(project=project, flow_id=flow_id, step=s, artifact=a,
                                                     context=ctx)
                            for a, s, path in eventual_artifacts if path.exists() and path.is_dir()]

        response = ArtifactsResponse(artifacts=actual_artifacts)
        return response


@router.post("/{project_id}/flows/{flow_id}/steps/{step_id}/run",
             summary="status")
async def run_pipeline_step(
        request: Request,
        project_id: str,
        flow_id: str,
        step_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(request=request, config=config, web_socket=WebSocketsCache.userChannel)

    def refresh_status_downstream_steps():
        """
        Downstream steps may depend on this guy => request status on them.
        Shortcut => request status on all the steps of the flow (not only subsequent)
        """
        _project: Project = next(p for p in context.config.projects if p.id == project_id)
        steps = _project.get_flow_steps(flow_id=flow_id)
        return asyncio.gather(*[
            pipeline_step_status(request=request, project_id=project_id, flow_id=flow_id, step_id=_step.id,
                                 config=config)
            for _step in steps
            ])

    async with context.start(
            action="Run pipeline-step",
            labels=[Label.INFO],
            with_attributes={
                'event': 'PipelineStatusPending',
                'projectId': project_id,
                'flowId': flow_id,
                'stepId': step_id
                },
            on_exit=lambda _ctx: refresh_status_downstream_steps()
            ) as ctx:
        project, step = await get_project_step(project_id, step_id, ctx)
        error_run = None
        try:
            outputs = await run(project=project, flow_id=flow_id, step=step, context=ctx)
            succeeded = True
        except CommandException as e:
            outputs = e.outputs
            error_run = e
            succeeded = False

        paths: PathsBook = ctx.config.pathsBook
        if isinstance(outputs, collections.abc.Mapping) and 'fingerprint' in outputs:
            await ctx.info(text="'sources' attribute not provided => expect fingerprint from run's output",
                           data={'run-output': outputs})
            fingerprint = outputs['fingerprint']
            files = []
        else:
            await ctx.info(text="'sources' attribute provided => fingerprint computed from it")
            fingerprint, files = await step.get_fingerprint(project=project, flow_id=flow_id, context=ctx)

        (context.config.pathsBook.system / project.name / flow_id / step.id).mkdir(parents=True, exist_ok=True)
        path = paths.artifacts_step(project_name=project.name, flow_id=flow_id, step_id=step.id)
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
