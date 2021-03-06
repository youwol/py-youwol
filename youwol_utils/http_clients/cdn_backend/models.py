from pathlib import Path
from typing import List, NamedTuple, Union, Dict, Any

from pydantic import BaseModel

from youwol_utils import TableBody
from youwol_utils.clients.docdb.models import Column, TableOptions, OrderingClause


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
    namespaces: List[str]


class Release(BaseModel):
    version: str
    version_number: int
    fingerprint: str


class ListVersionsResponse(BaseModel):
    name: str
    versions: List[str]
    namespace: str
    id: str
    releases: List[Release] = []


class ListLibsResponse(BaseModel):
    libraries: List[ListVersionsResponse]


Url = str


class DeleteBody(BaseModel):
    librariesName: List[str]


class DeleteLibraryResponse(BaseModel):
    deletedVersionsCount: int


class LoadingGraphResponse(BaseModel):
    graphType: str
    definition: List[List[Url]]


class Library(BaseModel):
    name: str
    version: str
    id: str
    namespace: str
    type: str
    fingerprint: str


class LoadingGraphResponseV1(BaseModel):
    graphType: str
    lock: List[Library]
    definition: List[List[Any]]  # 'Any' is actually Tuple[str, Url], but it leads to 500 when rendering the docs


class DependenciesResponse(BaseModel):
    libraries: Dict[str, str]
    loadingGraph: LoadingGraphResponse


class DependenciesResponseV1(BaseModel):
    libraries: Dict[str, str]
    loadingGraph: LoadingGraphResponseV1


class DependenciesLatestBody(BaseModel):
    libraries: List[str]


class LibVersionsBody(BaseModel):
    name: str


class LoadingGraphBody(BaseModel):
    libraries: Dict[str, str]
    using: Dict[str, str] = {}


class FileResponse(BaseModel):
    name: str
    size: int
    encoding: str


class FolderResponse(BaseModel):
    name: str
    path: str
    size: int = -1
    filesCount: int = -1  # prior to 06/07/2022 this property was not computed during publish


class ExplorerResponse(BaseModel):
    # prior to some point, no explorer data were published the default is then returned
    size: int = -1
    filesCount: int = -1  # prior to 06/07/2022 this property was not computed during publish
    files: List[FileResponse] = []
    folders: List[FolderResponse] = []


LIBRARIES_TABLE = TableBody(
    name='libraries',
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
        Column(name="fingerprint", type="text")
    ],
    partition_key=["library_name"],
    clustering_columns=["version_number"],
    table_options=TableOptions(
        clustering_order=[OrderingClause(name='version_number', order='DESC')]
    )
)
