# standard library
import asyncio
import functools
import itertools

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Iterable
from enum import Enum
from pathlib import Path

# typing
from typing import Any, Callable, Optional, Union, cast

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
    """
    The kind of link.
    """

    artifactFile = "artifactFile"
    """
    The link refers to a file in an artifact.
    """
    plainUrl = "plainUrl"
    """
    The link is an absolute URL.
    """


class FileListing(BaseModel):
    """
    Describes an implicit list of files from patterns to include or ignore.
    """

    include: list[str]
    """
    Patterns to include.
    """
    ignore: list[str] = []
    """
    Patterns to ignore.
    """


class Link(BaseModel):
    """
    Describes a link.
    """

    name: str
    """
    Name of the link
    """
    url: str
    """
    URL of the link, can reference either a file on disk, or can be an absolute URL.
    """
    kind: LinkKind = LinkKind.artifactFile
    """
    The kind of the link.
    """


class Artifact(BaseModel):
    """
    Artifact of a [PipelineStep](@yw-nav-class:youwol.app.routers.projects.models_project.PipelineStep).
    """

    id: str = ""
    """
    ID of the artifact.
    """
    files: FileListing
    """
    Describer of the files list to include in the artifact.
    """
    links: list[Link] = []
    """
    Eventual associated links (e.g. to the coverage.html for a test artifact).
    """


class PipelineStepStatus(Enum):
    """
    Status of a pipeline's step execution.
    """

    OK = "OK"
    """
    In sync: inputs of the step have not changed, and produced artifacts are available.
    """
    KO = "KO"
    """
    Execution leads to error.
    """
    outdated = "outdated"
    """
    Execution need to be re-run: some inputs of the step changed.
    """
    running = "running"
    """
    Step is actually running.
    """
    none = "none"
    """
    Expected outcome of the step does not exist.
    """


class Manifest(BaseModel):
    """
    Describes a manifest of execution of a step.
    """

    succeeded: bool
    """
    Whether the step succeeded to execute.
    """

    fingerprint: Optional[str]
    """
    Fingerprint of the step.
    """

    creationDate: str
    """
    Date of creation.
    """

    files: list[str]
    """
    Files path of the artifacts' files.
    """
    cmdOutputs: Union[list[str], dict] = []
    """
    The outputs generated during step execution.
    """


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
    """
    A command associated to an HTTP end-point for a
    [PipelineStep](@yw-nav-class:youwol.app.routers.projects.models_project.PipelineStep).

    They can be triggered using the URL:
    `GET/POST/PUT/DELETE: /admin/projects/{project_id}/flows/{flow_id}/steps/{step_id}/commands/{command_id}`
    """

    name: str
    """
    name of the command
    """

    do_get: Optional[
        Callable[["Project", str, Context], Union[Awaitable[JSON], JSON]]
    ] = None
    """
    Declare a `GET` end-point.

    Arguments of the callable:

        *  Project : reference on the [Project](@yw-nav-class:youwol.app.routers.projects.models_project.Project)
        *  str : flow ID
        *  Context : current execution [Context](@yw-nav-class:youwol.utils.context.Context)]
    """

    do_post: Optional[
        Callable[["Project", str, JSON, Context], Union[Awaitable[JSON], JSON]]
    ] = None
    """
    Declare a `POST` end-point.

    Arguments of the callable:

        *  Project : reference on the [Project](@yw-nav-class:youwol.app.routers.projects.models_project.Project)
        *  str : flow ID
        *  JSON : body of the POST
        *  Context : current execution [Context](@yw-nav-class:youwol.utils.context.Context)]
    """

    do_put: Optional[
        Callable[["Project", str, JSON, Context], Union[Awaitable[JSON], JSON]]
    ] = None
    """
    Declare a `PUT` end-point.

    Arguments of the callable:

        *  Project : reference on the [Project](@yw-nav-class:youwol.app.routers.projects.models_project.Project)
        *  str : flow ID
        *  JSON : body of the PUT
        *  Context : current execution [Context](@yw-nav-class:youwol.utils.context.Context)
    """

    do_delete: Optional[
        Callable[["Project", str, Context], Union[Awaitable[JSON], JSON]]
    ] = None
    """
    Declare a `DELETE` end-point.

    Arguments of the callable:
        *  Project : reference on the [Project](@yw-nav-class:youwol.app.routers.projects.models_project.Project)
        *  str : flow ID
        *  Context : current execution [Context](@yw-nav-class:youwol.utils.context.Context)
    """


class PipelineStep(BaseModel):
    """
    Base class for pipeline step.
    """

    id: str = ""
    """
    Id of the pipeline.
    """
    artifacts: list[Artifact] = []
    """
    List of artifacts produced by the step.
    """

    sources: Union[FileListing, SourcesFctImplicit, SourcesFctExplicit] = None
    """
    This attribute is used to check whether the status of the step is up-to-date regarding the files that
    generated it. For instance, in a typescript project it would include all the `.ts` files as well as some
    configuration files.

    In many scenarios using [FileListing](@yw-nav-class:youwol.app.routers.projects.models_project.FileListing) is
    enough, the other type of input can be useful when a reference on the actual project is needed.
    When using a [FileListing](@yw-nav-class:youwol.app.routers.projects.models_project.FileListing), the path are
    referenced from the path of the project.

    Yet, in some other scenario, the status of a step does not relies on files, in this case `sources` can
    be omitted, then either:

    *  a concept of 'fingerprint' stands: you should override the method
    `async def get_fingerprint(self, project: "Project", flow_id: FlowId, context: Context)` of this class
    *  if not, overrides the method `async def get_status(self, project: "Project", flow_id: str,
    last_manifest: Optional[Manifest], context: Context,) -> PipelineStepStatus` of this class.
    """

    view: Optional[Path]
    """
    It is the path of a javascript file that returns a function generating a view, it has the following signature:

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

        const {foo, bar} = await webpmClient.install({modules:['foo#^1.2.3', 'bar#^2.3.4']})'
        //  use foo and bar to create reactive view
        //  can interact with the custom backends of the step using projectsRouter.executeStepGetCommand$
        //  return the view
        }

    return getView;
    ```

    In practice, the view often interact with commands defined by the step (usually to retrieve data).
    See the attribute `http_commands`.
    """

    http_commands: list[CommandPipelineStep] = []
    """
    List of custom HTTP endpoints exposed for the step. Usually used within the `view` attribute.
    They are exposed from the router
    [pipeline_step_view](@yw-nav-func:youwol.app.routers.projects.router.pipeline_step_view).
    """

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
    """
    Action to execute when the step is run.

    Behavior w/ the type provided:

    *  *str* : the value is executed as shell command from the folder of the project
    *  [RunImplicit](@yw-nav-class:youwol.app.routers.projects.models_project.RunImplicit): the callback is called
    *  [ExplicitNone](@yw-nav-class:youwol.app.routers.projects.models_project.ExplicitNone): you should override
        the `async def execute_run(self, project: "Project", flow_id: FlowId, context: Context)` method of this class.

    """

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
    """
    Describes the connection between
    [PipelineStep](@yw-nav-class:youwol.app.routers.projects.models_project.PipelineStep).

    **Example**

    ```python
    flow = Flow(name='flow', steps=['init > build > publish', 'init > doc > publish'])
    ```
    Where `init`, `build`, `doc`, `publish` refers to ID of steps included in the
     [Pipeline](@yw-nav-class:youwol.app.routers.projects.models_project.Pipeline).
    """

    name: str
    """
    Name of the flow.
    """

    dag: list[str]
    """
    String representation of the branches involved in the DAG. See the example in the class documentation.
    """


class Family(Enum):
    """
    The family of the target produced by a
    [Pipeline](@yw-nav-class:youwol.app.routers.projects.models_project.Pipeline).
    """

    application = "application"
    """
    A frontend application.
    """
    library = "library"
    """
    A frontend library.
    """
    service = "service"
    """
    A backend service.
    """


class Target(BaseModel):
    """
    Base class to describe what kind of target a
    [Pipeline](@yw-nav-class:youwol.app.routers.projects.models_project.Pipeline)
     is aiming to produce as well as some associated links.

     Prefer using concrete class
     [BrowserLibBundle](@yw-nav-class:youwol.app.routers.projects.models_project.BrowserLibBundle) or
     [BrowserAppBundle](@yw-nav-class:youwol.app.routers.projects.models_project.BrowserAppBundle).
    """

    family: Family
    """
    The kind of target.
    """
    links: list[Link] = []
    """
    List of links associated to the pipeline's target (e.g. documentation, coverage, etc).
    """


class BrowserTarget(Target):
    pass


class BrowserLibBundle(BrowserTarget):
    """
    Describes run-time metadata for a front-end libraries.
    """

    family: Family = Family.library


JsBundle = BrowserLibBundle


class EntryPoint(Target):
    name: str


class Asset(BaseModel):
    """
    Describes the property available for an asset.
    """

    kind: str
    """
    Kind of the asset
    """

    mimeType: str
    name: str
    """
    Name of the asset
    """

    rawId: str
    """
    Raw ID of the asset
    """

    assetId: str
    """
    Asset ID
    """


class Parametrization(BaseModel):
    pass


class FromAsset(Parametrization):
    match: dict
    parameters: dict


class OpenWith(Parametrization):
    """
    Describes how to open an application from an
     [Asset](@yw-nav-class:youwol.app.routers.projects.models_project.Asset).

    For instance `OpenWith(match={"kind": "story"}, parameters={"id": "rawId"})` will:

    *  be available only for asset of `kind` `story`
    *  will pass as query parameters in the application URL the parameter `id=asset['rawId']`.
    """

    name: Optional[str]
    """
    name of the action
    """
    match: Union[dict, str]
    """
    Matching specifier.
    """
    parameters: Union[dict, str]
    """
    Parameters mapper between the asset and the URL's query parameters of the application to launch.
    """


class Execution(BaseModel):
    """
    Describes the execution mode of a [BrowserApp](@yw-nav-class:youwol.app.routers.projects.models_project.BrowserApp)
    application.
    """

    standalone: bool = True
    """
    Whether the application can be launched with no additional parameters (e.g. ID of a file/project)
    """

    parametrized: list[Parametrization] = []
    """
    Allow to plug execution of the application from an asset.
    """


class BrowserAppGraphics(BaseModel):
    """
    Describes graphics regarding application.
    """

    appIcon: Optional[Any]
    """
    The icon of the application provided, as json description of an html element.
    """

    fileIcon: Optional[Any]
    """
    The icon of a file that can be opened by the application, provided as json description of an html element.
    """

    background: Any
    """
    A background view for the application, provided as json description of an html element.
    """


class BrowserAppBundle(BrowserTarget):
    """
    Describes run-time metadata for a front-end application: name, graphics, and how the application can be triggered.
    """

    family: Family = Family.application
    displayName: Optional[str] = None
    """
    Display name of the application, name of the project if not provided.
    """
    execution: Execution = Execution()
    """
    How the application can be triggered.
    """
    graphics: BrowserAppGraphics
    """
    Graphics associated to the application.
    """


BrowserApp = BrowserAppBundle


class MicroService(Target):
    family: str = Family.service


class Pipeline(BaseModel):
    """
    Describes a pipeline.
    """

    target: Target
    """
    The pipeline [target](@yw-nav-class:youwol.app.routers.projects.models_project.Target).
    """

    tags: list[str] = []
    """
    Tags associated to the pipeline.
    """
    description: str = ""
    """
    Description of the pipeline.
    """

    steps: list[PipelineStep]
    """
    The list of steps the pipeline relies on; there is no notion of connection here.
    """

    flows: list[Flow]
    """
    The list of flowcharts the pipeline relies on; this is where the concept of connection appear.
    """
    extends: Optional[str] = None

    dependencies: Callable[["Project", Context], set[str]] = None
    """
    Callback function that returns the list of dependencies name from a
    [project](@yw-nav-class:youwol.app.routers.projects.models_project.Project) (e.g. from `requirements.txt` in python,
    `package.json` in javascript).
    """
    projectName: Callable[[Path], str]
    """
    Callback function that return the name of the project from the path of the project.
    (e.g. from `package.json > name` in javascript).
    """

    projectVersion: Callable[[Path], str]
    """
    Callback function that return the version of the project from the path of the project.
    (e.g. from `package.json > version` in javascript).
    """


class IPipelineFactory(ABC):
    @abstractmethod
    async def get(self, _env: YouwolEnvironment, _context: Context) -> Pipeline:
        return NotImplemented


class Project(BaseModel):
    """
    Describes a project, generated from a folder on the disk and a
    [Pipeline](@yw-nav-class:youwol.app.routers.projects.models_project.Pipeline).
    """

    pipeline: Pipeline
    """
    The pipeline that generated the project.
    """
    path: Path
    """
    Full path of the project on the disk.
    """
    name: str

    publishName: str
    id: str  # base64 encoded Project.name
    version: str
    """
    Version of the project.
    """

    async def get_dependencies(
        self,
        projects: list["Project"],
        recursive: bool,
        context: Context,
        ignore: Optional[list[str]] = None,
    ) -> list["Project"]:
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
    ) -> list[Path]:
        async with context.start(
            action="get_artifact_files", with_attributes={"artifact": artifact_id}
        ) as ctx:
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
    ) -> list[Path]:
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

    def get_flow_steps(self, flow_id: str) -> list[PipelineStep]:
        flow = next(f for f in self.pipeline.flows if f.name == flow_id)
        involved_steps = {step.strip() for b in flow.dag for step in b.split(">")}
        steps = [step for step in self.pipeline.steps if step.id in involved_steps]

        return steps

    def get_downstream_flow_steps(
        self, flow_id: str, from_step_id: str, from_step_included: bool
    ) -> list[PipelineStep]:
        flow = next(f for f in self.pipeline.flows if f.name == flow_id)
        branches = [[step.strip() for step in branch.split(">")] for branch in flow.dag]

        def implementation(from_step_tmp):
            starts = [
                (step, i, branch)
                for branch in branches
                for i, step in enumerate(branch)
                if step == from_step_tmp
            ]
            return {s for step, i, branch in starts for s in branch[i + 1 :]}

        downstream_steps = implementation(from_step_tmp=from_step_id)
        indirect = [implementation(from_step_tmp=s) for s in downstream_steps]
        involved_steps = downstream_steps.union(
            *indirect, {from_step_id} if from_step_included else {}
        )
        steps = [step for step in self.pipeline.steps if step.id in involved_steps]
        return steps

    def get_direct_upstream_steps(
        self, flow_id: str, step_id: str
    ) -> list[PipelineStep]:
        def get_direct_upstream_step_in_branch(branch: list[str]) -> Optional[str]:
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
    """
    Response model after project creation from template.
    """
