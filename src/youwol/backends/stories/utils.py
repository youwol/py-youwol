# standard library
import asyncio
import itertools
import math
import time

# typing
from typing import Any, Dict, List

# third parties
from fastapi import HTTPException

# Youwol backends
from youwol.backends.stories.configurations import Configuration, Constants

# Youwol utilities
from youwol.utils import (
    DocDbClient,
    QueryIndexException,
    StorageClient,
    generate_headers_downstream,
    log_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.cdn_backend import patch_loading_graph
from youwol.utils.http_clients.stories_backend import (
    DeleteResp,
    GetDocumentResp,
    Requirements,
    StoryResp,
)

zip_data_filename = "data.json"
zip_requirements_filename = "requirements.json"
zip_global_content_filename = "global-contents.json"


async def init_resources(config: Configuration):
    log_info("Ensure database resources")
    headers = config.admin_headers or {}

    log_info("Successfully retrieved authorization for resources creation")
    await asyncio.gather(
        config.doc_db_stories.ensure_table(headers=headers),
        config.doc_db_documents.ensure_table(headers=headers),
        config.storage.ensure_bucket(headers=headers),
    )
    log_info("resources initialization done")


async def query_story(story_id: str, doc_db_stories: DocDbClient, context: Context):
    docs = await doc_db_stories.query(
        query_body=f"story_id={story_id}#1",
        owner=Constants.default_owner,
        headers=context.headers(),
    )
    if not docs:
        raise QueryIndexException(
            query=f"story_id={story_id}#1", error="No document found"
        )
    return docs["documents"][0]


async def query_document(document_id: str, configuration: Configuration, headers):
    docs = await configuration.doc_db_documents.query(
        query_body=f"document_id={document_id}#1",
        owner=Constants.default_owner,
        headers=headers,
    )
    if not docs["documents"]:
        raise QueryIndexException(
            query="document_id={document_id}#1", error="No document found"
        )
    return docs["documents"][0]


def position_start():
    t = time.time()
    delta = t - math.floor(t)
    return position_format(5e5 + delta)


def position_next(index: str):
    t = time.time()
    delta = t - math.floor(t)
    return position_format(math.floor(float(index)) + 1 + delta)


def position_format(index: float):
    decimal = f"{index:.6f}"
    return (6 - len(decimal.split(".")[0])) * "0" + decimal


def format_document_resp(docdb_doc: Dict[str, str]):
    return GetDocumentResp(
        documentId=docdb_doc["document_id"],
        parentDocumentId=docdb_doc["parent_document_id"],
        storyId=docdb_doc["story_id"],
        title=docdb_doc["title"],
        contentId=docdb_doc["content_id"],
        position=float(docdb_doc["position"]),
    )


async def get_requirements(
    story_id: str, storage: StorageClient, context: Context
) -> Requirements:
    requirements_path = get_document_path(story_id=story_id, document_id="requirements")
    try:
        req_json = await storage.get_json(
            path=requirements_path,
            owner=Constants.default_owner,
            headers=context.headers(),
        )
        if req_json["loadingGraph"]["graphType"] != "sequential-v2":
            patch_loading_graph(req_json["loadingGraph"])
        return Requirements(**req_json)
    except HTTPException as e:
        if e.status_code != 404:
            raise e
        return Requirements(plugins=[])


def get_document_path(story_id: str, document_id: str):
    return f"{story_id}/{document_id}.json"


async def create_default_global_contents(
    story_id: str, configuration: Configuration, context: Context
):
    await configuration.storage.post_json(
        path=get_document_path(
            story_id=story_id, document_id=Constants.global_content_filename
        ),
        json=Constants.global_default_content.dict(),
        owner=Constants.default_owner,
        headers=context.headers(),
    )


async def create_global_contents_if_needed(
    story_id: str, configuration: Configuration, context: Context
):
    try:
        await configuration.storage.get_json(
            path=get_document_path(
                story_id=story_id, document_id=Constants.global_content_filename
            ),
            owner=Constants.default_owner,
            headers=context.headers(),
        )
    except HTTPException as e:
        if e.status_code == 404:
            await context.info(
                "Global content does not exist, create it",
                labels=["Backward compatibility"],
            )
            await create_default_global_contents(
                story_id=story_id, configuration=configuration, context=context
            )
            return
        raise e


async def get_story_impl(story_id: str, configuration: Configuration, context: Context):
    async with context.start(action="get_story_impl") as ctx:  # type: Context
        doc_db_stories = configuration.doc_db_stories
        doc_db_docs = configuration.doc_db_documents
        story, root_doc, requirements = await asyncio.gather(
            doc_db_stories.get_document(
                partition_keys={"story_id": story_id},
                clustering_keys={},
                owner=Constants.default_owner,
                headers=ctx.headers(),
            ),
            doc_db_docs.query(
                query_body=f"parent_document_id={story_id}#1",
                owner=Constants.default_owner,
                headers=ctx.headers(),
            ),
            get_requirements(
                story_id=story_id, storage=configuration.storage, context=ctx
            ),
        )
        if not root_doc["documents"]:
            raise HTTPException(
                status_code=500, detail="Can not find root document of story"
            )
        if len(root_doc["documents"]) > 1:
            raise HTTPException(
                status_code=500, detail="Multiple root documents can not exist"
            )

        root_doc = root_doc["documents"][0]
        await create_global_contents_if_needed(
            story_id=story_id, configuration=configuration, context=ctx
        )
        return StoryResp(
            storyId=story["story_id"],
            title=root_doc["title"],
            authors=story["authors"],
            rootDocumentId=root_doc["document_id"],
            requirements=requirements,
        )


async def get_children_rec(
    document_id: str, start_index, chunk_size, headers, doc_db_docs: DocDbClient
) -> List[Dict[str, Any]]:
    headers = generate_headers_downstream(headers)
    documents_resp = await doc_db_docs.query(
        query_body=f"parent_document_id={document_id},position>={start_index}#{chunk_size}",
        owner=Constants.default_owner,
        headers=headers,
    )
    direct_children = documents_resp["documents"]

    indirect_children = await asyncio.gather(
        *[
            get_children_rec(
                document_id=d["document_id"],
                start_index=0,
                chunk_size=chunk_size,
                headers=headers,
                doc_db_docs=doc_db_docs,
            )
            for d in direct_children
        ]
    )
    indirect_children = itertools.chain.from_iterable(indirect_children)
    if len(direct_children) == chunk_size:
        children_next = await get_children_rec(
            document_id=document_id,
            start_index=direct_children[-1]["order_index"] + 0.5,
            doc_db_docs=doc_db_docs,
            chunk_size=chunk_size,
            headers=headers,
        )
        return [*direct_children, *indirect_children, *children_next]

    return [*direct_children, *indirect_children]


async def delete_docdb_docs_from_page(
    document_id: str, configuration: Configuration, context: Context
):
    async with context.start(action="delete_document_impl") as ctx:  # type: Context
        headers = ctx.headers()
        doc_db_docs = configuration.doc_db_documents
        all_children = await get_children_rec(
            document_id=document_id,
            start_index=-math.inf,
            chunk_size=10,
            headers=headers,
            doc_db_docs=doc_db_docs,
        )

        docs = await doc_db_docs.query(
            query_body=f"document_id={document_id}#1",
            owner=Constants.default_owner,
            headers=headers,
        )
        document = docs["documents"][0]
        all_docs = [document, *all_children]
        await asyncio.gather(
            *[
                doc_db_docs.delete_document(
                    doc=doc, owner=Constants.default_owner, headers=headers
                )
                for doc in all_docs
            ]
        )
        return all_docs


async def delete_from_page(
    story_id: str, document_id: str, configuration: Configuration, context: Context
):
    async with context.start(action="delete_document_impl") as ctx:  # type: Context
        headers = ctx.headers()
        storage = configuration.storage

        deleted_docs = await delete_docdb_docs_from_page(
            document_id=document_id, configuration=configuration, context=ctx
        )

        await asyncio.gather(
            *[
                storage.delete(
                    path=get_document_path(
                        story_id=story_id, document_id=doc["content_id"]
                    ),
                    owner=Constants.default_owner,
                    headers=headers,
                )
                for doc in deleted_docs
            ]
        )
        return DeleteResp(deletedDocuments=len(deleted_docs))
