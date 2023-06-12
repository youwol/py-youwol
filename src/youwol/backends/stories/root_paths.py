# standard library
import asyncio
import functools
import io
import itertools
import tempfile
import uuid
import zipfile

from pathlib import Path

# third parties
from fastapi import APIRouter, Depends, File, HTTPException
from fastapi import Query as QueryParam
from fastapi import UploadFile
from starlette.responses import StreamingResponse

# Youwol backends
from youwol.backends.stories.configurations import (
    Configuration,
    Constants,
    get_configuration,
)
from youwol.backends.stories.utils import (
    create_default_global_contents,
    delete_docdb_docs_from_page,
    delete_from_page,
    format_document_resp,
    get_children_rec,
    get_document_path,
    get_requirements,
    get_story_impl,
    position_format,
    position_next,
    position_start,
    query_document,
    query_story,
    zip_data_filename,
    zip_global_content_filename,
    zip_requirements_filename,
)

# Youwol utilities
from youwol.utils import (
    InvalidInput,
    Query,
    Request,
    WhereClause,
    generate_headers_downstream,
    user_info,
)
from youwol.utils.clients.docdb.models import OrderingClause, QueryBody
from youwol.utils.context import Context
from youwol.utils.http_clients.stories_backend import (
    DeleteResp,
    GetChildrenResp,
    GetContentResp,
    GetDocumentResp,
    GetGlobalContentResp,
    LoadingGraphResponse,
    MoveDocumentBody,
    MoveDocumentResp,
    PostContentBody,
    PostDocumentBody,
    PostGlobalContentBody,
    PostPluginBody,
    PostPluginResponse,
    PostStoryBody,
    PutDocumentBody,
    PutStoryBody,
    Requirements,
    StoryResp,
    UpgradePluginsBody,
    UpgradePluginsResponse,
)
from youwol.utils.utils_paths import extract_zip_file, parse_json, write_json

router = APIRouter(tags=["stories-backend"])
flatten = itertools.chain.from_iterable


@router.get("/healthz")
async def healthz():
    return {"status": "stories-backend serving"}


@router.post(
    "/stories", response_model=StoryResp, summary="publish a story from zip file"
)
async def publish_story(
    request: Request,
    file: UploadFile = File(...),
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(action="publish from zip", request=request) as ctx:
        owner = Constants.default_owner
        doc_db_stories = configuration.doc_db_stories
        doc_db_docs = configuration.doc_db_documents
        storage = configuration.storage

        with tempfile.TemporaryDirectory() as tmp_folder:
            dir_path = Path(tmp_folder)
            zip_path = (dir_path / file.filename).with_suffix(".zip")
            try:
                extract_zip_file(file.file, zip_path=zip_path, dir_path=dir_path)
            except zipfile.BadZipFile as e:
                await ctx.error(
                    f"Extracting zip file failed {e}",
                )
                raise InvalidInput(error="Bad zip file")

            await ctx.info("Zip file extracted successfully")
            data = parse_json(dir_path / zip_data_filename)
            await ctx.info("Story data recovered", data=data)
            story = data["story"]
            story_id = story["story_id"]
            documents = data["documents"]
            docs = await doc_db_stories.query(
                query_body=f"story_id={story_id}#1",
                owner=Constants.default_owner,
                headers=ctx.headers(),
            )
            if docs["documents"]:
                await ctx.info("Story already exist, proceed to its destruction")
                await delete_story(
                    request, story_id=story_id, configuration=configuration
                )
            contents = {
                doc["document_id"]: parse_json(dir_path / (doc["content_id"] + ".json"))
                for doc in documents
            }
            await ctx.info("Story contents recovered", data=contents)
            requirements = parse_json(dir_path / zip_requirements_filename)
            await ctx.info("Story requirements recovered", data=requirements)
            global_content = parse_json(dir_path / zip_global_content_filename)
            await ctx.info("Global contents recovered", data=requirements)
            await asyncio.gather(
                doc_db_stories.create_document(
                    doc=story, owner=owner, headers=ctx.headers()
                ),
                *[
                    doc_db_docs.create_document(
                        doc=doc, owner=owner, headers=ctx.headers()
                    )
                    for doc in documents
                ],
                *[
                    storage.post_json(
                        path=get_document_path(
                            story_id=story_id, document_id=doc["content_id"]
                        ),
                        json=contents[doc["document_id"]],
                        owner=owner,
                        headers=ctx.headers(),
                    )
                    for doc in documents
                ],
                storage.post_json(
                    path=get_document_path(
                        story_id=story_id, document_id="requirements"
                    ),
                    json=requirements,
                    owner=owner,
                    headers=ctx.headers(),
                ),
                storage.post_json(
                    path=get_document_path(
                        story_id=story_id, document_id="global-contents"
                    ),
                    json=global_content,
                    owner=owner,
                    headers=ctx.headers(),
                ),
            )
            return StoryResp(
                storyId=story["story_id"],
                title=next(
                    d
                    for d in documents
                    if d["document_id"] == story["root_document_id"]
                )["title"],
                authors=story["authors"],
                rootDocumentId=story["root_document_id"],
                requirements=Requirements(plugins=[]),
            )


@router.get("/stories/{story_id}/download-zip", summary="download a story as zip file")
async def download_zip(
    request: Request,
    story_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    owner = Constants.default_owner
    doc_db_stories = configuration.doc_db_stories
    doc_db_docs = configuration.doc_db_documents
    storage = configuration.storage

    async with Context.start_ep(
        action="download zip", request=request
    ) as ctx:  # type: Context
        story = await query_story(
            story_id=story_id, doc_db_stories=doc_db_stories, context=ctx
        )
        await ctx.info(text="Story found", data=story)
        documents = await get_children_rec(
            document_id=story["root_document_id"],
            start_index=0,
            chunk_size=10,
            headers=ctx.headers(),
            doc_db_docs=doc_db_docs,
        )
        root_doc = await query_document(
            document_id=story["root_document_id"],
            configuration=configuration,
            headers=ctx.headers(),
        )
        await ctx.info(
            text="Children documents retrieved", data={"count": len(documents)}
        )
        requirements = await get_requirements(
            story_id=story_id, storage=storage, context=ctx
        )
        global_content = await storage.get_json(
            path=get_document_path(story_id=story_id, document_id="global-contents"),
            owner=Constants.default_owner,
            headers=ctx.headers(),
        )
        data = {"story": story, "documents": [root_doc, *documents]}
        with tempfile.TemporaryDirectory() as tmp_folder:
            base_path = Path(tmp_folder)
            write_json(data=data, path=base_path / zip_data_filename)
            write_json(
                data=requirements.dict(), path=base_path / zip_requirements_filename
            )
            write_json(
                data=global_content, path=base_path / zip_global_content_filename
            )
            for doc in data["documents"]:
                storage_path = get_document_path(
                    story_id=story_id, document_id=doc["content_id"]
                )
                content = await storage.get_json(
                    path=storage_path, owner=owner, headers=ctx.headers()
                )
                write_json(content, base_path / f"{doc['content_id']}.json")

            zipper = zipfile.ZipFile(base_path / "story.zip", "w", zipfile.ZIP_DEFLATED)
            all_files = [
                "data.json",
                zip_requirements_filename,
                zip_global_content_filename,
            ] + [f"{doc['content_id']}.json" for doc in data["documents"]]
            for filename in all_files:
                zipper.write(base_path / filename, arcname=filename)
            zipper.close()
            content_bytes = (Path(tmp_folder) / "story.zip").read_bytes()
            return StreamingResponse(
                io.BytesIO(content_bytes), media_type="application/zip"
            )


@router.put("/stories", response_model=StoryResp, summary="create a new story")
async def put_story(
    request: Request,
    body: PutStoryBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:
        user = user_info(request)
        story_id = body.storyId if body.storyId else str(uuid.uuid4())
        doc_db_stories = configuration.doc_db_stories
        doc_db_docs = configuration.doc_db_documents
        storage = configuration.storage
        root_doc_id = "root_" + story_id

        await asyncio.gather(
            doc_db_stories.create_document(
                doc={
                    "story_id": story_id,
                    "authors": [user["sub"]],
                    "root_document_id": root_doc_id,
                },
                owner=Constants.default_owner,
                headers=ctx.headers(),
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
                owner=Constants.default_owner,
                headers=ctx.headers(),
            ),
            storage.post_json(
                path=get_document_path(story_id=story_id, document_id=root_doc_id),
                json=Constants.get_default_doc(root_doc_id).dict(),
                owner=Constants.default_owner,
                headers=ctx.headers(),
            ),
            create_default_global_contents(
                story_id=story_id, configuration=configuration, context=ctx
            ),
            storage.post_json(
                path=get_document_path(story_id=story_id, document_id="requirements"),
                json={
                    "plugins": [],
                    "loadingGraph": {
                        "graphType": "sequential-v2",
                        "lock": [],
                        "definition": [],
                    },
                },
                owner=Constants.default_owner,
                headers=ctx.headers(),
            ),
        )
        return StoryResp(
            storyId=story_id,
            title=body.title,
            authors=[user["sub"]],
            rootDocumentId=root_doc_id,
            requirements=Requirements(plugins=[]),
        )


@router.post(
    "/stories/{story_id}", response_model=StoryResp, summary="update story's metadata"
)
async def post_story(
    request: Request,
    story_id: str,
    body: PostStoryBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        doc_db_stories = configuration.doc_db_stories
        doc_db_docs = configuration.doc_db_documents
        story_resp, requirements = await asyncio.gather(
            doc_db_stories.query(
                query_body=f"story_id={story_id}#1",
                owner=Constants.default_owner,
                headers=ctx.headers(),
            ),
            get_requirements(
                story_id=story_id, storage=configuration.storage, context=ctx
            ),
        )
        story = story_resp["documents"][0]
        docs_resp = await doc_db_docs.query(
            query_body=f"document_id={story['root_document_id']}#1",
            owner=Constants.default_owner,
            headers=ctx.headers(),
        )
        doc = {**docs_resp["documents"][0], **{"title": body.title}}
        await doc_db_docs.update_document(
            doc=doc, owner=Constants.default_owner, headers=ctx.headers()
        )

        return StoryResp(
            storyId=story_id,
            rootDocumentId=story["root_document_id"],
            title=body.title,
            authors=story["authors"],
            requirements=requirements,
        )


@router.get("/stories/{story_id}", response_model=StoryResp, summary="retrieve a story")
async def get_story(
    request: Request,
    story_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        return await get_story_impl(
            story_id=story_id, configuration=configuration, context=ctx
        )


@router.get(
    "/stories/{story_id}/documents/{document_id}",
    response_model=GetDocumentResp,
    summary="retrieve a document",
)
async def get_document(
    request: Request,
    document_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    headers = generate_headers_downstream(request.headers)
    document = await query_document(document_id, configuration, headers)

    return GetDocumentResp(
        storyId=document["story_id"],
        documentId=document["document_id"],
        title=document["title"],
        position=float(document["position"]),
        parentDocumentId=document["parent_document_id"],
        contentId=document["content_id"],
    )


@router.get(
    "/stories/{story_id}/global-contents",
    response_model=GetGlobalContentResp,
    summary="retrieve a document's content",
)
async def get_global_content(
    request: Request,
    story_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        try:
            content = await configuration.storage.get_json(
                path=get_document_path(
                    story_id=story_id, document_id=Constants.global_content_filename
                ),
                owner=Constants.default_owner,
                headers=ctx.headers(),
            )
        except HTTPException as e:
            if e.status_code == 404:
                return GetGlobalContentResp(**Constants.global_default_content.dict())
            raise e

        return GetGlobalContentResp(**content)


@router.post(
    "/stories/{story_id}/global-contents", summary="retrieve a document's content"
)
async def post_global_content(
    request: Request,
    story_id: str,
    body: PostGlobalContentBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        actual_content = await get_global_content(
            request=request, story_id=story_id, configuration=configuration
        )
        await configuration.storage.post_json(
            path=get_document_path(
                story_id=story_id, document_id=Constants.global_content_filename
            ),
            json={
                **actual_content.dict(),
                **{k: v for k, v in body.dict().items() if v},
            },
            owner=Constants.default_owner,
            headers=ctx.headers(),
        )
        return {}


@router.get(
    "/stories/{story_id}/contents/{content_id}",
    response_model=GetContentResp,
    summary="retrieve a document's content",
)
async def get_content(
    request: Request,
    story_id: str,
    content_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    headers = generate_headers_downstream(request.headers)
    content = await configuration.storage.get_json(
        path=get_document_path(story_id=story_id, document_id=content_id),
        owner=Constants.default_owner,
        headers=headers,
    )

    return GetContentResp(**content)


@router.post(
    "/stories/{story_id}/contents/{content_id}", summary="update a document's content"
)
async def post_content(
    request: Request,
    story_id: str,
    content_id: str,
    body: PostContentBody,
    configuration: Configuration = Depends(get_configuration),
):
    headers = generate_headers_downstream(request.headers)
    await configuration.storage.post_json(
        path=get_document_path(story_id=story_id, document_id=content_id),
        json=body.dict(),
        owner=Constants.default_owner,
        headers=headers,
    )
    return {}


@router.get(
    "/stories/{story_id}/documents/{document_id}/children",
    response_model=GetChildrenResp,
    summary="retrieve the children's list of a document",
)
async def get_children(
    request: Request,
    document_id: str,
    from_position: float = QueryParam(0, alias="from-position"),
    count: int = QueryParam(1000),
    configuration: Configuration = Depends(get_configuration),
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
        owner=Constants.default_owner,
        headers=headers,
    )
    documents = list(documents_resp["documents"])

    return GetChildrenResp(
        documents=[
            GetDocumentResp(
                storyId=d["story_id"],
                documentId=d["document_id"],
                parentDocumentId=d["parent_document_id"],
                title=d["title"],
                position=float(d["position"]),
                contentId=d["content_id"],
            )
            for d in documents
        ]
    )


@router.put(
    "/stories/{story_id}/documents",
    response_model=GetDocumentResp,
    summary="create a new document",
)
async def put_document(
    request: Request,
    story_id: str,
    body: PutDocumentBody,
    configuration: Configuration = Depends(get_configuration),
):
    document_id = body.documentId if body.documentId else str(uuid.uuid4())
    content_id = document_id
    headers = generate_headers_downstream(request.headers)
    doc_db_docs = configuration.doc_db_documents
    storage = configuration.storage

    query = Query(
        where_clause=[
            WhereClause(
                column="parent_document_id", relation="eq", term=body.parentDocumentId
            )
        ],
        ordering_clause=[OrderingClause(name="position", order="DESC")],
    )
    documents_resp = await doc_db_docs.query(
        query_body=QueryBody(max_results=1, query=query),
        owner=Constants.default_owner,
        headers=headers,
    )
    order_token = (
        position_start()
        if not documents_resp["documents"]
        else position_next(documents_resp["documents"][0]["position"])
    )

    doc = {
        "document_id": document_id,
        "parent_document_id": body.parentDocumentId,
        "story_id": story_id,
        "content_id": content_id,
        "title": body.title,
        "position": order_token,
        "complexity_order": 0,
    }
    content = body.content or Constants.get_default_doc(document_id)
    await asyncio.gather(
        doc_db_docs.create_document(
            doc=doc, owner=Constants.default_owner, headers=headers
        ),
        storage.post_json(
            path=get_document_path(story_id=story_id, document_id=content_id),
            json=content.dict(),
            owner=Constants.default_owner,
            headers=headers,
        ),
    )

    return format_document_resp(doc)


@router.post(
    "/stories/{story_id}/documents/{document_id}",
    response_model=GetDocumentResp,
    summary="update a document",
)
async def post_document(
    request: Request,
    story_id: str,
    document_id: str,
    body: PostDocumentBody,
    configuration: Configuration = Depends(get_configuration),
):
    content_id = document_id
    headers = generate_headers_downstream(request.headers)
    doc_db_docs = configuration.doc_db_documents
    storage = configuration.storage

    docs = await doc_db_docs.query(
        query_body=f"document_id={document_id}#1",
        owner=Constants.default_owner,
        headers=headers,
    )
    document = docs["documents"][0]
    doc = {**document, **{"title": body.title}}
    coroutines = [
        doc_db_docs.update_document(
            doc=doc, owner=Constants.default_owner, headers=headers
        )
    ]
    if body.content:
        coroutines.append(
            storage.post_json(
                path=get_document_path(story_id=story_id, document_id=content_id),
                json=body.content.dict(),
                owner=Constants.default_owner,
                headers=headers,
            )
        )

    await asyncio.gather(*coroutines)
    return format_document_resp(doc)


@router.post(
    "/stories/{story_id}/documents/{document_id}/move",
    response_model=MoveDocumentResp,
    summary="update a document",
)
async def move_document(
    request: Request,
    document_id: str,
    body: MoveDocumentBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        doc_db_docs = configuration.doc_db_documents
        docs = await doc_db_docs.query(
            query_body=f"document_id={document_id}#1",
            owner=Constants.default_owner,
            headers=ctx.headers(),
        )
        doc = docs["documents"][0]
        await doc_db_docs.delete_document(
            doc=doc, owner=Constants.default_owner, headers=ctx.headers()
        )
        doc["parent_document_id"] = body.parent
        doc["position"] = str(body.position)
        await doc_db_docs.create_document(
            doc=doc, owner=Constants.default_owner, headers=ctx.headers()
        )
        return MoveDocumentResp()


@router.delete(
    "/stories/{story_id}/documents/{document_id}",
    response_model=DeleteResp,
    summary="delete a document with its children",
)
async def delete_document(
    request: Request,
    story_id: str,
    document_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request) as ctx:  # type: Context
        return await delete_from_page(
            story_id=story_id,
            document_id=document_id,
            configuration=configuration,
            context=ctx,
        )


@router.delete(
    "/stories/{story_id}",
    response_model=DeleteResp,
    summary="delete a story with its children",
)
async def delete_story(
    request: Request,
    story_id: str,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(request=request, with_labels=["plugin"]) as ctx:
        headers = ctx.headers()
        doc_db_stories = configuration.doc_db_stories
        storage = configuration.storage
        story = await get_story_impl(
            story_id=story_id, configuration=configuration, context=ctx
        )
        deleted_docs, _, _ = await asyncio.gather(
            delete_docdb_docs_from_page(
                document_id=story.rootDocumentId,
                configuration=configuration,
                context=ctx,
            ),
            doc_db_stories.delete_document(
                doc={"story_id": story.storyId},
                owner=Constants.default_owner,
                headers=headers,
            ),
            storage.delete_group(
                prefix=story_id, owner=Constants.default_owner, headers=headers
            ),
        )

        return DeleteResp(deletedDocuments=len(deleted_docs))


@router.post(
    "/stories/{story_id}/plugins",
    response_model=PostPluginResponse,
    summary="update a document",
)
async def add_plugin(
    request: Request,
    story_id: str,
    body: PostPluginBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_labels=["plugin"]
    ) as ctx:  # type: Context
        storage = configuration.storage
        requirements = await get_requirements(
            story_id=story_id, storage=storage, context=ctx
        )
        if body.packageName in requirements.plugins:
            return PostPluginResponse(
                packageName=body.packageName,
                version=next(
                    lib.version
                    for lib in requirements.loadingGraph.lock
                    if lib.name == body.packageName
                ),
                requirements=requirements,
            )

        await ctx.info("Initial requirements", data=requirements)
        libraries = (
            {}
            if not requirements.loadingGraph
            else {lib.name: lib.version for lib in requirements.loadingGraph.lock}
        )
        libraries[body.packageName] = "latest"

        assets_gtw = configuration.assets_gtw_client
        loading_graph = await assets_gtw.get_cdn_backend_router().query_loading_graph(
            body={"libraries": libraries}, headers=ctx.headers()
        )

        new_requirements = Requirements(
            plugins=[*requirements.plugins, body.packageName],
            loadingGraph=LoadingGraphResponse(**loading_graph),
        )
        await storage.post_json(
            path=get_document_path(story_id=story_id, document_id="requirements"),
            json=new_requirements.dict(),
            owner=Constants.default_owner,
            headers=ctx.headers(),
        )
        return PostPluginResponse(
            packageName=body.packageName,
            version=next(
                lib.version
                for lib in new_requirements.loadingGraph.lock
                if lib.name == body.packageName
            ),
            requirements=new_requirements,
        )


@router.post(
    "/stories/{story_id}/plugins/upgrade",
    response_model=UpgradePluginsResponse,
    summary="update a document",
)
async def upgrade_plugins(
    request: Request,
    story_id: str,
    body: UpgradePluginsBody,
    configuration: Configuration = Depends(get_configuration),
):
    async with Context.start_ep(
        request=request, with_labels=["plugin"]
    ) as ctx:  # type: Context
        await ctx.info("request's body", data={"body": body})
        storage = configuration.storage
        requirements = await get_requirements(
            story_id=story_id, storage=storage, context=ctx
        )
        await ctx.info("Initial requirements", data=requirements)
        if not requirements.plugins:
            return
        body = {
            "libraries": functools.reduce(
                lambda acc, e: {**acc, e: "x"}, requirements.plugins, {}
            )
        }
        assets_gtw = configuration.assets_gtw_client
        loading_graph = await assets_gtw.get_cdn_backend_router().query_loading_graph(
            body=body, headers=ctx.headers()
        )

        new_requirements = Requirements(
            plugins=[*requirements.plugins],
            loadingGraph=LoadingGraphResponse(**loading_graph),
        )
        upgraded_plugins = [
            lib
            for lib in new_requirements.loadingGraph.lock
            if lib.name in requirements.plugins
        ]
        upgraded_plugins = functools.reduce(
            lambda acc, e: {**acc, e.name: e.version}, upgraded_plugins, {}
        )
        await storage.post_json(
            path=get_document_path(story_id=story_id, document_id="requirements"),
            json=new_requirements.dict(),
            owner=Constants.default_owner,
            headers=ctx.headers(),
        )
        return UpgradePluginsResponse(
            pluginsUpgraded=upgraded_plugins, requirements=new_requirements
        )
