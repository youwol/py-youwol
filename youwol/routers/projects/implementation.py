import os
import shutil
from typing import Tuple, List
from configuration import Project, PipelineStep, Artifact, Flow
from configuration.paths import PathsBook
from context import Context
from routers.projects.models import PipelineStepStatusResponse, Manifest, ArtifactResponse
from utils_low_level import to_json
from utils_paths import matching_files, parse_json


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
    steps = project.get_flow_steps(flow_id=flow_id)

    await context.info(text="project & flow & steps retrieved",
                       data={'project': to_json(project), 'flow': to_json(flow),
                             'steps': [s.id for s in steps]})
    return project, flow, steps


async def get_status(
        project: Project,
        flow_id: str,
        step: PipelineStep,
        context: Context
        ) -> PipelineStepStatusResponse:

    async with context.start(
            action="get status",
            with_attributes={'projectId': project.id, 'flowId': flow_id, 'stepId': step.id}
            ) as ctx:
        paths: PathsBook = ctx.config.pathsBook
        path = paths.artifacts_step(project_name=project.name, flow_id=flow_id, step_id=step.id)
        manifest = Manifest(**parse_json(path / 'manifest.json')) if (path / 'manifest.json').exists() else None

        status = await step.get_status(project=project, flow_id=flow_id, last_manifest=manifest, context=context)

        def format_artifact(artifact: Artifact):
            _path = paths.artifact(project_name=project.name, flow_id=flow_id, step_id=step.id, artifact_id=artifact.id)
            opening_url = f"{_path}/{artifact.openingUrl}" if artifact.openingUrl else None
            return ArtifactResponse(id=artifact.id, openingUrl=opening_url, path=_path)

        artifacts = [format_artifact(artifact) for artifact in step.artifacts]

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
            with_attributes={
                'projectId': project.id,
                'stepId': step.id,
                'event': 'PipelineStatusPending:run'
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

    async with context.start(
            action=f"create artifact '{artifact.id}'",
            with_attributes={'projectId': project.id, 'flowId': flow_id, 'stepId': step.id, 'artifactId': artifact.id,
                             'src fingerprint': fingerprint}
            ) as ctx:

        files = matching_files(
            folder=project.path,
            patterns=artifact.files
            )

        paths: PathsBook = ctx.config.pathsBook
        await ctx.info(text='got files listing', data=[str(f) for f in files])
        destination_folder = paths.artifact(project_name=project.name, flow_id=flow_id, step_id=step.id,
                                            artifact_id=artifact.id)

        for f in files:
            destination_path = destination_folder / f.relative_to(project.path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            shutil.copy(src=f, dst=destination_path)

        await context.info(text="Zip file created", data={'path': str(destination_path)})
