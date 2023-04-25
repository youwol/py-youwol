# typing
from typing import Dict, List, Optional

# third parties
from pydantic import BaseModel

# Youwol utilities
from youwol.utils.clients.docdb.models import (
    Column,
    IdentifierSI,
    OrderingClause,
    SecondaryIndex,
    TableBody,
    TableOptions,
)


class PutStoryBody(BaseModel):
    storyId: Optional[str]
    title: str


class PostStoryBody(BaseModel):
    title: str


class GetDocumentResp(BaseModel):
    storyId: str
    documentId: str
    parentDocumentId: str
    title: str
    contentId: str
    position: float


class MoveDocumentResp(BaseModel):
    pass


class MoveDocumentBody(BaseModel):
    parent: str
    position: float


class Content(BaseModel):
    css: str
    html: str
    components: str
    styles: str


class GlobalContent(BaseModel):
    css: str
    javascript: str
    components: str


class PostGlobalContentBody(BaseModel):
    css: Optional[str]
    javascript: Optional[str]
    components: Optional[str]


class GetGlobalContentResp(BaseModel):
    css: str
    javascript: str
    components: str


class GetContentResp(Content):
    pass


class GetChildrenResp(BaseModel):
    documents: List[GetDocumentResp]


class ContentBody(Content):
    pass


class PutDocumentBody(BaseModel):
    title: str
    parentDocumentId: str
    documentId: Optional[str]
    content: Optional[ContentBody]


class PostDocumentBody(BaseModel):
    title: str
    content: Optional[ContentBody]


class PostPluginBody(BaseModel):
    packageName: str


class Package(BaseModel):
    name: str
    version: str


class Library(BaseModel):
    name: str
    version: str
    id: str
    namespace: str
    type: str
    apiKey: str
    exportedSymbol: str


Url = str


class LoadingGraphResponse(BaseModel):
    graphType: str
    lock: List[Library]
    # the innest List should be Tuple[str, Url] => fastapi fails to parse it to create open-api doc
    definition: List[List[List[str]]]


class Requirements(BaseModel):
    plugins: List[str]
    loadingGraph: Optional[LoadingGraphResponse] = None


class PostPluginResponse(BaseModel):
    packageName: str
    version: str
    requirements: Requirements


class UpgradePluginsResponse(BaseModel):
    pluginsUpgraded: Dict[str, str]
    requirements: Requirements


class UpgradePluginsBody(BaseModel):
    pass


class StoryResp(BaseModel):
    storyId: str
    rootDocumentId: str
    title: str
    authors: List[str]
    requirements: Requirements


class DeleteResp(BaseModel):
    deletedDocuments: int


class PostContentBody(Content):
    pass


DOCUMENTS_TABLE = TableBody(
    name="documents",
    version="0.0",
    columns=[
        Column(name="document_id", type="text"),
        Column(name="parent_document_id", type="text"),
        Column(name="story_id", type="text"),
        Column(name="content_id", type="text"),
        Column(name="title", type="text"),
        Column(name="position", type="text"),
        Column(name="complexity_order", type="int"),
    ],
    partition_key=["parent_document_id"],
    clustering_columns=["position"],
    table_options=TableOptions(
        clustering_order=[OrderingClause(name="position", order="ASC")]
    ),
)

DOCUMENTS_TABLE_BY_ID = SecondaryIndex(
    name="document_by_id", identifier=IdentifierSI(column_name="document_id")
)

STORIES_TABLE = TableBody(
    name="stories",
    version="0.0",
    columns=[
        Column(name="story_id", type="text"),
        Column(name="root_document_id", type="text"),
        Column(name="authors", type="list<text>"),
    ],
    partition_key=["story_id"],
    clustering_columns=[],
)
