# standard library
from pathlib import Path

# typing
from typing import Any, NamedTuple, Optional, Union

# third parties
from pydantic import BaseModel
from semantic_version import Version

# Youwol utilities
from youwol.utils.clients.docdb.models import (
    Column,
    OrderingClause,
    TableBody,
    TableOptions,
)


def get_api_key(version: Union[str, Version]):
    parsed = version if isinstance(version, Version) else Version(version)
    if parsed.major != 0:
        return f"{parsed.major}"
    if parsed.minor != 0:
        return f"0{parsed.minor}"
    return f"00{parsed.patch}"


def get_exported_symbol(name: str):
    return exportedSymbols[name] if name in exportedSymbols else name


def patch_loading_graph(loading_graph: dict[str, Any]):
    if loading_graph["graphType"] == "sequential-v1":
        #  add missing apiKey & exportedSymbol in 'lock' attribute
        for lock in loading_graph["lock"]:
            lock["apiKey"] = get_api_key(lock["version"])
            lock["exportedSymbol"] = get_exported_symbol(lock["name"])
        loading_graph["graphType"] = "sequential-v2"


exportedSymbols = {
    "lodash": "_",
    "three": "THREE",
    "typescript": "ts",
    "three-trackballcontrols": "TrackballControls",
    "codemirror": "CodeMirror",
    "highlight.js": "hljs",
    "@pyodide/pyodide": "loadPyodide",
    "plotly.js": "Plotly",
    "plotly.js-gl2d-dist": "Plotly",
    "jquery": "$",
    "popper.js": "Popper",
    "reflect-metadata": "Reflect",
    "js-beautify": "js_beautify",
    "mathjax": "Mathjax",
    "@pyodide/scikit-learn": "sklearn",
    "@pyodide/python-dateutil": "dateutil",
    "@tweenjs/tween.js": "TWEEN",
    "@youwol/potree": "Potree",
}


class FormData(NamedTuple):
    objectName: Union[str, Path]
    objectData: bytes
    objectSize: int
    content_type: str
    content_encoding: str
    owner: Union[str, None]


class PublishResponse(BaseModel):
    name: str
    id: str
    version: str
    fingerprint: str
    compressedSize: int
    url: str


class UploadResponse(BaseModel):
    filesCount: int
    librariesCount: int
    compressedSize: int
    namespace: str


class PublishLibrariesResponse(BaseModel):
    filesCount: int
    librariesCount: int
    compressedSize: int
    namespaces: list[str]


class Release(BaseModel):
    version: str
    version_number: int
    fingerprint: str


class ListVersionsResponse(BaseModel):
    name: str
    versions: list[str]
    namespace: str
    id: str
    releases: list[Release] = []


class ListLibsResponse(BaseModel):
    libraries: list[ListVersionsResponse]


Url = str


class DeleteBody(BaseModel):
    librariesName: list[str]


class DeleteLibraryResponse(BaseModel):
    deletedVersionsCount: int


class LoadingGraphResponse(BaseModel):
    graphType: str
    definition: list[list[Url]]


class Library(BaseModel):
    name: str
    version: str
    id: str
    namespace: str
    type: str
    fingerprint: str
    # exportedSymbol is deprecated, use 'aliases' instead
    exportedSymbol: str
    aliases: list[str]
    apiKey: str


class LoadingGraphResponseV1(BaseModel):
    graphType: str
    lock: list[Library]
    definition: list[
        list[Any]
    ]  # 'Any' is actually Tuple[str, Url], but it leads to 500 when rendering the docs


class DependenciesResponse(BaseModel):
    libraries: dict[str, str]
    loadingGraph: LoadingGraphResponse


class DependenciesResponseV1(BaseModel):
    libraries: dict[str, str]
    loadingGraph: LoadingGraphResponseV1


class DependenciesLatestBody(BaseModel):
    libraries: list[str]


class LibVersionsBody(BaseModel):
    name: str


class LibraryQuery(BaseModel):
    name: str
    version: str


class LibraryResolved(Library):
    dependencies: list[LibraryQuery]
    bundle: str
    exportedSymbol: str
    apiKey: str

    def full_exported_symbol(self):
        return f"{self.exportedSymbol}_APIv{self.apiKey}"


class LoadingGraphBody(BaseModel):
    libraries: Union[list[LibraryQuery], dict[str, str]]
    using: dict[str, str] = {}
    extraIndex: Optional[str]


class LoadingGraphBodyV1(BaseModel):
    libraries: list[LibraryQuery]
    using: dict[str, str] = {}


class FileResponse(BaseModel):
    name: str
    size: int
    encoding: str


class FolderResponse(BaseModel):
    name: str
    path: str
    size: int = -1
    filesCount: int = (
        -1
    )  # prior to 06/07/2022 this property was not computed during publish


class ExplorerResponse(BaseModel):
    # prior to some point, no explorer data were published the default is then returned
    size: int = -1
    filesCount: int = (
        -1
    )  # prior to 06/07/2022 this property was not computed during publish
    files: list[FileResponse] = []
    folders: list[FolderResponse] = []


LIBRARIES_TABLE = TableBody(
    name="libraries",
    version="1.0",
    columns=[
        Column(name="library_id", type="text"),
        Column(name="library_name", type="text"),
        Column(name="namespace", type="text"),
        Column(name="version", type="text"),
        Column(name="type", type="text"),
        Column(name="description", type="text"),
        Column(name="tags", type="list<text>"),
        Column(name="dependencies", type="list<text>"),
        Column(name="bundle_min", type="text"),
        Column(name="bundle", type="text"),
        Column(name="version_number", type="text"),
        Column(name="path", type="text"),
        Column(name="fingerprint", type="text"),
    ],
    partition_key=["library_name"],
    clustering_columns=["version_number"],
    table_options=TableOptions(
        clustering_order=[OrderingClause(name="version_number", order="DESC")]
    ),
)
