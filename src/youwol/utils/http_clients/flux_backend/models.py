# typing
from typing import Optional, Union

# third parties
from pydantic import BaseModel, Field

# Youwol utilities
from youwol.utils.clients.docdb.models import Column, TableBody


class ProjectSnippetDeprecated(BaseModel):
    projectId: str = Field(..., title="projectId")


class ProjectsDeprecated(BaseModel):
    projects: list[ProjectSnippetDeprecated] = Field(..., title="projects")


class NewProjectResponse(BaseModel):
    projectId: str
    libraries: dict[str, str]


class Slot(BaseModel):
    slotId: str
    moduleId: str


class Adaptor(BaseModel):
    mappingFunction: str
    adaptorId: str


class Connection(BaseModel):
    start: Slot
    end: Slot
    adaptor: Optional[Adaptor] = None


class FactoryId(BaseModel):
    module: str
    pack: str


class Module(BaseModel):
    configuration: dict
    moduleId: str
    factoryId: FactoryId


class Plugin(BaseModel):
    configuration: dict
    moduleId: str
    parentModuleId: str
    factoryId: FactoryId


class Workflow(BaseModel):
    modules: list[Module] = []
    connections: list[Connection] = []
    plugins: list[Plugin] = []


class ModuleView(BaseModel):
    moduleId: str
    xWorld: float
    yWorld: float


class ConnectionView(BaseModel):
    connectionId: str
    wireless: bool


class Rendering(BaseModel):
    layout: str
    style: str


class DescriptionBoxProperties(BaseModel):
    color: str


class DescriptionBox(BaseModel):
    properties: DescriptionBoxProperties
    title: str
    descriptionBoxId: str = ""
    descriptionHtml: str
    modulesId: list[str]


class BuilderRendering(BaseModel):
    modulesView: list[ModuleView]
    connectionsView: list[ConnectionView]
    descriptionsBoxes: list[DescriptionBox] = []


class EditMetadata(BaseModel):
    name: Optional[str]
    description: Optional[str]
    libraries: Optional[dict[str, str]]


Url = str


class Library(BaseModel):
    name: str
    version: str
    id: str
    apiKey: str
    exportedSymbol: str


class LoadingGraph(BaseModel):
    graphType: str
    lock: Optional[list[Library]] = None
    definition: Union[list[list[Url]], list[list[list[str]]]]


class Requirements(BaseModel):
    fluxComponents: list[str] = []
    fluxPacks: list[str]
    libraries: dict[str, str]
    loadingGraph: LoadingGraph


class NewProject(BaseModel):
    name: str
    projectId: Optional[str]
    description: str


class Duplicate(BaseModel):
    projectId: str


class ProjectSnippet(BaseModel):
    id: str = Field(..., title="id")
    name: str
    description: str
    fluxPacks: list[str]


class Projects(BaseModel):
    projects: list[ProjectSnippet] = Field(..., title="projects")


class Description(BaseModel):
    name: str
    description: str


class RunnerRendering(BaseModel):
    layout: str
    style: str


class DuplicateProject(BaseModel):
    name: str


class UploadResponse(BaseModel):
    project_id: str


class Project(BaseModel):
    name: str
    schemaVersion: str
    description: str
    requirements: Requirements
    workflow: Workflow
    builderRendering: BuilderRendering
    runnerRendering: RunnerRendering


class Component(BaseModel):
    name: str
    description: str
    scope: str
    fluxPacks: list[str]
    workflow: Workflow
    builderRendering: BuilderRendering
    runnerRendering: Optional[RunnerRendering] = None


class Package(BaseModel):
    name: str
    description: str
    link: str
    tags: list[str]


class Packages(BaseModel):
    projects: list[Package] = Field(..., title="packages")


class ListFiles(BaseModel):
    files: list[str]


class PostAdaptorBody(BaseModel):
    adaptorId: str
    fromModuleFactoryId: str
    toModuleFactoryId: str
    fromModuleSlotId: str
    toModuleSlotId: str
    configuration: dict


class OpenWithDescription(BaseModel):
    match: Union[dict, str]
    parametrized: Union[dict, str]


class GraphicsDescription(BaseModel):
    appIcon: dict
    fileIcon: dict
    background: dict


class ExecutionDescription(BaseModel):
    standalone: bool
    parametrized: list[OpenWithDescription]


class PublishApplicationBody(BaseModel):
    name: str
    displayName: str
    version: str
    execution: ExecutionDescription
    graphics: GraphicsDescription


PROJECTS_TABLE = TableBody(
    name="projects",
    version="0.0",
    columns=[
        Column(name="path", type="text"),
        Column(name="project_id", type="text"),
        Column(name="bucket", type="text"),
        Column(name="description", type="text"),
        Column(name="name", type="text"),
        Column(name="packages", type="list<text>"),
    ],
    partition_key=["project_id"],
    clustering_columns=[],
)

COMPONENTS_TABLE = TableBody(
    name="entities",
    version="0.0",
    columns=[
        Column(name="path", type="text"),
        Column(name="component_id", type="text"),
        Column(name="bucket", type="text"),
        Column(name="description", type="text"),
        Column(name="name", type="text"),
        Column(name="packages", type="list<text>"),
        Column(name="has_view", type="boolean"),
    ],
    partition_key=["component_id"],
    clustering_columns=[],
)


class DeprecatedData(BaseModel):
    rootLayerTree: dict
