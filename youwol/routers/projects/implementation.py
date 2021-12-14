import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional
from configuration import Project, PipelineStep, Artifact, PipelineStepStatus
from context import Context, CommandException
from models import Label
from routers.projects.models import PipelineStepStatusResponse, Manifest, ArtifactResponse
from utils_low_level import merge
from utils_paths import matching_files, parse_json
from youwol_utils import files_check_sum


def artifacts_path(project: Project, flow_id: str, step: PipelineStep, context: Context):
    return context.config.pathsBook.system / project.name / flow_id / step.id


def artifact_path(project: Project, flow_id: str, step: PipelineStep, artifact: Artifact, context: Context) -> Path:
    return artifacts_path(project=project, flow_id=flow_id, step=step, context=context) / f"artifact-{artifact.id}"


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

        path = artifacts_path(project=project, flow_id=flow_id, step=step, context=ctx)
        artifacts = [
            ArtifactResponse(
                id=artifact.id,
                path=artifact_path(project=project, flow_id=flow_id, step=step, artifact=artifact, context=ctx))
            for artifact in step.artifacts]

        if not (path / 'manifest.json').exists():
            await ctx.info(text="No manifest found => status is none")
            return PipelineStepStatusResponse(
                projectId=project.id,
                flowId=flow_id,
                stepId=step.id,
                artifactFolder=path,
                artifacts=artifacts,
                status=PipelineStepStatus.none
                )

        manifest = Manifest(**parse_json(path / 'manifest.json'))
        await ctx.info(text="Manifest retrieved", data=manifest)

        fingerprint, _ = await get_fingerprint(project=project, step=step, context=ctx)
        await ctx.info(text="Actual fingerprint", data=fingerprint)
        if manifest.fingerprint != fingerprint:
            await ctx.info(text="Outdated entry", data={'actual fp': fingerprint, 'saved fp': manifest.fingerprint})
            return PipelineStepStatusResponse(
                projectId=project.id,
                flowId=flow_id,
                stepId=step.id,
                manifest=manifest,
                artifactFolder=path,
                artifacts=artifacts,
                status=PipelineStepStatus.outdated
                )

        return PipelineStepStatusResponse(
                projectId=project.id,
                flowId=flow_id,
                stepId=step.id,
                manifest=manifest,
                artifactFolder=path,
                artifacts=artifacts,
                status=PipelineStepStatus.OK if manifest.succeeded else PipelineStepStatus.KO
                )


async def run(project: Project, step: PipelineStep, context: Context):

    if not isinstance(step.run, str):
        raise RuntimeError("Ony run command as string are supported for now")

    async with context.start(
            action="run command",
            labels=[Label.BASH],
            with_attributes={
                'projectId': project.id,
                'stepId': step.id,
                'command': step.run,
                'event': 'PipelineStatusPending:run'
                }
            ) as ctx:

        p = await asyncio.create_subprocess_shell(
            cmd=f"(cd  {str(project.path)} && {step.run})",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
            )
        outputs = []
        async for f in merge(p.stdout, p.stderr):
            outputs.append(f.decode('utf-8'))
            await ctx.info(text=outputs[-1], labels=[Label.BASH])

        await p.communicate()

        return_code = p.returncode

        if return_code > 0:
            raise CommandException(command=f"{project.name}#{step.id} ({step.run})", outputs=outputs)
        return outputs


async def get_fingerprint(project: Project, step: PipelineStep, context: Context):

    checksum: Optional[str] = None

    async with context.start(
            action="fingerprint",
            succeeded_data=lambda _ctx: ("fingerprint", checksum),
            with_attributes={'projectId': project.id, 'stepId': step.id}
            ) as ctx:

        if step.sources:
            files = matching_files(
                folder=project.path,
                patterns=step.sources
                )
            await ctx.info(text='got file listing', data=[str(f) for f in files])
            checksum = files_check_sum(files)
            return checksum, files

        raise RuntimeError("fingerprint can only be FileListing for now")


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

        await ctx.info(text='got files listing', data=[str(f) for f in files])
        destination_folder = artifact_path(project=project, flow_id=flow_id, step=step, artifact=artifact, context=ctx)
        # zipper = zipfile.ZipFile(destination_path, 'w', zipfile.ZIP_DEFLATED)
        for f in files:
            destination_path = destination_folder / f.relative_to(project.path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            shutil.copy(src=f, dst=destination_path)
            # zipper.write(filename=f, arcname=f.relative_to(project.path))
        # zipper.close()

        await context.info(text="Zip file created", data={'path': str(destination_path)})
