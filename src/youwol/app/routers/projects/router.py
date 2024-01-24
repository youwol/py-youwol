# standard library
import asyncio
import collections.abc
import itertools
import os
import shutil

from collections.abc import Mapping
from datetime import datetime

# typing
from typing import Any

# third parties
from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

# Youwol application
from youwol.app.environment import PathsBook, YouwolEnvironment, yw_config
from youwol.app.routers.commons import Label
from youwol.app.web_socket import LogsStreamer

# Youwol utilities
from youwol.utils import JSON, CommandException, decode_id
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
async def status(request: Request) -> ProjectsLoadingResults:
    """
    Parameters:
        request: Incoming request

    Return:
        The description of the projects list in the workspace, it is also send via the `data` webSocket.
    """
    async with Context.start_ep(
        request=request, with_reporters=[LogsStreamer()]
    ) as ctx:
        response = await ProjectLoader.refresh(ctx)
        await ctx.send(response)
        return response


@router.get(
    "/{project_id}/flows/{flow_id}/steps/{step_id}",
    response_model=PipelineStepStatusResponse,
    summary="Check the status of a step, it is also send via the `/ws-data` webSocket.",
)
async def pipeline_step_status(
    request: Request, project_id: str, flow_id: str, step_id: str
) -> PipelineStepStatusResponse:
    """
    Check the status of a step, it is also send via the `/ws-data` webSocket.

    Parameters:
        request: incoming request
        project_id: id of the project
        flow_id: id of the flow
        step_id: id of the step

    Return:
        The status of target step.
    """

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


@router.get(
    "/{project_id}",
    response_model=ProjectStatusResponse,
    summary="Check the status of a project, it is also send via the `/ws-data` webSocket.",
)
async def project_status(
    request: Request, project_id: str, config: YouwolEnvironment = Depends(yw_config)
) -> ProjectStatusResponse:
    """
    Check the status of a project, it is also send via the `/ws-data` webSocket.

    Parameters:
        request: incoming request
        project_id: id of the project
        config: the current environment

    Return:
        The status of the target project.
    """
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
    summary="Check the status of a flow, it is also send via the `/ws-data` webSocket.",
)
async def flow_status(
    request: Request, project_id: str, flow_id: str
) -> PipelineStatusResponse:
    """
    Check the status of a flow, it is also send via the `/ws-data` webSocket.
    The steps included in the response are the steps included in the requested `flow_id`.

    Parameters:
        request: incoming request
        project_id: id of the project
        flow_id: id of the flow

    Return:
        The status of the target flow.
    """

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
    summary="Retrieve the list of a project's artifacts for a given flow",
)
async def project_artifacts(
    request: Request, project_id: str, flow_id: str
) -> ArtifactsResponse:
    """
    Retrieve the list of a project's artifacts for a given flow.

    Parameters:
        request: incoming request
        project_id: id of the project
        flow_id: id of the flow

    Return:
        The list artifacts.
    """

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
    "/{project_id}/flows/{flow_id}/steps/{step_id}/configuration",
    summary="Retrieve the configuration of a step.",
)
async def get_configuration(
    request: Request, project_id: str, flow_id: str, step_id: str
) -> JSONResponse:
    """
    Retrieve the configuration of a step.

    Parameters:
        request: incoming request
        project_id: id of the project
        flow_id: id of the flow
        step_id: id of the step

    Return:
        The configuration of a step
    """
    async with Context.from_request(request).start(action="get_configuration") as ctx:
        return JSONResponse(
            content=await get_project_configuration(
                project_id=project_id, flow_id=flow_id, step_id=step_id, context=ctx
            )
        )


@router.post(
    "/{project_id}/flows/{flow_id}/steps/{step_id}/configuration",
    response_model=UpdateConfigurationResponse,
    summary="update configuration",
)
async def update_configuration(
    request: Request,
    project_id: str,
    flow_id: str,
    step_id: str,
    body: Mapping[str, Any],
    env: YouwolEnvironment = Depends(yw_config),
) -> UpdateConfigurationResponse:
    """
    Update the configuration of a step.

    Parameters:
        request: incoming request
        project_id: id of the project
        flow_id: id of the flow
        step_id: id of the step
        body: configuration's definition
        env: current environment

    Return:
        Update response
    """
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
    run_upstream: bool,
    context: Context,
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

    async with context.start(
        action="run_pipeline_step_implementation",
        with_labels=[str(Label.RUN_PIPELINE_STEP), str(Label.PIPELINE_STEP_RUNNING)],
        on_enter=on_enter,
        on_exit=on_exit,
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
) -> Response:
    """
    Run a step of a pipeline asynchronously. Result of the run will be sent in a future data message using the
    `data` WebSocket with a [PipelineStepEvent](@yw-nav-class:youwol.app.routers.projects.models.PipelineStepEvent).

    Parameters:
        request: incoming request
        project_id: id of the project
        flow_id: id of the flow
        step_id: id of the step
        run_upstream: whether to run upstream steps

    Return:
        Response(status_code=202) : acknowledged
    """
    async with Context.start_ep(
        request=request,
        action="run_pipeline_step",
        with_attributes={"projectId": project_id, "flowId": flow_id, "stepId": step_id},
        with_reporters=[LogsStreamer()],
    ) as ctx:
        task = run_pipeline_step_implementation(
            request=request,
            project_id=project_id,
            flow_id=flow_id,
            step_id=step_id,
            run_upstream=run_upstream,
            context=ctx,
        )
        future = asyncio.ensure_future(task)
        await ctx.future("Async run step scheduled", future=future)
        return Response(status_code=202)


@router.get(
    "/{project_id}/cdn",
    response_model=CdnResponse,
    summary="Retrieve the status of a particular project published within the CDN database.",
)
async def cdn_status(
    request: Request, project_id: str, config: YouwolEnvironment = Depends(yw_config)
) -> CdnResponse:
    """
    Retrieve the status of a particular project published within the CDN database.

    Parameters:
        request: incoming request
        project_id: id of the project
        config: current environment

    Return:
        The status response.
    """

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
    summary="Create a new project from a specified template.",
)
async def new_project_from_template(
    request: Request,
    body: CreateProjectFromTemplateBody,
    config: YouwolEnvironment = Depends(yw_config),
) -> CreateProjectFromTemplateResponse:
    """
    Create a new project from a specified template.

    Parameters:
        request: incoming request
        body: generator reference
        config: current environment

    Return:
        Information on the created project
    """

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

        response = await ProjectLoader.refresh(ctx)
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
) -> FileResponse:
    """
    Return the view of a pipeline step.

    It is a javascript file that return a function generating a view, it has the following signature:

    ```typescript
    async function getView(body:{
      triggerRun: () => void,
      // to be called by the view when the configuration is validated
      project: Project,
      flowId: str,
      //  the flowId
      stepId: str,
      //  the stepId
      projectsRouter,
      webpmClient,
       // the packages manager client, used to install dependencies to create the view if needed,
    }) : HTMLElement {

        // typical implementation

        const {foo, bar} = await webpmClient.install({modules:['foo#^1.2.3', 'bar#^2.3.4']})
        //  use foo and bar to create reactive view
        //  can interact with the custom backends of the step using projectsRouter.executeStepGetCommand$
        //  return the view
        }

    return getView;
    ```

    In practice, the view often interact with commands defined by the step (usually to retrieve data).
    See [do_cmd_get_pipeline_step](@yw-nav-func:youwol.app.routers.projects.router.do_cmd_get_pipeline_step).

    Parameters:
        request (Starlette.Request): incoming request
        project_id: id of the project
        step_id: id of the step

    Return:
        text/javascript FileResponse with returned `getView` function when executed.
    """
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
    summary="Execute a particular GET command defined by step.",
)
async def do_cmd_get_pipeline_step(
    request: Request,
    project_id: str,
    flow_id: str,
    step_id: str,
    command_id: str,
) -> JSON:
    """
    Execute a particular GET command defined by step.

    Parameters:
        request: incoming request
        project_id: id of the project
        flow_id: id of the flow
        step_id: id of the step
        command_id: id of the command

    Return:
        The response from the associated command.
    """

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
