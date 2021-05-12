import asyncio
import itertools
import json
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi import Query as RequestQuery
from starlette.requests import Request
from starlette.responses import Response

from .configurations import Configuration, get_configuration
from .models import AssetResponse, NewAssetBody, PostAssetBody, QueryAssetBody
from .utils import (
    to_doc_db_id, access_policy_record_id, ensure_post_permission, format_asset,
    ensure_get_permission, to_snake_case, ensure_delete_permission, format_record_history, format_image, get_thumbnail,
    )
from youwol_utils import (
    User, user_info, get_all_individual_groups, Group, private_group_id, to_group_id,
    generate_headers_downstream, AccessPolicyBody, AccessPolicyResp, is_child_group, ReadPolicyEnum, SharePolicyEnum,
    ancestors_group_id, QueryBody, Query, WhereClause, PermissionsResp, get_leaf_group_ids, FileData, RecordsResponse,
    GetRecordsBody, List, RecordsTable, RecordsKeyspace, RecordsBucket, RecordsDocDb, RecordsStorage,
    )

router = APIRouter()
flatten = itertools.chain.from_iterable


@router.get("/.ambassador-internal/openapi-docs")
async def patch_until_this_call_is_removed():
    return {}


@router.get("/healthz")
async def healthz():
    return {"status": "assets-backend ok"}


@router.get("/user-info",
            response_model=User,
            summary="retrieve user info")
async def get_user_info(request: Request):

    user = user_info(request)
    groups = get_all_individual_groups(user["memberof"])
    groups = [Group(id=private_group_id(user), path="private")] + \
             [Group(id=str(to_group_id(g)), path=g) for g in groups if g]

    return User(name=user['preferred_username'], groups=groups)


@router.put("/assets",
            response_model=AssetResponse,
            summary="new asset")
async def create_asset(
        request: Request,
        body: NewAssetBody,
        configuration: Configuration = Depends(get_configuration)):

    user = user_info(request)
    policy = body.defaultAccessPolicy
    headers = generate_headers_downstream(request.headers)
    asset_id = body.assetId if body.assetId else to_doc_db_id(body.relatedId)
    owning_group = body.groupId or private_group_id(user)
    doc_asset = {
        "asset_id": asset_id,
        "related_id": body.relatedId,
        "group_id": owning_group,
        "name": body.name,
        "description": body.description,
        "kind": body.kind,
        "tags": [], "images": [], "thumbnails": []}

    if policy.read == ReadPolicyEnum.forbidden and policy.share == SharePolicyEnum.forbidden:
        await ensure_post_permission(request=request, doc=doc_asset, configuration=configuration)
        return format_asset(doc_asset, request)

    docdb_access = configuration.doc_db_access_policy
    now = time.time()  # s since epoch (January 1, 1970)
    doc_access_default = {
        "record_id": access_policy_record_id(asset_id, "*"),
        "asset_id": asset_id,
        "related_id": body.relatedId,
        "consumer_group_id": "*",
        "read": body.defaultAccessPolicy.read.value,
        "share": body.defaultAccessPolicy.share.value,
        "parameters": "{}",
        "timestamp": int(now)
        }

    await asyncio.gather(
        ensure_post_permission(request=request, doc=doc_asset, configuration=configuration),
        docdb_access.create_document(doc=doc_access_default, owner=configuration.public_owner, headers=headers))
    return format_asset(doc_asset, request)


@router.post("/assets/{asset_id}",
             response_model=AssetResponse,
             summary="update an asset"
             )
async def post_asset(
        request: Request,
        asset_id: str,
        body: PostAssetBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    docdb_access = configuration.doc_db_access_policy
    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration)

    new_attributes = {to_snake_case(k): v for k, v in body.dict().items() if v is not None}
    if 'group_id' in new_attributes and "/" in new_attributes['group_id']:
        new_attributes['group_id'] = to_group_id(new_attributes['group_id'])

    doc = {**asset, **new_attributes}

    if 'defaultAccessPolicy' in doc:
        #  access data are stored only in access_policy db
        del doc['defaultAccessPolicy']

    await ensure_post_permission(request=request, doc=doc, configuration=configuration)
    if body.defaultAccessPolicy:
        now = time.time()  # s since epoch (January 1, 1970)
        doc_access = {
            "record_id": access_policy_record_id(asset_id, "*"),
            "asset_id": asset_id,
            "related_id": asset['related_id'],
            "consumer_group_id": "*",
            "read": body.defaultAccessPolicy.read.value,
            "share": body.defaultAccessPolicy.share.value,
            "parameters": "{}",
            "timestamp": int(now)
            }
        await docdb_access.create_document(doc=doc_access, owner=configuration.public_owner, headers=headers)

    return format_asset(doc, request)


@router.put("/assets/{asset_id}/access/{group_id}",
            summary="update an asset")
async def put_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        body: AccessPolicyBody,
        configuration: Configuration = Depends(get_configuration)
        ):

    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration)
    headers = generate_headers_downstream(request.headers)
    docdb_access = configuration.doc_db_access_policy
    now = time.time()  # s since epoch (January 1, 1970)
    doc_access = {
        "record_id": access_policy_record_id(asset_id, group_id),
        "asset_id": asset_id,
        "related_id": asset['related_id'],
        "consumer_group_id": group_id,
        "read": body.read.value,
        "share": body.share.value,
        "parameters": json.dumps(body.parameters),
        "timestamp": int(now)
        }
    await docdb_access.create_document(doc=doc_access, owner=configuration.public_owner, headers=headers)

    return {}


@router.delete("/assets/{asset_id}/access/{group_id}", summary="update an asset")
async def delete_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    docdb_access = configuration.doc_db_access_policy
    await docdb_access.delete_document(doc={"asset_id": asset_id, "consumer_group_id":  group_id},
                                       owner=configuration.public_owner,
                                       headers=headers)
    return {}


@router.get("/assets/{asset_id}/access/{group_id}",
            response_model=AccessPolicyResp,
            summary="update an asset")
async def get_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    docdb_access = configuration.doc_db_access_policy
    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope='r', configuration=configuration)
    if is_child_group(child_group_id=group_id, parent_group_id=asset['group_id']):
        return AccessPolicyResp(read=ReadPolicyEnum.owning, parameters={}, share=SharePolicyEnum.authorized,
                                timestamp=None)

    ancestors_groups = [group_id] + ancestors_group_id(group_id)
    bodies_specific = [QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                  WhereClause(column="consumer_group_id", relation="eq", term=group_id)])
        ) for group_id in ancestors_groups]

    query_specific = [docdb_access.query(query_body=body, owner=configuration.public_owner, headers=headers)
                      for body in bodies_specific]

    body_default = QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                  WhereClause(column="consumer_group_id", relation="eq", term="*")])
        )

    query_default = docdb_access.query(query_body=body_default, owner=configuration.public_owner, headers=headers)

    *specifics, default = await asyncio.gather(*query_specific, query_default)
    closed = {"read": "forbidden", "parameters": "{}", "timestamp": -1, "share": "forbidden"}
    documents = list(flatten([s['documents'] for s in specifics])) + default['documents'] + [closed]
    if not documents:
        return AccessPolicyResp(read=ReadPolicyEnum.forbidden, parameters={},
                                share=SharePolicyEnum.forbidden, timestamp=None)

    doc = documents[0]
    return AccessPolicyResp(read=doc["read"], parameters=json.loads(doc["parameters"]),
                            share=doc["share"], timestamp=doc["timestamp"])


def get_permission(write, policies):

    if not policies:
        return PermissionsResp(write=False, read=False, share=False, expiration=None)

    opened = any(policy['read'] == ReadPolicyEnum.authorized for policy in policies)
    share = any(policy['share'] == SharePolicyEnum.authorized for policy in policies)
    if opened:
        return PermissionsResp(write=write, read=True, share=share, expiration=None)

    deadlines = [policy for policy in policies if policy['read'] == ReadPolicyEnum.expiration_date]
    if deadlines:

        expirations = [policy['timestamp'] + json.loads(policy['parameters'])["period"] for policy in deadlines]
        remaining = max(expirations) - int(time.time())
        return PermissionsResp(write=write, read=remaining > 0, share=share, expiration=remaining)

    return PermissionsResp(write=write, read=False, share=False, expiration=None)


@router.get("/assets/{asset_id}/permissions",
            response_model=PermissionsResp,
            summary="permissions of the user on the asset")
async def get_permissions(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)):

    user = user_info(request)
    group_ids = get_leaf_group_ids(user)
    group_ids = list(flatten([[group_id] + ancestors_group_id(group_id) for group_id in group_ids]))
    group_ids = list(set(group_ids))

    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope='r', configuration=configuration)
    #  watch for owner case with read access
    if any([is_child_group(child_group_id=group_id, parent_group_id=asset['group_id'])
            for group_id in group_ids]):
        return PermissionsResp(write=True, read=True, share=True, expiration=None)

    # watch if default policy is sufficient
    docdb_access = configuration.doc_db_access_policy
    headers = generate_headers_downstream(request.headers)
    body_default = QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                  WhereClause(column="consumer_group_id", relation="eq", term="*")])
        )

    default = await docdb_access.query(query_body=body_default, owner=configuration.public_owner, headers=headers)

    if len(default['documents']) > 0 and default['documents'][0]['read'] == ReadPolicyEnum.authorized \
            and default['documents'][0]['share'] == SharePolicyEnum.authorized:
        return PermissionsResp(write=False, read=True, share=True, expiration=None)

    # then gather specific policies for the all the groups the user belongs
    bodies_specific = [QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                  WhereClause(column="consumer_group_id", relation="eq", term=group_id)])
        ) for group_id in group_ids]

    specifics = await asyncio.gather(*[docdb_access.query(query_body=body, owner=configuration.public_owner,
                                                          headers=headers) for body in bodies_specific])
    policies = list(flatten([d["documents"] for d in specifics]))
    permission = get_permission(False, policies)

    return permission


@router.delete("/assets/{asset_id}", summary="delete an asset")
async def delete_asset(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration)
    headers = generate_headers_downstream(request.headers)
    docdb_access = configuration.doc_db_access_policy

    query = QueryBody(
        max_results=1000,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id)])
        )

    _, docs = await asyncio.gather(
        ensure_delete_permission(request=request, asset=asset, configuration=configuration),
        docdb_access.query(query_body=query, owner=configuration.public_owner, headers=headers))

    await asyncio.gather(*[docdb_access.delete_document(doc=d, owner=configuration.public_owner, headers=headers)
                           for d in docs['documents']])
    return {}


@router.post("/query", summary="query assets")
async def query_asset(_request: Request,  _body: QueryAssetBody):
    """
        start_time = time.time()

        docs = await ensure_query_permission(request=request, query=body, scope='r')
        elapsed_time = time.time() - start_time

        return JSONResponse(
            content={"assets": [format_asset(asset, request).dict() for asset in docs]},
            headers={"Server-Timing": f"doc_db;dur={elapsed_time*1000}"})
    """
    raise NotImplementedError()


@router.get("/assets/{asset_id}",
            response_model=AssetResponse,
            summary="return an asset")
async def get_asset(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)):

    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope='r', configuration=configuration)
    return format_asset(asset, request)


@router.put("/raw/access/{related_id}", summary="register access")
async def record_access(
        request: Request,
        related_id: str,
        configuration: Configuration = Depends(get_configuration)
        ):
    """
    WARNING: use 'allow_filtering' => do not use in prod
    Probably need as secondary index on 'related_id'
    """
    headers = generate_headers_downstream(request.headers)
    user = user_info(request)
    doc_db_assets, doc_db_history = configuration.doc_db_asset, configuration.doc_db_access_history

    query = QueryBody(
        max_results=1,
        allow_filtering=True,
        query=Query(where_clause=[WhereClause(column="related_id", relation="eq", term=related_id)])
        )
    asset = await doc_db_assets.query(query_body=query, owner=configuration.public_owner, headers=headers)

    if len(asset["documents"]) == 0:
        raise HTTPException(status_code=404, detail=f"Asset with related_id ${related_id} not found")
    if len(asset["documents"]) > 1:
        raise HTTPException(status_code=404, detail=f"Multiple assets with related_id ${related_id} found")

    asset = asset["documents"][0]
    now = time.time()  # s since epoch (January 1, 1970)
    doc = {"record_id": str(uuid.uuid4()), "asset_id": asset["asset_id"], "related_id": asset["related_id"],
           "username": user['preferred_username'], "timestamp": int(now)}
    await doc_db_history.create_document(doc=doc, owner=configuration.public_owner, headers=headers)

    return doc


@router.get("/raw/access/{asset_id}/query-latest", summary="query latest access record")
async def query_access(
        request: Request,
        asset_id,
        max_count: int = RequestQuery(100, alias="max-count"),
        configuration: Configuration = Depends(get_configuration)):
    """
    WARNING: use 'allow_filtering' => do not use in prod
    Probably need as secondary index on 'related_id'
    """
    headers = generate_headers_downstream(request.headers)
    doc_db_history = configuration.doc_db_access_history

    query = QueryBody(
        max_results=max_count,
        allow_filtering=True,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id)])
        )

    results = await doc_db_history.query(query_body=query, owner=configuration.public_owner, headers=headers)

    return {"records": [format_record_history(r) for r in results["documents"]]}


@router.delete("/raw/access/{asset_id}", summary="clear user access history")
async def clear_asset_history(
        request: Request,
        asset_id,
        count: int = 1000,
        configuration: Configuration = Depends(get_configuration)
        ):
    """
    WARNING: use 'allow_filtering' => do not use in prod
    Probably need as secondary index on 'related_id'
    """
    headers = generate_headers_downstream(request.headers)
    doc_db_history = configuration.doc_db_access_history

    user = user_info(request)
    query = QueryBody(
        max_results=count,
        allow_filtering=True,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                  WhereClause(column="username", relation="eq", term=user["preferred_username"])])
        )

    results = await doc_db_history.query(query_body=query, owner=configuration.public_owner, headers=headers)
    await asyncio.gather(*[
        doc_db_history.delete_document(doc=doc, owner=configuration.public_owner, headers=headers)
        for doc in results["documents"]
        ])
    return {}


@router.post("/assets/{asset_id}/images/{filename}", summary="add an image to asset")
async def post_image(
        request: Request,
        asset_id: str,
        filename: str,
        file: UploadFile = File(...),
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    storage, doc_db = configuration.storage, configuration.doc_db_asset

    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration)

    if [img for img in asset["images"] if img.split('/')[-1] == filename]:
        raise HTTPException(status_code=409, detail=f"image '{filename}' already exist")

    image = await format_image(filename, file)
    thumbnail = get_thumbnail(image, size=(200, 200))

    doc = {**asset, **{
            "images": [*asset["images"], f"/api/assets-backend/assets/{asset_id}/images/{image.name}"],
            "thumbnails": [*asset["thumbnails"], f"/api/assets-backend/assets/{asset_id}/thumbnails/{thumbnail.name}"]}
           }

    await ensure_post_permission(request=request, doc=doc, configuration=configuration)

    post_image_body = FileData(
        objectData=image.content, objectName=Path(asset['kind']) / asset_id / "images" / image.name,
        owner=configuration.public_owner, objectSize=len(image.content), content_type="image/"+image.extension,
        content_encoding=""
        )

    post_thumbnail_body = FileData(
        objectData=thumbnail.content, objectName=Path(asset['kind']) / asset_id / "thumbnails" / thumbnail.name,
        owner=configuration.public_owner, objectSize=len(thumbnail.content), content_type="image/"+thumbnail.extension,
        content_encoding="")

    post_file_bodies = [post_image_body, post_thumbnail_body]

    await asyncio.gather(*[storage.post_object(path=post_file_body.objectName, content=post_file_body.objectData,
                                               owner=post_file_body.owner, content_type=post_file_body.content_type,
                                               headers=headers)
                           for post_file_body in post_file_bodies])
    return {}


@router.delete("/assets/{asset_id}/images/{name}", summary="remove an image")
async def remove_image(
        request: Request,
        asset_id: str,
        name: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    storage, doc_db = configuration.storage, configuration.doc_db_asset

    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration)

    doc = {**asset, **{
            "images": [image for image in asset["images"]
                       if image != str(Path("/api/assets-backend/")/'assets'/asset_id/"images"/name)],
            "thumbnails": [thumbnail for thumbnail in asset["thumbnails"]
                           if thumbnail != str(Path("/api/assets-backend/")/'assets'/asset_id/"thumbnails"/name)]
            }
           }
    await ensure_post_permission(request=request, doc=doc, configuration=configuration)
    await asyncio.gather(storage.delete(Path(asset['kind']) / asset_id / "images" / name,
                                        owner=configuration.public_owner, headers=headers),
                         storage.delete(Path(asset['kind']) / asset_id / "thumbnails" / name,
                                        owner=configuration.public_owner, headers=headers))
    return {}


@router.get("/assets/{asset_id}/{media_type}/{name}", summary="return a media")
async def get_media(
        request: Request,
        asset_id: str,
        media_type: str,
        name: str,
        configuration: Configuration = Depends(get_configuration)
        ):

    headers = generate_headers_downstream(request.headers)
    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="r", configuration=configuration)

    storage = configuration.storage
    path = Path(asset['kind']) / asset_id / media_type / name
    file = await storage.get_bytes(path, owner=configuration.public_owner, headers=headers)
    return Response(content=file, headers={
        "Content-Encoding": "",
        "Content-Type": f"image/{path.suffix[1:]}",
        "cache-control": "public, max-age=31536000"
        })
    # return StreamingResponse(io.BytesIO(file), media_type=f"image/{path.suffix}")


@router.post("/records",
             response_model=RecordsResponse,
             summary="return a media")
async def get_records(
        request: Request,
        body: GetRecordsBody,
        configuration: Configuration = Depends(get_configuration)):

    doc_db = configuration.doc_db_asset
    storage = configuration.storage
    records = await asyncio.gather(*[
        ensure_get_permission(request=request, asset_id=asset_id, scope="r", configuration=configuration)
        for asset_id in body.ids
        ])

    def to_path(media_type: str, urls: List[str], asset) -> List[Path]:
        return [Path(asset['kind'])/asset['asset_id']/media_type/url.split('/')[-1] for url in urls]

    paths_images = [to_path("images", asset["images"], asset) for asset in records]
    paths_images = list(flatten(paths_images))
    paths_thumbnails = [to_path("thumbnails", asset["thumbnails"], asset) for asset in records]
    paths_thumbnails = list(flatten(paths_thumbnails))

    table = RecordsTable(
        id=doc_db.table_name,
        primaryKey=doc_db.table_body.partition_key[0],
        values=body.ids
        )
    keyspace = RecordsKeyspace(
        id=doc_db.keyspace_name,
        groupId=to_group_id(configuration.public_owner),
        tables=[table]
        )

    paths = [str(p) for p in paths_images + paths_thumbnails]
    bucket = RecordsBucket(
        id=storage.bucket_name,
        groupId=to_group_id(configuration.public_owner),
        paths=paths
        )
    response = RecordsResponse(
        docdb=RecordsDocDb(keyspaces=[keyspace]),
        storage=RecordsStorage(buckets=[bucket])
        )

    return response
