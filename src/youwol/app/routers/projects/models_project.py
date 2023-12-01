# standard library
import asyncio
import functools
import itertools

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

# typing
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Set,
    Union,
    cast,
)

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import PathsBook, YouwolEnvironment

# Youwol utilities
from youwol.utils import JSON, CommandException, execute_shell_cmd, files_check_sum
from youwol.utils.context import Context
from youwol.utils.utils_paths import matching_files, parse_json

FlowId = str


class LinkKind(Enum):
    artifactFile = "artifactFile"
    plainUrl = "plainUrl"


class FileListing(BaseModel):
    include: List[str]
    ignore: List[str] = []


class Link(BaseModel):
    name: str
    url: str
    kind: LinkKind = LinkKind.artifactFile


class Artifact(BaseModel):
    id: str = ""
    files: FileListing
    links: List[Link] = []


class PipelineStepStatus(Enum):
    OK = "OK"
    KO = "KO"
    outdated = "outdated"
    running = "running"
    none = "none"


class Manifest(BaseModel):
    succeeded: bool
    fingerprint: Optional[str]
    creationDate: str
    files: List[str]
    cmdOutputs: Union[List[str], Dict] = []


class ExplicitNone(BaseModel):
    pass


StatusFct = Callable[
    ["Project", Optional[Manifest], Context],
    Union[PipelineStepStatus, Awaitable[PipelineStepStatus]],
]
RunImplicit = Callable[
    ["PipelineStep", "Project", FlowId, Context], Union[str, Awaitable[str]]
]
SourcesFct = Callable[
    ["PipelineStep", "Project", FlowId, Context], Union[Any, Awaitable[Any]]
]
SourcesFctImplicit = Callable[
    ["PipelineStep", "Project", FlowId, Context],
    Union[FileListing, Awaitable[FileListing]],
]
SourcesFctExplicit = Callable[
    ["PipelineStep", "Project", FlowId, Context],
    Union[Iterable[Path], Awaitable[Iterable[Path]]],
]


class CommandPipelineStep(BaseModel):
    name: str
    do_get: Optional[
        Callable[["Project", str, Context], Union[Awaitable[JSON], JSON]]
    ] = None
    do_post: Optional[
        Callable[["Project", str, JSON, Context], Union[Awaitable[JSON], JSON]]
    ] = None
    do_put: Optional[
        Callable[["Project", str, JSON, Context], Union[Awaitable[JSON], JSON]]
    ] = None
    do_delete: Optional[
        Callable[["Project", str, Context], Union[Awaitable[JSON], JSON]]
    ] = None


class PipelineStep(BaseModel):
    id: str = ""

    artifacts: List[Artifact] = []

    sources: Union[FileListing, SourcesFctImplicit, SourcesFctExplicit] = None

    view: Optional[Path]

    http_commands: List[CommandPipelineStep] = []

    async def get_sources(
        self, project: "Project", flow_id: FlowId, context: Context
    ) -> Optional[Iterable[Path]]:
        if self.sources is None:
            return None

        if isinstance(self.sources, FileListing):
            return matching_files(folder=project.path, patterns=self.sources)
        sources_fct = cast(SourcesFct, self.sources)
        r = sources_fct(self, project, flow_id, context)
        r = await r if isinstance(r, Awaitable) else r
        return (
            matching_files(folder=project.path, patterns=r)
            if isinstance(r, FileListing)
            else r
        )

    status: StatusFct = None

    async def get_status(
        self,
        project: "Project",
        flow_id: str,
        last_manifest: Optional[Manifest],
        context: Context,
    ) -> PipelineStepStatus:
        if not last_manifest:
            await context.info(
                text="No manifest found, status is PipelineStepStatus.none"
            )
            return PipelineStepStatus.none

        env: YouwolEnvironment = await context.get("env", YouwolEnvironment)
        artifacts = [
            env.pathsBook.artifact(
                project_name=project.name,
                flow_id=flow_id,
                step_id=self.id,
                artifact_id=artifact.id,
            )
            for artifact in self.artifacts
        ]

        if any(not path.exists() for path in artifacts):
            return PipelineStepStatus.none

        await context.info(text="Manifest retrieved", data=last_manifest)

        fingerprint, _ = await self.get_fingerprint(
            project=project, flow_id=flow_id, context=context
        )
        await context.info(text="Actual fingerprint", data={"fingerprint": fingerprint})

        if last_manifest.fingerprint != fingerprint:
            await context.info(
                text="Outdated entry",
                data={"actual fp": fingerprint, "saved fp": last_manifest.fingerprint},
            )
            return PipelineStepStatus.outdated

        return PipelineStepStatus.OK

    run: Union[str, RunImplicit, ExplicitNone]

    async def execute_run(self, project: "Project", flow_id: FlowId, context: Context):
        if isinstance(self.run, ExplicitNone):
            raise RuntimeError(
                "When 'ExplicitNone' is provided, the step must overrides the 'execute_run' method"
            )

        if isinstance(self.run, str):
            await context.info(f"Run cmd {self.run}")
            return await PipelineStep.__execute_run_cmd(
                project=project, run_cmd=self.run, context=context
            )

        run = cast(
            Callable[["PipelineStep", "Project", str, Context], Awaitable[str]],
            self.run,
        )
        await context.info("Run custom function")
        run_cmd = run(self, project, flow_id, context)
        run_cmd = await run_cmd if isinstance(run_cmd, Awaitable) else run_cmd
        return await PipelineStep.__execute_run_cmd(
            project=project, run_cmd=run_cmd, context=context
        )

    async def get_fingerprint(
        self, project: "Project", flow_id: FlowId, context: Context
    ):
        async with context.start(action="get_fingerprint") as ctx:
            files = await self.get_sources(
                project=project, flow_id=flow_id, context=context
            )
            if files is None:
                return None, []
            files = list(files)
            if len(files) > 1000:
                await ctx.warning(
                    text=f"Retrieved large number of source code files ({len(files)})"
                )
            await ctx.info(
                text="got file listing",
                data={f"files ({len(files)})": [str(f) for f in files[0:1000]]},
            )
            checksum = files_check_sum(files)
            return checksum, files

    @staticmethod
    async def __execute_run_cmd(project: "Project", run_cmd: str, context: Context):
        return_code, outputs = await execute_shell_cmd(
            cmd=f"(cd  {str(project.path)} && {run_cmd})", context=context
        )
        if return_code > 0:
            raise CommandException(command=run_cmd, outputs=outputs)
        return outputs


class Flow(BaseModel):
    name: str
    dag: List[str]


class Family(Enum):
    application = "application"
    library = "library"
    service = "service"


class Target(BaseModel):
    family: Family
    links: List[Link] = []


class BrowserTarget(Target):
    pass


class BrowserLibBundle(BrowserTarget):
    family: Family = Family.library


JsBundle = BrowserLibBundle


class EntryPoint(Target):
    name: str


class Asset(BaseModel):
    kind: str
    mimeType: str
    name: str
    rawId: str
    assetId: str


class Parametrization(BaseModel):
    pass


class FromAsset(Parametrization):
    match: Dict
    parameters: Dict


class OpenWith(Parametrization):
    name: Optional[str]
    match: Union[Dict, str]
    parameters: Union[Dict, str]


class Execution(BaseModel):
    standalone: bool = True
    parametrized: List[Parametrization] = []


class BrowserAppGraphics(BaseModel):
    appIcon: Optional[Any]
    fileIcon: Optional[Any]
    background: Any


class BrowserAppBundle(BrowserTarget):
    family: Family = Family.application
    displayName: Optional[str] = None
    execution: Execution = Execution()
    graphics: BrowserAppGraphics


BrowserApp = BrowserAppBundle


class MicroService(Target):
    family: str = Family.service


class Pipeline(BaseModel):
    target: Target
    tags: List[str] = []
    description: str = ""
    steps: List[PipelineStep]
    flows: List[Flow]
    extends: Optional[str] = None
    dependencies: Callable[["Project", Context], Set[str]] = None
    projectName: Callable[[Path], str]
    projectVersion: Callable[[Path], str]


class IPipelineFactory(ABC):
    @abstractmethod
    async def get(self, _env: YouwolEnvironment, _context: Context) -> Pipeline:
        return NotImplemented


class Project(BaseModel):
    pipeline: Pipeline
    path: Path
    name: str
    publishName: str
    id: str  # base64 encoded Project.name
    version: str

    async def get_dependencies(
        self,
        projects: List["Project"],
        recursive: bool,
        context: Context,
        ignore: List[str] = None,
    ) -> List["Project"]:
        ignore = ignore or []
        all_dependencies = (
            self.pipeline.dependencies(self, context)
            if self.pipeline.dependencies
            else []
        )
        dependencies = [
            p for p in projects if p.name in all_dependencies and p.name not in ignore
        ]
        ignore = ignore + [p.name for p in dependencies]
        if not recursive:
            return dependencies
        dependencies_rec = functools.reduce(
            lambda acc, e: acc + e,
            [
                dependencies,
                *[
                    await p.get_dependencies(
                        recursive=recursive,
                        projects=projects,
                        context=context,
                        ignore=ignore,
                    )
                    for p in dependencies
                ],
            ],
        )

        return dependencies_rec

    async def get_artifact_files(
        self, flow_id: str, artifact_id: str, context: Context
    ) -> List[Path]:
        async with context.start(
            action="get_artifact_files", with_attributes={"artifact": artifact_id}
        ) as ctx:  # type: Context
            env = await context.get("env", YouwolEnvironment)
            steps = self.get_flow_steps(flow_id=flow_id)
            step = next(
                (s for s in steps if artifact_id in [a.id for a in s.artifacts]), None
            )
            await ctx.info(text="Step retrieved", data={"step": step})
            if not step:
                artifacts_id = [a.id for s in steps for a in s.artifacts]
                await ctx.error(
                    text=f"Can not find artifact '{artifact_id}' in given flow '{flow_id}'",
                    data={"artifacts_id": artifacts_id},
                )
            folder = env.pathsBook.artifact(
                project_name=self.name,
                flow_id=flow_id,
                step_id=step.id,
                artifact_id=artifact_id,
            )
            await ctx.info(text=f"Target folder: {folder}")
            if not folder.exists() or not folder.is_dir():
                await ctx.error(text="Target folder does not exist")
                return []
            files = [Path(p) for p in folder.glob("**/*") if Path(p).is_file()]
            await ctx.info(
                text=f"Retrieved {len(files)} files",
                data={"files[0:100]": files[0:100]},
            )
            return files

    async def get_step_artifacts_files(
        self, flow_id: str, step_id: str, context: Context
    ) -> List[Path]:
        steps = self.get_flow_steps(flow_id=flow_id)
        step = next((s for s in steps if s.id == step_id), None)
        files = await asyncio.gather(
            *[
                self.get_artifact_files(
                    flow_id=flow_id, artifact_id=artifact.id, context=context
                )
                for artifact in step.artifacts
            ]
        )
        return list(itertools.chain.from_iterable(files))

    def get_flow_steps(self, flow_id: str) -> List[PipelineStep]:
        flow = next(f for f in self.pipeline.flows if f.name == flow_id)
        involved_steps = set(step.strip() for b in flow.dag for step in b.split(">"))
        steps = [step for step in self.pipeline.steps if step.id in involved_steps]

        return steps

    def get_downstream_flow_steps(
        self, flow_id: str, from_step_id: str, from_step_included: bool
    ) -> List[PipelineStep]:
        flow = next(f for f in self.pipeline.flows if f.name == flow_id)
        branches = [[step.strip() for step in branch.split(">")] for branch in flow.dag]

        def implementation(from_step_tmp):
            starts = [
                (step, i, branch)
                for branch in branches
                for i, step in enumerate(branch)
                if step == from_step_tmp
            ]
            return set(s for step, i, branch in starts for s in branch[i + 1 :])

        downstream_steps = implementation(from_step_tmp=from_step_id)
        indirect = [implementation(from_step_tmp=s) for s in downstream_steps]
        involved_steps = downstream_steps.union(
            *indirect, {from_step_id} if from_step_included else {}
        )
        steps = [step for step in self.pipeline.steps if step.id in involved_steps]
        return steps

    def get_direct_upstream_steps(
        self, flow_id: str, step_id: str
    ) -> List[PipelineStep]:
        def get_direct_upstream_step_in_branch(branch: List[str]) -> Optional[str]:
            if step_id not in branch:
                return None

            if branch.index(step_id) == 0:
                return None

            return branch[(branch.index(step_id) - 1)]

        flow = next(f for f in self.pipeline.flows if f.name == flow_id)
        branches = [[step.strip() for step in branch.split(">")] for branch in flow.dag]
        steps_ids = [
            step
            for step in [
                get_direct_upstream_step_in_branch(branch) for branch in branches
            ]
            if step is not None
        ]
        return [step for step in self.pipeline.steps if step.id in steps_ids]

    def get_manifest(self, flow_id: FlowId, step: PipelineStep, env: YouwolEnvironment):
        paths_book: PathsBook = env.pathsBook
        manifest_path = paths_book.artifacts_manifest(
            project_name=self.name, flow_id=flow_id, step_id=step.id
        )
        if not manifest_path.exists():
            return None
        return Manifest(**parse_json(manifest_path))


class CreateProjectFromTemplateResponse(Project):
    pass
