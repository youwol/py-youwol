import asyncio
import itertools
import math
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from fastapi import Query as QueryParam
from starlette.responses import Response

from youwol_utils.clients.docdb.models import OrderingClause, QueryBody
from .all_icons_emojipedia import (
    icons_smileys_people, icons_animals, icons_foods, icons_activities, icons_travel,
    icons_objects, icons_symbols, icons_flags,
    )
from .configurations import Configuration, get_configuration

from youwol_utils import (
    User, Request, user_info, get_all_individual_groups, Group, private_group_id, to_group_id,
    generate_headers_downstream, Query, WhereClause, DocDbClient,
    )
from .models import (
    StoryResp, PutStoryBody, GetDocumentResp, GetChildrenResp, PutDocumentBody, DeleteResp,
    PostContentBody, PostDocumentBody
    )
from .utils import (
    query_document, position_start,
    position_next, position_format,
    )

router = APIRouter()
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "stories-backend serving"}


@router.get(
    "/user-info",
    response_model=User,
    summary="retrieve user info")
async def get_user_info(
        request: Request
        ):

    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    groups = [Group(id=private_group_id(user), path="private")] + \
             [Group(id=str(to_group_id(g)), path=g) for g in groups if g]

    return User(name=user['preferred_username'], groups=groups)


@router.put(
    "/stories",
    response_model=StoryResp,
    summary="create a new story")
async def put_story(
        request: Request,
        body: PutStoryBody,
        configuration: Configuration = Depends(get_configuration)
        ):
    user = user_info(request)
    story_id = body.storyId if body.storyId else str(uuid.uuid4())
    headers = generate_headers_downstream(request.headers)
    doc_db_stories = configuration.doc_db_stories
    doc_db_docs = configuration.doc_db_documents
    storage = configuration.storage
    root_doc_id = "root_" + story_id

    await asyncio.gather(
        doc_db_stories.create_document(
            doc={
                "story_id": story_id,
                "authors": [user['sub']],
                "root_document_id": root_doc_id
                },
            owner=Configuration.default_owner,
            headers=headers
            ),
        doc_db_docs.create_document(
            doc={
                "document_id": root_doc_id,
                "parent_document_id": story_id,
                "story_id": story_id,
                "content_id": root_doc_id,
                "title": body.title,
                "position": position_start(),
                "complexity_order": 0,
                },
            owner=Configuration.default_owner,
            headers=headers
            ),
        storage.post_object(
            path=root_doc_id,
            content="You can start writing your story :)",
            content_type=Configuration.text_content_type,
            owner=Configuration.default_owner,
            headers=headers
            )
        )
    return await get_story(request=request, story_id=story_id, configuration=configuration)


@router.get(
    "/stories/{story_id}",
    response_model=StoryResp,
    summary="retrieve a story")
async def get_story(
        request: Request,
        story_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    doc_db_stories = configuration.doc_db_stories
    doc_db_docs = configuration.doc_db_documents
    story, root_doc = await asyncio.gather(
        doc_db_stories.get_document(
            partition_keys={"story_id": story_id},
            clustering_keys={},
            owner=Configuration.default_owner,
            headers=headers
            ),
        doc_db_docs.query(
            query_body=f"parent_document_id={story_id}#1",
            owner=Configuration.default_owner,
            headers=headers
            )
        )
    if not root_doc['documents']:
        raise HTTPException(status_code=500, detail="Can not find root document of story")
    if len(root_doc['documents']) > 1:
        raise HTTPException(status_code=500, detail="Multiple root documents can not exist")

    root_doc = root_doc['documents'][0]

    return StoryResp(
        storyId=story['story_id'],
        title=root_doc['title'],
        authors=story['authors'],
        rootDocumentId=root_doc['document_id']
        )


@router.get(
    "/stories/{story_id}/documents/{document_id}",
    response_model=GetDocumentResp,
    summary="retrieve a document")
async def get_document(
        request: Request,
        document_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    document = await query_document(document_id, configuration, headers)

    return GetDocumentResp(
        storyId=document['story_id'],
        documentId=document['document_id'],
        title=document['title'],
        position=float(document['position']),
        parentDocumentId=document['parent_document_id'],
        contentId=document["content_id"]
        )


@router.get(
    "/stories/{story_id}/contents/{content_id}",
    summary="retrieve a document's content")
async def get_content(
        request: Request,
        content_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    content = await configuration.storage.get_text(path=content_id, owner=Configuration.default_owner, headers=headers)

    return Response(
        content=content,
        headers={
            "Content-Type": Configuration.text_content_type
            }
        )


@router.post(
    "/stories/{story_id}/contents/{content_id}",
    summary="update a document's content")
async def post_content(
        request: Request,
        content_id: str,
        body: PostContentBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    await configuration.storage.post_object(
        path=content_id,
        content=body.content,
        content_type=Configuration.text_content_type,
        owner=Configuration.default_owner,
        headers=headers
        )
    return {}


@router.get(
    "/stories/{story_id}/documents/{document_id}/children",
    response_model=GetChildrenResp,
    summary="retrieve the children's list of a document")
async def get_children(
        request: Request,
        document_id: str,
        from_position: float = QueryParam(0, alias="from-position"),
        count: int = QueryParam(1000),
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    doc_db_docs = configuration.doc_db_documents
    from_position = position_format(from_position)
    query = Query(
        where_clause=[
            WhereClause(column="parent_document_id", relation="eq", term=document_id),
            WhereClause(column="position", relation="geq", term=from_position),
            ]
        )
    documents_resp = await doc_db_docs.query(
        query_body=QueryBody(max_results=count, query=query),
        owner=Configuration.default_owner,
        headers=headers
        )
    documents = [d for d in documents_resp['documents']]

    return GetChildrenResp(
        documents=[GetDocumentResp(
            storyId=d['story_id'],
            documentId=d['document_id'],
            parentDocumentId=d['parent_document_id'],
            title=d['title'],
            position=float(d['position']),
            contentId=d["content_id"]
            ) for d in documents]
        )


@router.put(
    "/stories/{story_id}/documents",
    response_model=GetDocumentResp,
    summary="create a new document")
async def put_document(
        request: Request,
        story_id: str,
        body: PutDocumentBody,
        configuration: Configuration = Depends(get_configuration)
        ):
    document_id = body.documentId if body.documentId else str(uuid.uuid4())
    content_id = document_id
    headers = generate_headers_downstream(request.headers)
    doc_db_docs = configuration.doc_db_documents
    storage = configuration.storage

    query = Query(
        where_clause=[
            WhereClause(column="parent_document_id", relation="eq", term=body.parentDocumentId)
            ],
        ordering_clause=[
            OrderingClause(name="position", order='DESC')
            ]
        )
    documents_resp = await doc_db_docs.query(
            query_body=QueryBody(max_results=1, query=query),
            owner=Configuration.default_owner,
            headers=headers
            )
    order_token = position_start() \
        if not documents_resp['documents'] \
        else position_next(documents_resp['documents'][0]['position'])

    await asyncio.gather(
        doc_db_docs.create_document(
            doc={
                "document_id": document_id,
                "parent_document_id": body.parentDocumentId,
                "story_id": story_id,
                "content_id": content_id,
                "title": body.title,
                "position": order_token,
                "complexity_order": 0,
                },
            owner=Configuration.default_owner,
            headers=headers
            ),
        storage.post_object(
            path=content_id,
            content=body.content,
            content_type=Configuration.text_content_type,
            owner=Configuration.default_owner,
            headers=headers
            )
        )

    return GetDocumentResp(storyId=story_id, documentId=document_id, parentDocumentId=body.parentDocumentId,
                           title=body.title, position=order_token, contentId=content_id)


@router.post(
    "/stories/{story_id}/documents/{document_id}",
    response_model=GetDocumentResp,
    summary="update a document")
async def post_document(
        request: Request,
        document_id: str,
        body: PostDocumentBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    content_id = document_id
    headers = generate_headers_downstream(request.headers)
    doc_db_docs = configuration.doc_db_documents
    storage = configuration.storage

    docs = await doc_db_docs.query(query_body=f"document_id={document_id}#1", owner=configuration.default_owner,
                                   headers=headers)
    document = docs['documents'][0]
    coroutines = [
        doc_db_docs.update_document(
            doc={
                **document,
                **{"title": body.title}
                },
            owner=Configuration.default_owner,
            headers=headers
            )
        ]
    if body.content:
        coroutines.append(
            storage.post_object(
                path=content_id,
                content=body.content,
                content_type=Configuration.text_content_type,
                owner=Configuration.default_owner,
                headers=headers
                )
            )

    await asyncio.gather(*coroutines)
    return await get_document(request=request, document_id=document_id, configuration=configuration)


@router.delete(
    "/stories/{story_id}/documents/{document_id}",
    response_model=DeleteResp,
    summary="delete a document with its children")
async def delete_document(
        request: Request,
        document_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    doc_db_docs = configuration.doc_db_documents
    storage = configuration.storage

    all_children = await get_children_rec(
        document_id=document_id,
        start_index=-math.inf,
        chunk_size=10,
        headers=headers,
        doc_db_docs=doc_db_docs
        )

    docs = await doc_db_docs.query(query_body=f"document_id={document_id}#1", owner=configuration.default_owner,
                                   headers=headers)
    document = docs['documents'][0]

    await asyncio.gather(
        *[
            doc_db_docs.delete_document(doc=doc, owner=configuration.default_owner, headers=headers)
            for doc in [document, *all_children]
            ],
        *[
            storage.delete(path=doc['content_id'], owner=configuration.default_owner, headers=headers)
            for doc in [document, *all_children]
            ]
        )
    return DeleteResp(deletedDocuments=len(all_children) + 1)


@router.delete(
    "/stories/{story_id}",
    response_model=DeleteResp,
    summary="delete a story with its children")
async def delete_story(
        request: Request,
        story_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    doc_db_stories = configuration.doc_db_stories
    story = await get_story(request=request, story_id=story_id, configuration=configuration)
    deleted = await delete_document(request=request, document_id=story.rootDocumentId, configuration=configuration)
    await doc_db_stories.delete_document(doc={'story_id': story.storyId}, owner=configuration.default_owner,
                                         headers=headers)
    return deleted


async def get_children_rec(
        document_id: str,
        start_index,
        chunk_size,
        headers,
        doc_db_docs: DocDbClient
        ) -> List[str]:

    headers = generate_headers_downstream(headers)
    documents_resp = await doc_db_docs.query(
        query_body=f"parent_document_id={document_id},position>={start_index}#{chunk_size}",
        owner=Configuration.default_owner,
        headers=headers
        )
    direct_children = documents_resp["documents"]

    indirect_children = await asyncio.gather(
        *[
            get_children_rec(document_id=d["document_id"], start_index=0, chunk_size=chunk_size, headers=headers,
                             doc_db_docs=doc_db_docs) for d in direct_children
            ]
        )
    indirect_children = itertools.chain.from_iterable(indirect_children)
    if len(direct_children) == chunk_size:
        children_next = await get_children_rec(
            document_id=document_id,
            start_index=direct_children[-1]['order_index'] + 0.5,
            doc_db_docs=doc_db_docs,
            chunk_size=chunk_size,
            headers=headers
            )
        return [*direct_children, *indirect_children, * children_next]

    return [*direct_children, *indirect_children]


@router.get("/emojis/{category}",
            summary="return available emojis",
            )
async def list_emojis(category):

    icons = {
        "smileys_people": icons_smileys_people,
        "animals": icons_animals,
        "foods": icons_foods,
        "activities": icons_activities,
        "travel": icons_travel,
        "objects": icons_objects,
        "symbols": icons_symbols,
        "flags": icons_flags
        }
    return {
        'emojis': [icon[0] for icon in icons[category]]
        }
