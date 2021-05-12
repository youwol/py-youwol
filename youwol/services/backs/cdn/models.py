from pathlib import Path
from typing import List, NamedTuple, Union, Dict, Tuple

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


class FluxPackSummary(BaseModel):
    name: str
    id: str
    description: str
    tags: List[str]
    namespace: str


class ListPacksResponse(BaseModel):
    fluxPacks: List[FluxPackSummary]


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


class SyncResponse(BaseModel):
    filesCount: int
    librariesCount: int
    compressedSize: int
    namespaces: List[str]


class Release(BaseModel):
    version: str
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


class LoadingGraphResponse(BaseModel):
    graphType: str
    definition: List[List[Url]]


class Library(BaseModel):
    name: str
    version: str
    id: str
    namespace: str
    type: str


class LoadingGraphResponseV1(BaseModel):
    graphType: str
    lock: List[Library]
    definition: List[List[Tuple[str, Url]]]


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


LIBRARIES_TABLE = TableBody(
    name='libraries',
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
        Column(name="version_number", type="int"),
        Column(name="path", type="text"),
        Column(name="fingerprint", type="text")
        ],
    partition_key=["library_name"],
    clustering_columns=["version"],
    table_options=TableOptions(
        clustering_order=[OrderingClause(name='version', order='DESC')]
        )
    )
