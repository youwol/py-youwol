import itertools
from datetime import datetime
from typing import Optional, Tuple

from fastapi import APIRouter, Depends

from starlette.requests import Request

from configuration import Project, PipelineStep
from context import Context, ActionException
from models import Label
from routers.projects.implementation import (
    run, get_fingerprint, create_artifacts, artifacts_path, artifact_path,
    get_status, Manifest,
    )
from utils_low_level import to_json
from utils_paths import write_json
from youwol.web_socket import WebSocketsCache

from routers.projects.models import PipelineStepStatusResponse
from youwol.configuration.youwol_configuration import YouwolConfiguration
from youwol.configuration.youwol_configuration import yw_config

router = APIRouter()
flatten = itertools.chain.from_iterable


async def get_project_step(project_id: str, step_id: str, ctx: Context) -> Tuple[Project, PipelineStep]:
    project = next(p for p in ctx.config.projects if p.id == project_id)
    step = next(s for s in project.pipeline.steps if s.id == step_id)

    await ctx.info(text="project & step retrieved",
                   data={'project': to_json(project), 'step': to_json(step)})
    return project, step


@router.get("/{project_id}/steps/{step_id}",
            response_model=PipelineStepStatusResponse,
            summary="status")
async def pipeline_step_status(
        request: Request,
        project_id: str,
        step_id: str,
        config: YouwolConfiguration = Depends(yw_config)
        ):
    context = Context(request=request, config=config, web_socket=WebSocketsCache.userChannel)
    response: Optional[PipelineStepStatusResponse] = None
    async with context.start(
            action="Get pipeline-status",
            labels=[Label.INFO],
            succeeded_data=lambda _ctx: ('PipelineStepStatusResponse', response),
            with_attributes={
                'event': 'PipelineStatusPending',
                'projectId': project_id,
                'stepId': step_id
                }
            ) as ctx:

        project, step = await get_project_step(project_id, step_id, ctx)

        step_status = await get_status(project=project, step=step, context=ctx)
        response = PipelineStepStatusResponse(
            projectId=project.id,
            stepId=step_id,
            artifacts={artifact.id: artifact_path(project=project, step=step, artifact=artifact, context=ctx)
                       for artifact in step.artifacts},
            status=step_status
            )


@router.post("/{project_id}/steps/{step_id}/run",
             summary="status")
async def run_pipeline_step(
        request: Request,
        project_id: str,
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
                'stepId': step_id
                },
            on_exit=lambda _ctx: pipeline_step_status(request=request, project_id=project_id, step_id=step_id,
                                                      config=config)
            ) as ctx:
        project, step = await get_project_step(project_id, step_id, ctx)

        try:
            succeeded = await run(project=project, step=step, context=ctx)
        except ActionException:
            pass

        fingerprint, files = await get_fingerprint(project=project, step=step, context=ctx)
        (context.config.pathsBook.system / project.name / step.id).mkdir(parents=True, exist_ok=True)
        path = artifacts_path(project=project, step=step, context=context)
        manifest = Manifest(succeeded=succeeded if succeeded is not None else False,
                            fingerprint=fingerprint,
                            creationDate=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            files=[str(f) for f in files])
        
        write_json(manifest.dict(), path / "manifest.json")
        await ctx.info(text="Manifest updated", data=manifest)

        if not succeeded:
            raise ActionException(action=f"${project.name}#{step.id}", message="Failed running script")

        await create_artifacts(project=project, step=step, fingerprint=fingerprint, context=ctx)
