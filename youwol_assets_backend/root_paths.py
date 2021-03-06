import asyncio
import itertools
import json
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi import Query as RequestQuery
from starlette.requests import Request
from starlette.responses import Response

from youwol_utils import (
    user_info, private_group_id, to_group_id, is_child_group,
    ancestors_group_id, QueryBody, Query, WhereClause, get_leaf_group_ids, FileData, to_group_scope,
    QueryIndexException
)
from youwol_assets_backend.configurations import Configuration, get_configuration, Constants
from youwol_utils.context import Context
from youwol_utils.http_clients.assets_backend import AssetResponse, NewAssetBody, PostAssetBody, SharePolicyEnum, \
    ReadPolicyEnum, AccessPolicyBody, AccessPolicyResp, PermissionsResp, HealthzResponse, AccessInfoResp,\
    ConsumerInfo, OwningGroup, OwnerInfo, ExposingGroup
from .utils import (
    to_doc_db_id, access_policy_record_id, ensure_post_permission, format_asset,
    ensure_get_permission, to_snake_case, ensure_delete_permission, format_record_history, format_image, get_thumbnail,
    format_policy,
)

router = APIRouter(tags=["assets-backend"])
flatten = itertools.chain.from_iterable


@router.get(
    "/healthz",
    response_model=HealthzResponse
)
async def healthz():
    return HealthzResponse()


@router.put(
    "/assets",
    response_model=AssetResponse,
    summary="new asset"
)
async def create_asset(
        request: Request,
        body: NewAssetBody,
        configuration: Configuration = Depends(get_configuration)):

    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        user = user_info(request)
        policy = body.defaultAccessPolicy
        asset_id = body.assetId if body.assetId else to_doc_db_id(body.rawId)
        owning_group = body.groupId or private_group_id(user)
        doc_asset = {
            "asset_id": asset_id,
            "related_id": body.rawId,
            "group_id": owning_group,
            "name": body.name,
            "description": body.description,
            "kind": body.kind,
            "tags": body.tags,
            "images": [],
            "thumbnails": []
        }
        await ensure_post_permission(request=request, doc=doc_asset, configuration=configuration, context=ctx)
        if policy.read == ReadPolicyEnum.forbidden and policy.share == SharePolicyEnum.forbidden:
            return format_asset(doc_asset, request)

        docdb_access = configuration.doc_db_access_policy
        now = time.time()  # s since epoch (January 1, 1970)
        doc_access_default = {
            "record_id": access_policy_record_id(asset_id, "*"),
            "asset_id": asset_id,
            "related_id": body.rawId,
            "consumer_group_id": "*",
            "read": body.defaultAccessPolicy.read.value,
            "share": body.defaultAccessPolicy.share.value,
            "parameters": "{}",
            "timestamp": int(now)
        }

        await docdb_access.create_document(doc=doc_access_default, owner=Constants.public_owner, headers=ctx.headers())

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
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        docdb_access = configuration.doc_db_access_policy
        asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration,
                                            context=ctx)

        new_attributes = {to_snake_case(k): v for k, v in body.dict().items() if v is not None}
        if 'group_id' in new_attributes and "/" in new_attributes['group_id']:
            new_attributes['group_id'] = to_group_id(new_attributes['group_id'])

        doc = {**asset, **new_attributes}

        if 'defaultAccessPolicy' in doc:
            #  access data are stored only in access_policy db
            del doc['defaultAccessPolicy']

        await ensure_post_permission(request=request, doc=doc, configuration=configuration, context=ctx)
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
            await docdb_access.create_document(doc=doc_access, owner=Constants.public_owner, headers=ctx.headers())

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
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration,
                                            context=ctx)
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
        await docdb_access.create_document(doc=doc_access, owner=Constants.public_owner, headers=ctx.headers())

        return {}


@router.delete("/assets/{asset_id}/access/{group_id}", summary="update an asset")
async def delete_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        docdb_access = configuration.doc_db_access_policy
        await docdb_access.delete_document(doc={"asset_id": asset_id, "consumer_group_id": group_id},
                                           owner=Constants.public_owner,
                                           headers=ctx.headers())
        return {}


@router.get("/assets/{asset_id}/access/{group_id}",
            response_model=AccessPolicyResp,
            summary="update an asset")
async def get_access_policy(
        request: Request,
        asset_id: str,
        group_id: str,
        include_inherited: bool = RequestQuery(True, alias="include-inherited"),
        configuration: Configuration = Depends(get_configuration)
):
    def query_body(for_group_id: str):
        return QueryBody(
            max_results=1,
            query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                      WhereClause(column="consumer_group_id", relation="eq", term=for_group_id)])
        )

    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        docdb_access = configuration.doc_db_access_policy

        if not include_inherited:
            query_specific = query_body(for_group_id=group_id)
            resp = await docdb_access.query(query_body=query_specific, owner=Constants.public_owner,
                                            headers=ctx.headers())
            if not resp["documents"]:
                raise QueryIndexException(query="docdb_access@[asset_id,group_id]",
                                          error={"reason": "no record found", "assetId": asset_id, "groupId": group_id})
            doc = resp["documents"][0]
            return AccessPolicyResp(read=ReadPolicyEnum[doc["read"]], parameters=json.loads(doc["parameters"]),
                                    share=SharePolicyEnum[doc["share"]], timestamp=doc["timestamp"])

        asset = await ensure_get_permission(request=request, asset_id=asset_id, scope='r', configuration=configuration,
                                            context=ctx)
        if is_child_group(child_group_id=group_id, parent_group_id=asset['group_id']):
            return AccessPolicyResp(read=ReadPolicyEnum.owning, parameters={}, share=SharePolicyEnum.authorized,
                                    timestamp=None)

        ancestors_groups = [group_id] + ancestors_group_id(group_id)
        bodies_specific = [query_body(for_group_id=for_group_id) for for_group_id in ancestors_groups]

        query_specific = [docdb_access.query(query_body=body, owner=Constants.public_owner, headers=ctx.headers())
                          for body in bodies_specific]

        body_default = query_body(for_group_id="*")

        query_default = docdb_access.query(query_body=body_default, owner=Constants.public_owner, headers=ctx.headers())

        *specifics, default = await asyncio.gather(*query_specific, query_default)
        closed = {"read": "forbidden", "parameters": "{}", "timestamp": -1, "share": "forbidden"}
        documents = list(flatten([s['documents'] for s in specifics])) + default['documents'] + [closed]
        if not documents:
            return AccessPolicyResp(read=ReadPolicyEnum.forbidden, parameters={},
                                    share=SharePolicyEnum.forbidden, timestamp=None)

        doc = documents[0]
        return AccessPolicyResp(read=ReadPolicyEnum[doc["read"]], parameters=json.loads(doc["parameters"]),
                                share=SharePolicyEnum[doc["share"]], timestamp=doc["timestamp"])


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


async def get_permissions_implementation(
        request: Request,
        asset_id: str,
        configuration: Configuration,
        context: Context
) -> PermissionsResp:

    user = user_info(request)
    group_ids = get_leaf_group_ids(user)
    group_ids = list(flatten([[group_id] + ancestors_group_id(group_id) for group_id in group_ids]))
    group_ids = list(set(group_ids))

    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope='r', configuration=configuration,
                                        context=context)
    #  watch for owner case with read access
    if any([is_child_group(child_group_id=group_id, parent_group_id=asset['group_id'])
            for group_id in group_ids]):
        return PermissionsResp(write=True, read=True, share=True, expiration=None)

    # watch if default policy is sufficient
    docdb_access = configuration.doc_db_access_policy

    body_default = QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                  WhereClause(column="consumer_group_id", relation="eq", term="*")])
    )

    default = await docdb_access.query(query_body=body_default, owner=Constants.public_owner, headers=context.headers())

    if len(default['documents']) > 0 and default['documents'][0]['read'] == ReadPolicyEnum.authorized \
            and default['documents'][0]['share'] == SharePolicyEnum.authorized:
        return PermissionsResp(write=False, read=True, share=True, expiration=None)

    # then gather specific policies for the all the groups the user belongs
    bodies_specific = [QueryBody(
        max_results=1,
        query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                  WhereClause(column="consumer_group_id", relation="eq", term=group_id)])
    ) for group_id in group_ids]

    specifics = await asyncio.gather(*[docdb_access.query(query_body=body, owner=Constants.public_owner,
                                                          headers=context.headers()) for body in bodies_specific])
    policies = list(flatten([d["documents"] for d in specifics]))
    permission = get_permission(False, policies)

    return permission


@router.get(
    "/assets/{asset_id}/permissions",
    response_model=PermissionsResp,
    summary="permissions of the user on the asset"
)
async def get_permissions(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context
        return await get_permissions_implementation(request=request, asset_id=asset_id, configuration=configuration,
                                                    context=ctx)


@router.get("/assets/{asset_id}/access-info",
            response_model=AccessInfoResp,
            summary="get asset info w/ access")
async def access_info(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    response = Optional[AccessInfoResp]
    max_policies_count = 1000
    async with Context.start_ep(
            request=request,
            response=lambda: response,
            with_attributes={"asset_id": asset_id}
    ) as ctx:
        docdb_access = configuration.doc_db_access_policy
        body_default = QueryBody(
            max_results=max_policies_count,
            query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id)])
        )

        policies = await docdb_access.query(query_body=body_default, owner=Constants.public_owner,
                                            headers=ctx.headers())
        if len(policies['documents']) > max_policies_count:
            raise QueryIndexException(query="access_policy, query policies by asset_id",
                                      error=f"Maximum expected count reached {max_policies_count}")

        asset, permissions = await asyncio.gather(
            get_asset_implementation(request=request, asset_id=asset_id, configuration=configuration, context=ctx),
            get_permissions_implementation(request=request, asset_id=asset_id, configuration=configuration, context=ctx)
        )
        owning_group = OwningGroup(name=to_group_scope(asset.groupId), groupId=asset.groupId)

        groups = list({policy['consumer_group_id'] for policy in policies['documents']
                       if policy['consumer_group_id'] != asset.groupId})
        policies = await asyncio.gather(*[
            get_access_policy(request=request, asset_id=asset_id, group_id=group_id, configuration=configuration)
            for group_id in groups + ["*"]
        ])
        exposing_groups = [ExposingGroup(name=to_group_scope(group), groupId=group, access=format_policy(policy))
                           for group, policy in zip(groups, policies[0:-1]) if group != "*"]
        default_access = format_policy(policies[-1])
        owner_info = OwnerInfo(exposingGroups=exposing_groups, defaultAccess=default_access)

        permissions = PermissionsResp(write=permissions.write, read=permissions.read, share=permissions.share,
                                      expiration=permissions.expiration)

        consumer_info = ConsumerInfo(permissions=permissions)

        response = AccessInfoResp(owningGroup=owning_group,
                                  ownerInfo=owner_info,
                                  consumerInfo=consumer_info)
        return response


@router.delete("/assets/{asset_id}", summary="delete an asset")
async def delete_asset(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration,
                                            context=ctx)
        docdb_access = configuration.doc_db_access_policy

        query = QueryBody(
            max_results=1000,
            query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id)])
        )

        _, docs = await asyncio.gather(
            ensure_delete_permission(request=request, asset=asset, configuration=configuration,
                                     context=ctx),
            docdb_access.query(query_body=query, owner=Constants.public_owner, headers=ctx.headers()))

        await asyncio.gather(*[docdb_access.delete_document(doc=d, owner=Constants.public_owner, headers=ctx.headers())
                               for d in docs['documents']])
        return {}


async def get_asset_implementation(
        request: Request,
        asset_id: str,
        configuration: Configuration,
        context: Context) -> AssetResponse:
    asset = await ensure_get_permission(request=request, asset_id=asset_id, scope='r', configuration=configuration,
                                        context=context)
    return format_asset(asset, request)


@router.get(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    summary="return an asset"
)
async def get_asset(
        request: Request,
        asset_id: str,
        configuration: Configuration = Depends(get_configuration)):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context
        return await get_asset_implementation(request=request, asset_id=asset_id, configuration=configuration,
                                              context=ctx)


@router.put(
    "/raw/access/{related_id}",
    summary="register access"
)
async def record_access(
        request: Request,
        related_id: str,
        configuration: Configuration = Depends(get_configuration)
):
    """
    WARNING: use 'allow_filtering' => do not use in prod
    Probably need as secondary index on 'related_id'
    """
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        user = user_info(request)
        doc_db_assets, doc_db_history = configuration.doc_db_asset, configuration.doc_db_access_history

        query = QueryBody(
            max_results=1,
            allow_filtering=True,
            query=Query(where_clause=[WhereClause(column="related_id", relation="eq", term=related_id)])
        )
        asset = await doc_db_assets.query(query_body=query, owner=Constants.public_owner, headers=ctx.headers())

        if len(asset["documents"]) == 0:
            raise HTTPException(status_code=404, detail=f"Asset with related_id ${related_id} not found")
        if len(asset["documents"]) > 1:
            raise HTTPException(status_code=404, detail=f"Multiple assets with related_id ${related_id} found")

        asset = asset["documents"][0]
        now = time.time()  # s since epoch (January 1, 1970)
        doc = {"record_id": str(uuid.uuid4()), "asset_id": asset["asset_id"], "related_id": asset["related_id"],
               "username": user['preferred_username'], "timestamp": int(now)}
        await doc_db_history.create_document(doc=doc, owner=Constants.public_owner, headers=ctx.headers())

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
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        doc_db_history = configuration.doc_db_access_history

        query = QueryBody(
            max_results=max_count,
            allow_filtering=True,
            query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id)])
        )

        results = await doc_db_history.query(query_body=query, owner=Constants.public_owner, headers=ctx.headers())

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
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        doc_db_history = configuration.doc_db_access_history

        user = user_info(request)
        query = QueryBody(
            max_results=count,
            allow_filtering=True,
            query=Query(where_clause=[WhereClause(column="asset_id", relation="eq", term=asset_id),
                                      WhereClause(column="username", relation="eq", term=user["preferred_username"])])
        )

        results = await doc_db_history.query(query_body=query, owner=Constants.public_owner, headers=ctx.headers())
        await asyncio.gather(*[
            doc_db_history.delete_document(doc=doc, owner=Constants.public_owner, headers=ctx.headers())
            for doc in results["documents"]
        ])
        return {}


@router.post("/assets/{asset_id}/images/{filename}",
             response_model=AssetResponse,
             summary="add an image to asset")
async def post_image(
        request: Request,
        asset_id: str,
        filename: str,
        file: UploadFile = File(...),
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        storage, doc_db = configuration.storage, configuration.doc_db_asset

        asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration,
                                            context=ctx)

        if [img for img in asset["images"] if img.split('/')[-1] == filename]:
            raise HTTPException(status_code=409, detail=f"image '{filename}' already exist")

        image = await format_image(filename, file)
        thumbnail = get_thumbnail(image, size=(200, 200))

        doc = {**asset, **{
            "images": [*asset["images"], f"/api/assets-backend/assets/{asset_id}/images/{image.name}"],
            "thumbnails": [*asset["thumbnails"], f"/api/assets-backend/assets/{asset_id}/thumbnails/{thumbnail.name}"]}
               }

        await ensure_post_permission(request=request, doc=doc, configuration=configuration,
                                     context=ctx)

        post_image_body = FileData(
            objectData=image.content, objectName=Path(asset['kind']) / asset_id / "images" / image.name,
            owner=Constants.public_owner, objectSize=len(image.content), content_type="image/" + image.extension,
            content_encoding=""
        )

        post_thumbnail_body = FileData(
            objectData=thumbnail.content, objectName=Path(asset['kind']) / asset_id / "thumbnails" / thumbnail.name,
            owner=Constants.public_owner, objectSize=len(thumbnail.content),
            content_type="image/" + thumbnail.extension,
            content_encoding="")

        post_file_bodies = [post_image_body, post_thumbnail_body]

        await asyncio.gather(*[storage.post_object(path=post_file_body.objectName, content=post_file_body.objectData,
                                                   owner=post_file_body.owner, content_type=post_file_body.content_type,
                                                   headers=ctx.headers())
                               for post_file_body in post_file_bodies])
        return await get_asset_implementation(request=request, asset_id=asset_id, configuration=configuration,
                                              context=ctx)


@router.delete("/assets/{asset_id}/images/{filename}",
               response_model=AssetResponse,
               summary="remove an image")
async def remove_image(
        request: Request,
        asset_id: str,
        filename: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        storage, doc_db = configuration.storage, configuration.doc_db_asset

        asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="w", configuration=configuration,
                                            context=ctx)
        base_path = Path("/api/assets-backend/") / 'assets' / asset_id
        doc = {**asset, **{
            "images": [image for image in asset["images"]
                       if image != str(base_path / "images" / filename)],
            "thumbnails": [thumbnail for thumbnail in asset["thumbnails"]
                           if thumbnail != str(base_path / "thumbnails" / filename)]
        }
               }
        await ensure_post_permission(request=request, doc=doc, configuration=configuration,
                                     context=ctx)
        await asyncio.gather(storage.delete(Path(asset['kind']) / asset_id / "images" / filename,
                                            owner=Constants.public_owner, headers=ctx.headers()),
                             storage.delete(Path(asset['kind']) / asset_id / "thumbnails" / filename,
                                            owner=Constants.public_owner, headers=ctx.headers()))
        return await get_asset_implementation(request=request, asset_id=asset_id, configuration=configuration,
                                              context=ctx)


@router.get("/assets/{asset_id}/{media_type}/{name}", summary="return a media")
async def get_media(
        request: Request,
        asset_id: str,
        media_type: str,
        name: str,
        configuration: Configuration = Depends(get_configuration)
):
    async with Context.start_ep(
            request=request
    ) as ctx:  # type: Context

        asset = await ensure_get_permission(request=request, asset_id=asset_id, scope="r", configuration=configuration,
                                            context=ctx)

        storage = configuration.storage
        path = Path(asset['kind']) / asset_id / media_type / name
        file = await storage.get_bytes(path, owner=Constants.public_owner, headers=ctx.headers())
        return Response(content=file, headers={
            "Content-Encoding": "",
            "Content-Type": f"image/{path.suffix[1:]}",
            "cache-control": "public, max-age=31536000"
        })
