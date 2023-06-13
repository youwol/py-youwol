# standard library
import asyncio
import datetime
import functools

# typing
from typing import Optional

# Youwol application
from youwol.app.routers.projects.models_project import (
    FlowId,
    Manifest,
    PipelineStep,
    PipelineStepStatus,
    Project,
)

# Youwol utilities
from youwol.utils import CommandException, execute_shell_cmd
from youwol.utils.context import Context

# relative
from .models import NpmRepo


async def get_shasum_published(project: Project, context: Context):
    _, outputs = await execute_shell_cmd(
        cmd=f"npm view {project.name}@{project.version} dist.shasum", context=context
    )
    return outputs[0].replace("\n", "")


async def get_shasum_local(project: Project, context: Context):
    shasum_prefix = "shasum:"
    _, outputs = await execute_shell_cmd(
        cmd=f"(cd {project.path} && npm publish --dry-run)", context=context
    )
    shasum_line = next(line for line in outputs if shasum_prefix in line)
    return shasum_line.split(shasum_prefix)[1].strip()


class PublishNpmStep(PipelineStep):
    id: str = "publish-npm"
    run: str = "yarn publish --access public"
    npm_target: NpmRepo

    async def execute_run(self, project: "Project", flow_id: FlowId, context: Context):
        async with context.start(
            action="PublishNpmStep.execute_run",
        ) as ctx:
            npm_outputs = await self.npm_target.publish(project=project, context=ctx)
            shasum_published, shasum_local = await asyncio.gather(
                get_shasum_published(project=project, context=context),
                get_shasum_local(project=project, context=context),
            )

            return {
                "npm_outputs": npm_outputs,
                "shasum_published": shasum_published,
                "shasum_local": shasum_local,
                "version": project.version,
                "date": f"{datetime.date.today()}",
            }

    async def get_status(
        self,
        project: Project,
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        async with context.start(
            action="PublishNpmStep.get_status",
        ) as ctx:
            shasum_prefix = "shasum:"
            cmd = f"npm view {project.name} versions --json"
            exit_code, outputs = await execute_shell_cmd(cmd=cmd, context=ctx)

            if exit_code != 0 and "E404" in outputs[0]:
                return PipelineStepStatus.none

            if exit_code != 0:
                raise CommandException(command=cmd, outputs=outputs)

            flat_output = functools.reduce(lambda acc, e: acc + e, outputs, "")
            if f'"{project.version}"' not in flat_output:
                return PipelineStepStatus.none

            exit_code, outputs = await execute_shell_cmd(
                cmd=f"npm view {project.name}@{project.version} dist.shasum",
                context=ctx,
            )
            shasum_published = outputs[0].replace("\n", "")
            exit_code, outputs = await execute_shell_cmd(
                cmd=f"(cd {project.path} && npm publish --dry-run)", context=ctx
            )
            shasum_line = next(line for line in outputs if shasum_prefix in line)
            shasum_project = shasum_line.split(shasum_prefix)[1].strip()
            return (
                PipelineStepStatus.OK
                if shasum_published == shasum_project
                else PipelineStepStatus.outdated
            )
