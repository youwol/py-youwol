# standard library
import asyncio
import collections.abc
import itertools
import os
import shutil

from datetime import datetime

# typing
from typing import Any, Mapping

# third parties
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

# Youwol application
from youwol.app.environment import PathsBook, YouwolEnvironment, yw_config
from youwol.app.routers.commons import Label
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils import CommandException, decode_id
from youwol.utils.context import Context
from youwol.utils.utils_paths import parse_json, write_json

# relative
from .dependencies import resolve_project_dependencies
from .implementation import (
    create_artifacts,
    format_artifact_response,
    get_project_configuration,
    get_project_flow_steps,
    get_project_step,
    get_status,
)
from .models import (
    ArtifactsResponse,
    CdnResponse,
    CdnVersionResponse,
    CreateProjectFromTemplateBody,
    Event,
    PipelineStatusResponse,
    PipelineStepEvent,
    PipelineStepStatusResponse,
    ProjectStatusResponse,
    UpdateConfigurationResponse,
)
from .models_project import (
    CreateProjectFromTemplateResponse,
    Manifest,
    PipelineStepStatus,
    Project,
)
from .projects_loader import ProjectLoader, ProjectsLoadingResults

router = APIRouter()
flatten = itertools.chain.from_iterable


@router.get("/status", response_model=ProjectsLoadingResults, summary="status")
async def status(request: Request):
    async with Context.start_ep(
        request=request, with_reporters=[LogsStreamer()]
    ) as ctx:  # type: Context
        response = ProjectsLoadingResults(results=await ProjectLoader.refresh(ctx))
        await ctx.send(response)
        return response


@router.get(
    "/{project_id}/flows/{flow_id}/steps/{step_id}",
    response_model=PipelineStepStatusResponse,
    summary="status",
)
async def pipeline_step_status(
    request: Request, project_id: str, flow_id: str, step_id: str
) -> PipelineStepStatusResponse:
    async with Context.start_ep(
        request=request,
        action="pipeline_step_status",
        with_labels=[str(Label.PIPELINE_STEP_STATUS_PENDING)],
        with_attributes={"projectId": project_id, "flowId": flow_id, "stepId": step_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        project, step = await get_project_step(
            project_id=project_id, step_id=step_id, context=ctx
        )
        response = await get_status(
            project=project, flow_id=flow_id, step=step, context=ctx
        )
        return response


@router.get("/{project_id}", response_model=ProjectStatusResponse, summary="status")
async def project_status(
    request: Request, project_id: str, config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.start_ep(
        request=request,
        action="project_status",
        with_attributes={"projectId": project_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        projects = await ProjectLoader.get_cached_projects()
        project: Project = next(p for p in projects if p.id == project_id)

        workspace_dependencies = await resolve_project_dependencies(
            project=project, context=ctx
        )
        await ctx.info("Project dependencies retrieved", data=workspace_dependencies)
        response = ProjectStatusResponse(
            projectId=project_id,
            projectName=project.name,
            workspaceDependencies=workspace_dependencies,
        )
        await cdn_status(request=request, project_id=project_id, config=config)
        await ctx.send(response)
        return response


@router.get(
    "/{project_id}/flows/{flow_id}",
    response_model=PipelineStatusResponse,
    summary="status",
)
async def flow_status(request: Request, project_id: str, flow_id: str):
    async with Context.start_ep(
        request=request,
        action="flow_status",
        with_attributes={"projectId": project_id, "flowId": flow_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        project, flow, steps = await get_project_flow_steps(
            project_id=project_id, flow_id=flow_id, context=ctx
        )
        await ctx.info(
            text="project, flow & steps retried",
            data={"project": project, "flow": flow, "steps": steps},
        )
        steps_status = await asyncio.gather(
            *[
                get_status(project=project, flow_id=flow_id, step=step, context=ctx)
                for step in steps
            ]
        )
        response = PipelineStatusResponse(
            projectId=project_id, steps=list(steps_status)
        )
        await ctx.send(response)
        return response


@router.get(
    "/{project_id}/flows/{flow_id}/artifacts",
    response_model=ArtifactsResponse,
    summary="status",
)
async def project_artifacts(request: Request, project_id: str, flow_id: str):
    async with Context.start_ep(
        request=request,
        action="project_artifacts",
        with_attributes={"projectId": project_id, "flowId": flow_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        paths: PathsBook = env.pathsBook

        project, _, steps = await get_project_flow_steps(
            project_id=project_id, flow_id=flow_id, context=ctx
        )
        eventual_artifacts = [
            (
                a,
                s,
                paths.artifact(
                    project_name=project.name,
                    flow_id=flow_id,
                    step_id=s.id,
                    artifact_id=a.id,
                ),
            )
            for s in steps
            for a in s.artifacts
        ]

        actual_artifacts = [
            format_artifact_response(
                project=project, flow_id=flow_id, step=s, artifact=a, env=env
            )
            for a, s, path in eventual_artifacts
            if path.exists() and path.is_dir()
        ]

        response = ArtifactsResponse(artifacts=actual_artifacts)
        await ctx.send(response)
        return response


async def run_upstream_steps(
    request: Request, project: Project, flow_id: str, step_id: str, context: Context
):
    async with context.start(action="run_upstream_steps") as ctx:
        parent_steps = project.get_direct_upstream_steps(flow_id, step_id)
        parent_steps_ids_to_run = [
            statusStep.stepId
            for statusStep in [
                await get_status(project, flow_id, parent_step, context=ctx)
                for parent_step in parent_steps
            ]
            if statusStep.status != PipelineStepStatus.OK
        ]
        for parent_step_id in parent_steps_ids_to_run:
            await run_pipeline_step(
                request=request,
                project_id=project.id,
                flow_id=flow_id,
                step_id=parent_step_id,
                run_upstream=True,
            )
        # Do we need to check for KOs in previous run and raise exception ?


@router.get(
    "/{project_id}/flows/{flow_id}/steps/{step_id}/configuration", summary="status"
)
async def get_configuration(
    request: Request, project_id: str, flow_id: str, step_id: str
):
    async with Context.from_request(request).start(action="get_configuration") as ctx:
        return JSONResponse(
            content=await get_project_configuration(
                project_id=project_id, flow_id=flow_id, step_id=step_id, context=ctx
            )
        )


@router.post(
    "/{project_id}/flows/{flow_id}/steps/{step_id}/configuration",
    response_model=UpdateConfigurationResponse,
    summary="status",
)
async def update_configuration(
    request: Request,
    project_id: str,
    flow_id: str,
    step_id: str,
    body: Mapping[str, Any],
    env: YouwolEnvironment = Depends(yw_config),
):
    async with Context.from_request(request).start(
        action="update_configuration"
    ) as ctx:
        project, _ = await get_project_step(project_id, step_id, ctx)
        base_path = env.pathsBook.artifacts_flow(
            project_name=project.name, flow_id=flow_id
        )
        path = base_path / "configurations.json"
        content = parse_json(path=path) if path.exists() else {}
        content[step_id] = body
        write_json(data=content, path=path)
        return UpdateConfigurationResponse(path=path, configuration=body)


async def run_pipeline_step_implementation(
    request: Request,
    project_id: str,
    flow_id: str,
    step_id: str,
    run_upstream: bool = Query(alias="run-upstream", default=False),
):
    async def on_enter(ctx_enter):
        env_enter = await ctx_enter.get("env", YouwolEnvironment)
        if "runningProjectSteps" not in env_enter.cache_py_youwol:
            env_enter.cache_py_youwol["runningProjectSteps"] = set()
        env_enter.cache_py_youwol["runningProjectSteps"].add(
            f"{project_id}#{flow_id}#{step_id}"
        )
        await ctx_enter.send(
            PipelineStepEvent(
                projectId=project_id,
                flowId=flow_id,
                stepId=step_id,
                event=Event.runStarted,
            )
        )

    async def on_exit(ctx_exit):
        env_exit = await ctx_exit.get("env", YouwolEnvironment)
        if (
            f"{project_id}#{flow_id}#{step_id}"
            in env_exit.cache_py_youwol["runningProjectSteps"]
        ):
            env_exit.cache_py_youwol["runningProjectSteps"].remove(
                f"{project_id}#{flow_id}#{step_id}"
            )
        async with ctx_exit.start(action="refresh_status_downstream_steps") as ctx_1:
            await ctx_1.send(
                PipelineStepEvent(
                    projectId=project_id,
                    flowId=flow_id,
                    stepId=step_id,
                    event=Event.runDone,
                )
            )

            _project: Project = next(p for p in projects if p.id == project_id)

            steps = _project.get_downstream_flow_steps(
                flow_id=flow_id, from_step_id=step_id, from_step_included=True
            )
            return asyncio.gather(
                *[
                    get_status(
                        project=_project, flow_id=flow_id, step=_step, context=ctx_1
                    )
                    for _step in steps
                    if f"{project_id}#{flow_id}#{_step.id}"
                    not in env.cache_py_youwol["runningProjectSteps"]
                ]
            )

    async with Context.start_ep(
        request=request,
        action="Run pipeline-step",
        with_labels=[str(Label.RUN_PIPELINE_STEP), str(Label.PIPELINE_STEP_RUNNING)],
        with_attributes={"projectId": project_id, "flowId": flow_id, "stepId": step_id},
        on_enter=on_enter,
        on_exit=on_exit,
        with_reporters=[LogsStreamer()],
    ) as ctx:
        env = await ctx.get("env", YouwolEnvironment)
        projects = await ProjectLoader.get_cached_projects()
        paths: PathsBook = env.pathsBook

        project, step = await get_project_step(project_id, step_id, ctx)
        error_run = None
        try:
            if run_upstream:
                await run_upstream_steps(
                    request=request,
                    project=project,
                    flow_id=flow_id,
                    step_id=step_id,
                    context=ctx,
                )

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

        if isinstance(outputs, collections.abc.Mapping) and "fingerprint" in outputs:
            await ctx.info(
                text="'sources' attribute not provided => expect fingerprint from run's output",
                data={"run-output": outputs},
            )
            fingerprint = outputs["fingerprint"]
            files = []
        else:
            await ctx.info(
                text="'sources' attribute provided => fingerprint computed from it"
            )
            fingerprint, files = await step.get_fingerprint(
                project=project, flow_id=flow_id, context=ctx
            )

        path = paths.artifacts_step(
            project_name=project.name, flow_id=flow_id, step_id=step.id
        )
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=False)

        manifest = Manifest(
            succeeded=succeeded if succeeded else False,
            fingerprint=fingerprint,
            creationDate=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            cmdOutputs=outputs,
            files=[str(f) for f in files],
        )

        write_json(manifest.dict(), path / "manifest.json")
        await ctx.info(text="Manifest updated", data=manifest)

        if not succeeded:
            raise error_run

        await create_artifacts(
            project=project,
            flow_id=flow_id,
            step=step,
            fingerprint=fingerprint,
            context=ctx,
        )


@router.post(
    "/{project_id}/flows/{flow_id}/steps/{step_id}/run",
    summary="run a step of a pipeline",
)
async def run_pipeline_step(
    request: Request,
    project_id: str,
    flow_id: str,
    step_id: str,
    run_upstream: bool = Query(alias="run-upstream", default=False),
):
    asyncio.ensure_future(
        run_pipeline_step_implementation(
            request=request,
            project_id=project_id,
            flow_id=flow_id,
            step_id=step_id,
            run_upstream=run_upstream,
        )
    )
    return Response(status_code=202)


@router.get("/{project_id}/cdn", response_model=CdnResponse, summary="status")
async def cdn_status(
    request: Request, project_id: str, config: YouwolEnvironment = Depends(yw_config)
):
    async with Context.from_request(request).start(
        action="Get local cdn status",
        with_attributes={"event": "CdnResponsePending", "projectId": project_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        data = config.backends_configuration.cdn_backend.doc_db.data["documents"]
        data = [d for d in data if d["library_name"] == decode_id(project_id)]

        def format_version(doc):
            storage_cdn_path = config.pathsBook.local_cdn_storage
            folder_path = storage_cdn_path / doc["path"]
            bundle_path = folder_path / doc["bundle"]
            files_count = sum(len(files) for r, d, files in os.walk(folder_path))
            bundle_size = bundle_path.stat().st_size
            return CdnVersionResponse(
                name=doc["library_name"],
                version=doc["version"],
                versionNumber=doc["version_number"],
                filesCount=files_count,
                bundleSize=bundle_size,
                path=folder_path,
                namespace=doc["namespace"],
            )

        response = CdnResponse(
            name=decode_id(project_id), versions=[format_version(d) for d in data]
        )
        await ctx.send(response)
        return response


@router.put(
    "/create-from-template",
    response_model=CreateProjectFromTemplateResponse,
    summary="status",
)
async def new_project_from_template(
    request: Request,
    body: CreateProjectFromTemplateBody,
    config: YouwolEnvironment = Depends(yw_config),
):
    async with Context.from_request(request).start(
        action="new_project_from_template",
        with_attributes={"templateType": body.type},
        with_labels=[f"{Label.PROJECT_CREATING}"],
        with_reporters=[LogsStreamer()],
    ) as ctx:
        template = next(
            (
                template
                for template in config.projects.templates
                if template.type == body.type
            ),
            None,
        )
        if not template:
            raise RuntimeError(f"Can not find a template of type {body.type}")

        await ctx.info(text="Found template generator", data=template)
        name, _ = await template.generator(template.folder, body.parameters, ctx)

        response = ProjectsLoadingResults(results=await ProjectLoader.refresh(ctx))
        await ctx.send(response)

        projects = await ProjectLoader.get_cached_projects()
        project = next((p for p in projects if p.name == name), None)
        return project


@router.get(
    "/{project_id}/flows/{flow_id}/steps/{step_id}/view",
    summary="view of a pipeline step",
)
async def pipeline_step_view(
    request: Request,
    project_id: str,
    step_id: str,
):
    async with Context.from_request(request).start(
        action="new_project_from_template"
    ) as ctx:
        _, step = await get_project_step(project_id, step_id, ctx)
        if not step.view:
            raise HTTPException(
                status_code=404, detail="The step has no view definition associated"
            )
        if step.view:
            return FileResponse(
                path=step.view,
                media_type="text/javascript",
                filename=step.view.name,
                headers={"cache-control": "no-cache"},
            )


@router.get(
    "/{project_id}/flows/{flow_id}/steps/{step_id}/commands/{command_id}",
    summary="view of a pipeline step",
)
async def do_cmd_get_pipeline_step(
    request: Request,
    project_id: str,
    flow_id: str,
    step_id: str,
    command_id: str,
):
    async with Context.from_request(request).start(
        action="do_cmd_get_pipeline_step"
    ) as ctx:
        project, step = await get_project_step(project_id, step_id, ctx)
        command = next((c for c in step.http_commands if c.name == command_id), None)

        if not command:
            raise HTTPException(
                status_code=404, detail=f"The step has no command '{command_id}'"
            )

        return await command.do_get(project, flow_id, ctx)
