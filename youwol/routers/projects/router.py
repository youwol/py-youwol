import asyncio
import itertools
from datetime import datetime
from typing import Optional, Tuple, List

from fastapi import APIRouter, Depends

from starlette.requests import Request

from configuration import Project, PipelineStep, Flow
from context import Context, CommandException
from models import Label
from routers.projects.implementation import (
    run, get_fingerprint, create_artifacts, artifacts_path,
    get_status, Manifest, artifact_path,
    )
from utils_low_level import to_json
from utils_paths import write_json
from youwol.web_socket import WebSocketsCache

from routers.projects.models import (
    PipelineStepStatusResponse, PipelineStatusResponse, ArtifactsResponse,
    ArtifactResponse,
    )
from youwol.configuration.youwol_configuration import YouwolConfiguration
from youwol.configuration.youwol_configuration import yw_config

router = APIRouter()
flatten = itertools.chain.from_iterable


async def get_project_step(
        project_id: str,
        step_id: str,
        context: Context
        ) -> Tuple[Project, PipelineStep]:
    project = next(p for p in context.config.projects if p.id == project_id)
    step = next(s for s in project.pipeline.steps if s.id == step_id)

    await context.info(text="project & step retrieved",
                       data={'project': to_json(project), 'step': to_json(step)})
    return project, step


async def get_project_flow_steps(
        project_id: str,
        flow_id: str,
        context: Context
        ) -> Tuple[Project, Flow, List[PipelineStep]]:

    project = next(p for p in context.config.projects if p.id == project_id)
    flow = next(f for f in project.pipeline.flows if f.name == flow_id)
    involved_steps = set([step.strip() for b in flow.dag for step in b.split('>')])
    steps = [step for step in project.pipeline.steps if step.id in involved_steps]

    await context.info(text="project & flow & steps retrieved",
                       data={'project': to_json(project), 'flow': to_json(flow),
                             'steps': [s for s in involved_steps]})
    return project, flow, steps


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


@router.get("/{project_id}/flows/{flow_id}",
            response_model=PipelineStatusResponse,
            summary="status")
async def project_status(
        request: Request,
        project_id: str,
        flow_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(request=request, config=config, web_socket=WebSocketsCache.userChannel)
    response: Optional[PipelineStatusResponse] = None
    async with context.start(
            action="Get project status",
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

        project, flow, steps = await get_project_flow_steps(project_id=project_id, flow_id=flow_id, context=ctx)
        eventual_artifacts = [(a, artifact_path(project=project, flow_id=flow_id, step=s, artifact=a, context=ctx))
                              for s in steps for a in s.artifacts]
        actual_artifacts = [ArtifactResponse(id=a.id, path=path) for a, path in eventual_artifacts
                            if path.exists() and path.is_dir()]
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

    async with context.start(
            action="Run pipeline-step",
            labels=[Label.INFO],
            with_attributes={
                'event': 'PipelineStatusPending',
                'projectId': project_id,
                'flowId': flow_id,
                'stepId': step_id
                },
            on_exit=lambda _ctx: pipeline_step_status(request=request, project_id=project_id, flow_id=flow_id,
                                                      step_id=step_id, config=config)
            ) as ctx:
        project, step = await get_project_step(project_id, step_id, ctx)
        error_run = None
        try:
            outputs = await run(project=project, step=step, context=ctx)
            succeeded = True
        except CommandException as e:
            outputs = e.outputs
            error_run = e
            succeeded = False

        fingerprint, files = await get_fingerprint(project=project, step=step, context=ctx)
        (context.config.pathsBook.system / project.name / flow_id / step.id).mkdir(parents=True, exist_ok=True)
        path = artifacts_path(project=project, flow_id=flow_id, step=step, context=context)
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
