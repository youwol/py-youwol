import asyncio
import functools
import glob
import sys
import traceback
from enum import Enum
from pathlib import Path
from typing import List, Union, Set, Dict, Any, Callable, Awaitable, Iterable, cast, Optional
from pydantic import BaseModel
from aiostream import stream

from youwol.context import Context
from youwol.environment.forward_declaration import YouwolEnvironment
from youwol.environment.paths import PathsBook
from youwol.exceptions import CommandException
from youwol.models import Label
from youwol.utils_paths import matching_files, parse_json
from youwol_utils import JSON, files_check_sum

FlowId = str


class ErrorResponse(BaseModel):

    reason: str
    hints: List[str] = []


def format_unknown_error(reason: str, error: Exception):
    detail = error.args[0]
    error_class = error.__class__.__name__
    cl, exc, tb = sys.exc_info()
    line_number = traceback.extract_tb(tb)[-1][1]
    return ErrorResponse(
        reason=reason,
        hints=[f"{error_class} at line {line_number}: {detail}"]
        )


class Check(BaseModel):
    name: str
    status: Union[bool, ErrorResponse, None] = None


class FormalParameterEnum(Enum):
    STRING = 'STRING'
    ENUM = 'ENUM'


class FormalParameter(BaseModel):
    name: str
    value: Any
    description: str = ""
    meta: Dict[str, Any]


def parameter_enum(name: str, value: str, description: str, values: List[str]):
    return FormalParameter(
        name=name,
        value=value,
        description=description,
        meta={"type": 'ENUM', 'values': values}
        )


class ConfigParameters(BaseModel):
    parameters: Dict[str, FormalParameter]

    def get_values(self) -> Dict[str, Any]:
        return {pid: p.value for pid, p in self.parameters.items()}

    def with_updates(self, new_values: Dict[str, Any]) -> 'ConfigParameters':
        def new_param(pid: str, p: FormalParameter):
            return FormalParameter(name=p.name, description=p.description, meta=p.meta,
                                   value=new_values[pid] if pid in new_values else p.value)
        new_params = {pid: new_param(pid, p) for pid, p in self.parameters.items()}
        return ConfigParameters(parameters=new_params)


class FileListing(BaseModel):
    include: List[str]
    ignore: List[str] = []


class SkeletonParameter(BaseModel):
    displayName: str
    id: str
    type: str
    required: bool
    description: str
    defaultValue: Any
    placeholder: str


class Skeleton(BaseModel):
    folder: Union[Path, str]
    description: str
    parameters: List[SkeletonParameter]
    generate: Callable[[Path, Dict[str, any], 'Pipeline', Context], Awaitable] = None


class Link(BaseModel):
    name: str
    url: str


class Artifact(BaseModel):
    id: str = ""
    files: FileListing
    links: List[Link] = []


class PipelineStepStatus(Enum):
    OK = "OK"
    KO = "KO"
    outdated = "outdated"
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
    ['Project', Optional[Manifest], Context],
    Union[PipelineStepStatus, Awaitable[PipelineStepStatus]]
]
RunImplicit = Callable[
    ['Project', FlowId, Context],
    Union[JSON, Awaitable[JSON]]
    ]
SourcesFct = Callable[
    ['Project', FlowId, Context],
    Union[Any, Awaitable[Any]]
    ]
SourcesFctImplicit = Callable[
    ['Project', FlowId, Context],
    Union[FileListing, Awaitable[FileListing]]
    ]
SourcesFctExplicit = Callable[
    ['Project', FlowId, Context],
    Union[Iterable[Path], Awaitable[Iterable[Path]]]
    ]


class PipelineStep(BaseModel):

    id: str = ""

    artifacts: List[Artifact] = []

    sources: Union[FileListing, SourcesFctImplicit, SourcesFctExplicit] = None

    async def get_sources(self, project: 'Project', flow_id: FlowId, context: Context) -> Optional[Iterable[Path]]:

        if self.sources is None:
            return None

        if isinstance(self.sources, FileListing):
            return matching_files(folder=project.path, patterns=self.sources)
        sources_fct = cast(SourcesFct, self.sources)
        r = await sources_fct(project, flow_id, context)
        return matching_files(folder=project.path, patterns=r) if isinstance(r, FileListing) else r

    status: StatusFct = None

    async def get_status(self, project: 'Project', flow_id: str, last_manifest: Optional[Manifest], context: Context) \
            -> PipelineStepStatus:

        if last_manifest is None:
            await context.info(text="No manifest found => status is none")
            return PipelineStepStatus.none

        await context.info(text="Manifest retrieved", data=last_manifest)

        fingerprint, _ = await self.get_fingerprint(project=project, flow_id=flow_id, context=context)
        await context.info(text="Actual fingerprint", data=fingerprint)

        if last_manifest.fingerprint != fingerprint:
            await context.info(text="Outdated entry",
                               data={'actual fp': fingerprint, 'saved fp': last_manifest.fingerprint})
            return PipelineStepStatus.outdated

        return PipelineStepStatus.OK if last_manifest.succeeded else PipelineStepStatus.KO

    run: Union[str, RunImplicit, ExplicitNone]

    async def execute_run(self, project: 'Project', flow_id: FlowId, context: Context):

        if isinstance(self.run, ExplicitNone):
            raise RuntimeError("When 'ExplicitNone' is provided, the step must overrides the 'execute_run' method")

        if isinstance(self.run, str):
            await context.info(f'Run cmd {self.run}')
            return await self.__execute_run_cmd(project=project, run_cmd=self.run, context=context)

        try:
            run = cast(self.run, Callable[['Project', str, Context], Awaitable[JSON]])
            await context.info(f'Run custom function')
            outputs = await run(project, flow_id, context)
        except Exception as e:
            raise CommandException(command=f"custom run function", outputs=[str(e)])

        return outputs

    async def get_fingerprint(self, project: 'Project', flow_id: FlowId, context: Context):

        files = await self.get_sources(project=project, flow_id=flow_id, context=context)
        if files is None:
            return None, []
        await context.info(text='got file listing', data={"files": [str(f) for f in files]})
        checksum = files_check_sum(files)
        return checksum, files

    async def __execute_run_cmd(self, project: 'Project', run_cmd: str, context: Context):

        p = await asyncio.create_subprocess_shell(
            cmd=f"(cd  {str(project.path)} && {run_cmd})",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=True
            )
        outputs = []
        async with stream.merge(p.stdout, p.stderr).stream() as messages_stream:
            async for message in messages_stream:
                outputs.append(message.decode('utf-8'))
                await context.info(text=outputs[-1], labels=[Label.BASH])
        await p.communicate()

        return_code = p.returncode

        if return_code > 0:
            raise CommandException(command=f"{project.name}#{self.id} ({self.run})", outputs=outputs)
        return outputs


class Flow(BaseModel):
    name: str
    dag: List[str]


class Pipeline(BaseModel):

    id: str
    language: Optional[str] = None
    compiler: Optional[str] = None
    output: Optional[str] = None
    description: str = ""
    skeleton: Union[Skeleton, Callable[[YouwolEnvironment], Skeleton]] = None
    steps: List[PipelineStep]
    flows: List[Flow]
    extends: Optional[str] = None
    dependencies: Callable[['Project', Context], Set[str]] = None
    projectName: Callable[[Path], str]
    projectVersion: Callable[[Path], str]


class Project(BaseModel):
    pipeline: Pipeline
    path: Path
    name: str
    id: str  # base64 encoded Project.name
    version: str

    def get_dependencies(self, recursive: bool, context: Context, ignore: List[str] = None) -> List['Project']:
        ignore = ignore or []
        all_dependencies = self.pipeline.dependencies(self, context)
        dependencies = [p for p in context.config.projects if p.name in all_dependencies and p.name not in ignore]
        ignore = ignore + [p.name for p in dependencies]
        if not recursive:
            return dependencies
        dependencies_rec = functools.reduce(lambda acc, e: acc+e, [
            dependencies,
            *[p.get_dependencies(recursive=recursive, context=context, ignore=ignore) for p in dependencies]
            ])

        return dependencies_rec

    async def get_artifact_files(self, flow_id: str, artifact_id: str, context: Context) -> List[Path]:

        steps = self.get_flow_steps(flow_id=flow_id)
        step = next((s for s in steps if artifact_id in [a.id for a in s.artifacts]), None)
        if not step:
            artifacts_id = [a.id for s in steps for a in s.artifacts]
            await context.error(text=f"Can not find artifact '{artifact_id}' in given flow '{flow_id}'",
                                data={"artifacts_id": artifacts_id})
        folder = context.config.pathsBook.artifact(project_name=self.name, flow_id=flow_id, step_id=step.id,
                                                   artifact_id=artifact_id)

        if not folder.exists() or not folder.is_dir():
            return []
        return [Path(p) for p in glob.glob(str(folder) + '/**/*', recursive=True) if Path(p).is_file()]

    def get_flow_steps(
            self,
            flow_id: str
            ) -> List[PipelineStep]:

        flow = next(f for f in self.pipeline.flows if f.name == flow_id)
        involved_steps = set([step.strip() for b in flow.dag for step in b.split('>')])
        steps = [step for step in self.pipeline.steps if step.id in involved_steps]

        return steps

    def get_manifest(self, flow_id: FlowId, step: PipelineStep, context: Context):
        paths_book: PathsBook = context.config.pathsBook
        manifest_path = paths_book.artifacts_manifest(project_name=self.name, flow_id=flow_id, step_id=step.id)
        if not manifest_path.exists():
            return None
        return Manifest(**parse_json(manifest_path))
