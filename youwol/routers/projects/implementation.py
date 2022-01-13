import os
import shutil
from typing import Tuple, List

from youwol.environment.youwol_environment import YouwolEnvironment
from youwol.environment.models_project import Project, PipelineStep, Artifact, Flow, Link, Manifest
from youwol.environment.paths import PathsBook
from youwol_utils import to_json
from youwol_utils.context import Context
from youwol.routers.commons import Label
from youwol.routers.projects.models import (
    PipelineStepStatusResponse, ArtifactResponse
    )
from youwol_utils.utils_paths import matching_files, parse_json


async def get_project_step(
        project_id: str,
        step_id: str,
        context: Context
        ) -> Tuple[Project, PipelineStep]:
    env = await context.get('env', YouwolEnvironment)
    project = next(p for p in env.projects if p.id == project_id)
    step = next(s for s in project.pipeline.steps if s.id == step_id)

    await context.info(text="project & step retrieved",
                       data={'project': to_json(project), 'step': to_json(step)})
    return project, step


async def get_project_flow_steps(
        project_id: str,
        flow_id: str,
        context: Context
        ) -> Tuple[Project, Flow, List[PipelineStep]]:

    env = await context.get('env', YouwolEnvironment)
    project = next(p for p in env.projects if p.id == project_id)
    flow = next(f for f in project.pipeline.flows if f.name == flow_id)
    steps = project.get_flow_steps(flow_id=flow_id)

    await context.info(text="project & flow & steps retrieved",
                       data={'project': to_json(project), 'flow': to_json(flow),
                             'steps': [s.id for s in steps]})
    return project, flow, steps


def format_artifact_response(
        project: Project,
        flow_id: str,
        step: PipelineStep,
        artifact: Artifact,
        env: YouwolEnvironment
        ) -> ArtifactResponse:

    paths: PathsBook = env.pathsBook

    path = paths.artifact(project_name=project.name, flow_id=flow_id, step_id=step.id, artifact_id=artifact.id)
    return ArtifactResponse(
        id=artifact.id,
        links=[Link(name=link.name, url=f"{path}/{link.url}") for link in artifact.links],
        path=path
        )


async def get_status(
        project: Project,
        flow_id: str,
        step: PipelineStep,
        context: Context
        ) -> PipelineStepStatusResponse:

    env = await context.get('env', YouwolEnvironment)
    paths: PathsBook = env.pathsBook
    async with context.start(
            action="get status",
            with_attributes={'projectId': project.id, 'flowId': flow_id, 'stepId': step.id}
            ) as _ctx:
        path = paths.artifacts_step(project_name=project.name, flow_id=flow_id, step_id=step.id)
        manifest = Manifest(**parse_json(path / 'manifest.json')) if (path / 'manifest.json').exists() else None

        status = await step.get_status(project=project, flow_id=flow_id, last_manifest=manifest, context=context)

        artifacts = [format_artifact_response(project=project, flow_id=flow_id, step=step, artifact=artifact,
                                              env=env)
                     for artifact in step.artifacts]

        return PipelineStepStatusResponse(
            projectId=project.id,
            flowId=flow_id,
            stepId=step.id,
            manifest=manifest,
            artifactFolder=path,
            artifacts=artifacts,
            status=status
            )


async def run(project: Project, flow_id: str, step: PipelineStep, context: Context):

    async with context.start(
            action="run function",
            with_labels=[str(Label.PIPELINE_STEP_RUNNING)],
            with_attributes={
                'projectId': project.id,
                'stepId': step.id
                }
            ) as ctx:

        return await step.execute_run(project, flow_id, ctx)


async def create_artifacts(
        project: Project,
        flow_id: str,
        step: PipelineStep,
        fingerprint: str,
        context: Context
        ):

    async with context.start(
            action="create artifacts",
            with_attributes={'projectId': project.id, 'flowId': flow_id, 'stepId': step.id,
                             'src fingerprint': fingerprint}
            ) as ctx:

        for artifact in step.artifacts:
            await create_artifact(
                project=project,
                flow_id=flow_id,
                step=step,
                artifact=artifact,
                fingerprint=fingerprint,
                context=ctx)


async def create_artifact(
        project: Project,
        flow_id: str,
        step: PipelineStep,
        artifact: Artifact,
        fingerprint: str,
        context: Context
        ):

    env = await context.get('env', YouwolEnvironment)
    async with context.start(
            action=f"create artifact '{artifact.id}'",
            with_attributes={'projectId': project.id, 'flowId': flow_id, 'stepId': step.id, 'artifactId': artifact.id,
                             'src fingerprint': fingerprint}
            ) as ctx:

        files = matching_files(
            folder=project.path,
            patterns=artifact.files
            )

        paths: PathsBook = env.pathsBook
        await ctx.info(text='got files listing', data=[str(f) for f in files])
        destination_folder = paths.artifact(project_name=project.name, flow_id=flow_id, step_id=step.id,
                                            artifact_id=artifact.id)

        for f in files:
            destination_path = destination_folder / f.relative_to(project.path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            shutil.copy(src=f, dst=destination_path)

        await context.info(text="Zip file created", data={'path': str(destination_path)})
