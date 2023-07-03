# standard library
import os
import shutil

# typing
from typing import List, Tuple

# Youwol application
from youwol.app.environment import PathsBook, YouwolEnvironment

# Youwol utilities
from youwol.utils import (
    PipelineFlowNotFound,
    PipelineStepNotFound,
    ProjectNotFound,
    decode_id,
    to_json,
)
from youwol.utils.context import Context
from youwol.utils.utils_paths import matching_files, parse_json

# relative
from .models import (
    ArtifactResponse,
    Event,
    PipelineStepEvent,
    PipelineStepStatusResponse,
)
from .models_project import (
    Artifact,
    Flow,
    Link,
    LinkKind,
    Manifest,
    PipelineStep,
    PipelineStepStatus,
    Project,
)
from .projects_loader import ProjectLoader


def is_step_running(
    project_id: str, flow_id: str, step_id: str, env: YouwolEnvironment
):
    if (
        "runningProjectSteps" in env.cache_py_youwol
        and f"{project_id}#{flow_id}#{step_id}"
        in env.cache_py_youwol["runningProjectSteps"]
    ):
        return True
    return False


async def get_project_configuration(
    project_id: str, flow_id: str, step_id: str, context: Context
):
    project, _ = await get_project_step(project_id, step_id, context)
    env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
    base_path = env.pathsBook.artifacts_flow(project_name=project.name, flow_id=flow_id)

    path = base_path / "configurations.json"
    if not path.exists():
        return {}
    return parse_json(path=path).get(step_id, {})


async def get_project_step(
    project_id: str, step_id: str, context: Context
) -> Tuple[Project, PipelineStep]:
    projects = await ProjectLoader.get_cached_projects()
    project = next((p for p in projects if p.id == project_id), None)
    if project is None:
        raise ProjectNotFound(
            project=decode_id(project_id),
            context="py-youwol.admin.projects => get_project_step",
        )
    step = next((s for s in project.pipeline.steps if s.id == step_id), None)
    if step is None:
        raise PipelineStepNotFound(
            project=decode_id(project_id),
            step=step_id,
            context="py-youwol.admin.projects => get_project_step",
        )

    await context.info(
        text="project & step retrieved",
        data={"project": to_json(project), "step": to_json(step)},
    )
    return project, step


async def get_project_flow_steps(
    project_id: str, flow_id: str, context: Context
) -> Tuple[Project, Flow, List[PipelineStep]]:
    projects = await ProjectLoader.get_cached_projects()
    project = next((p for p in projects if p.id == project_id), None)

    if project is None:
        raise ProjectNotFound(
            project=decode_id(project_id),
            context="py-youwol.admin.projects => get_project_flow_steps",
        )

    flow = next((f for f in project.pipeline.flows if f.name == flow_id), None)

    if flow is None:
        raise PipelineFlowNotFound(
            project=decode_id(project_id),
            flow=flow_id,
            context="py-youwol.admin.projects => get_project_flow_steps",
        )
    steps = project.get_flow_steps(flow_id=flow_id)

    await context.info(
        text="project & flow & steps retrieved",
        data={
            "project": to_json(project),
            "flow": to_json(flow),
            "steps": [s.id for s in steps],
        },
    )
    return project, flow, steps


def format_artifact_response(
    project: Project,
    flow_id: str,
    step: PipelineStep,
    artifact: Artifact,
    env: YouwolEnvironment,
) -> ArtifactResponse:
    paths: PathsBook = env.pathsBook

    path = paths.artifact(
        project_name=project.name,
        flow_id=flow_id,
        step_id=step.id,
        artifact_id=artifact.id,
    )
    return ArtifactResponse(
        id=artifact.id,
        links=[
            Link(
                name=link.name,
                url=link.url
                if link.kind == LinkKind.plainUrl
                else f"/admin/system/file/{path}/{link.url}",
            )
            for link in artifact.links
        ],
        path=path,
    )


async def get_status(
    project: Project, flow_id: str, step: PipelineStep, context: Context
) -> PipelineStepStatusResponse:
    env = await context.get("env", YouwolEnvironment)
    paths: PathsBook = env.pathsBook
    async with context.start(
        action="implementation.get_status",
        with_attributes={"projectId": project.id, "flowId": flow_id, "stepId": step.id},
        on_enter=lambda ctx_enter: ctx_enter.send(
            PipelineStepEvent(
                projectId=project.id,
                flowId=flow_id,
                stepId=step.id,
                event=Event.statusCheckStarted,
            )
        ),
    ) as ctx:
        path = paths.artifacts_step(
            project_name=project.name, flow_id=flow_id, step_id=step.id
        )
        manifest = (
            Manifest(**parse_json(path / "manifest.json"))
            if (path / "manifest.json").exists()
            else None
        )

        if is_step_running(project.id, flow_id, step.id, env):
            return PipelineStepStatusResponse(
                projectId=project.id,
                flowId=flow_id,
                stepId=step.id,
                manifest=manifest,
                artifactFolder=path,
                artifacts=[],
                status=PipelineStepStatus.running,
            )

        # noinspection PyBroadException
        try:
            status = await step.get_status(
                project=project, flow_id=flow_id, last_manifest=manifest, context=ctx
            )
        except Exception:
            status = PipelineStepStatus.KO
        artifacts = [
            format_artifact_response(
                project=project, flow_id=flow_id, step=step, artifact=artifact, env=env
            )
            for artifact in step.artifacts
        ]
        response = PipelineStepStatusResponse(
            projectId=project.id,
            flowId=flow_id,
            stepId=step.id,
            manifest=manifest,
            artifactFolder=path,
            artifacts=artifacts,
            status=status,
        )
        await ctx.send(response)
        return response


async def create_artifacts(
    project: Project,
    flow_id: str,
    step: PipelineStep,
    fingerprint: str,
    context: Context,
):
    async with context.start(
        action="create artifacts",
        with_attributes={
            "projectId": project.id,
            "flowId": flow_id,
            "stepId": step.id,
            "srcFingerprint": fingerprint or "not-provided",
        },
    ) as ctx:
        for artifact in step.artifacts:
            await create_artifact(
                project=project,
                flow_id=flow_id,
                step=step,
                artifact=artifact,
                fingerprint=fingerprint,
                context=ctx,
            )


async def create_artifact(
    project: Project,
    flow_id: str,
    step: PipelineStep,
    artifact: Artifact,
    fingerprint: str,
    context: Context,
):
    env = await context.get("env", YouwolEnvironment)
    async with context.start(
        action=f"create artifact '{artifact.id}'",
        with_attributes={
            "projectId": project.id,
            "flowId": flow_id,
            "stepId": step.id,
            "artifactId": artifact.id,
            "src fingerprint": fingerprint or "not-provided",
        },
    ) as ctx:
        files = matching_files(folder=project.path, patterns=artifact.files)

        paths: PathsBook = env.pathsBook
        await ctx.info(
            text=f"files retrieved ({len(files)})",
            data={"files": [str(f) for f in files]},
        )
        destination_folder = paths.artifact(
            project_name=project.name,
            flow_id=flow_id,
            step_id=step.id,
            artifact_id=artifact.id,
        )

        for f in files:
            destination_path = destination_folder / f.relative_to(project.path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            shutil.copy(src=f, dst=destination_path)

        await ctx.info(
            text="Artifact created",
            data={"destination_folder": str(destination_folder)},
        )
