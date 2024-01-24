# standard library
from collections.abc import Mapping
from enum import Enum
from pathlib import Path

# typing
from typing import Any, Optional

# third parties
from pydantic import BaseModel

# relative
from .models_project import Link, Manifest, PipelineStepStatus, Project

ArtifactId = str
PipelineStepId = str


class Failure(BaseModel):
    path: Path
    failure: str = "generic"
    message: str


class FailurePipelineNotFound(Failure):
    """
    Failure because of a directory not found.
    """

    failure: str = "pipeline_not_found"
    message: str = "Pipeline not found"


class FailureDirectoryNotFound(Failure):
    """
    Failure because of a `yw_pipeline.py` file not found.
    """

    failure: str = "directory_not_found"
    message: str = "Project's directory not found"


class FailureImportException(Failure):
    """
    Failure because of an exception while parsing `yw_pipeline.py`.
    """

    failure: str = "import"
    traceback: str
    exceptionType: str


class ListProjectsResponse(BaseModel):
    projects: list[Project]


class ArtifactResponse(BaseModel):
    """
    Response model for artifact generated during the execution of a pipeline's step.
    """

    id: str
    """
    Id of the artifact.
    """

    path: Path
    """
    Path of the artifact on the PC.
    """

    links: list[Link] = []
    """
    List of associated links.
    """


class ArtifactsResponse(BaseModel):
    """
    Response model for artifacts list.
    """

    artifacts: list[ArtifactResponse]
    """
    List of associated links.
    """


class PipelineStepStatusResponse(BaseModel):
    """
    Response model for the status of a pipeline's step.
    """

    projectId: str
    """
    Id of the project
    """

    flowId: str
    """
    Id of the flow
    """

    stepId: PipelineStepId
    """
    Id of the step
    """

    artifactFolder: Path
    """
    Path on the disk of the folder containing the artifacts
    """

    artifacts: list[ArtifactResponse]
    """
    The list of artifacts.
    """
    manifest: Optional[Manifest] = None
    """
    The manifest of the last execution.
    """

    status: PipelineStepStatus
    """
    The current status of the step.
    """


class PipelineStatusResponse(BaseModel):
    """
    Response model w/ the status of selected steps within a pipeline.
    """

    projectId: str
    """
    Id of the project
    """

    steps: list[PipelineStepStatusResponse]
    """
    Status of requested steps.
    """


class ChildToParentConnections(BaseModel):
    """
    Describe edges from a child to its parents regarding the modelling of dependencies.
    """

    id: str
    """
    ID of the child.
    """

    parentIds: list[str]
    """
    IDs of the parents.
    """


class DependenciesResponse(BaseModel):
    """
    Response model of the dependencies of a target project w/ projects included in the workspace.
    """

    above: list[str]
    """
    Name of the projects that consume the target project
    """

    below: list[str]
    """
    Name of the projects that are consumed by the target project
    """

    dag: list[ChildToParentConnections]
    """
    Full DAG representation of the relationships
    """

    simpleDag: list[ChildToParentConnections]
    """
    Simple DAG representation of the relationships
    """


class ProjectStatusResponse(BaseModel):
    """
    Response model of the status of a project.
    """

    projectId: str
    """
    ID of the project
    """

    projectName: str
    """
    name of the project
    """

    workspaceDependencies: DependenciesResponse
    """
    Its dependencies upon other projects in the workspace.
    """


class CdnVersionResponse(BaseModel):
    """
    Response model of a specific version of a project published within the CDN database.
    """

    name: str
    """
    name of the project
    """

    version: str
    """
    version of the project
    """

    versionNumber: int
    """
    version of the project converted to an integer, preserving ordering w/ semantic versioning.
    """

    filesCount: int
    """
    number of files in the published folder.
    """

    bundleSize: int
    """
    Size of the bundle
    """

    path: Path
    """
    Path on the disk
    """

    namespace: str
    """
    Namespace if any
    """


class CdnResponse(BaseModel):
    """
    Response model of the status of a project within the CDN database.
    """

    name: str
    """
    Name of the project.
    """
    versions: list[CdnVersionResponse]
    """
    List of versions available in the CDN.
    """


class Event(Enum):
    """
    Kind of event emitted by a pipeline's step.
    """

    runStarted = "runStarted"
    """
    specifies that the run has started
    """

    runDone = "runDone"
    """
    specifies that the run has finished
    """

    statusCheckStarted = "statusCheckStarted"
    """
    specifies that the status check has started
    """


class PipelineStepEvent(BaseModel):
    """
    Represents an event associated to a pipeline step.
    """

    projectId: str
    """
    Id of the project.
    """

    flowId: str
    """
    Id of the flow.
    """

    stepId: str
    """
    ID of the step.
    """

    event: Event
    """
    Event description.
    """


class CreateProjectFromTemplateBody(BaseModel):
    """
    Body for the instantiation of a new project template of particular kind.
    """

    type: str
    """
    The type ID of the template (generator) to use, should be referenced within the running configuration in
    [Projects](@yw-nav-class:youwol.app.environment.models.models_config.Projects).
    """

    parameters: dict[str, str]
    """
    The parameters to forward to the associated project generator.
    """


class UpdateConfigurationResponse(BaseModel):
    """
    Response model when a pipeline's step configuration is updated.
    """

    path: Path
    """
    Path of the configuration json file on the disk.
    """

    configuration: Mapping[str, Any]
    """
    Body of the configuration
    """
