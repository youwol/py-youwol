# standard library
import asyncio
import base64
import io
import itertools

from datetime import datetime
from pathlib import Path

# typing
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

# third parties
from fastapi import UploadFile
from PIL import Image
from starlette.requests import Request

# Youwol backends
from youwol.backends.assets.configurations import Configuration, Constants

# Youwol utilities
from youwol.utils import (
    JSON,
    DocDb,
    QueryBody,
    Storage,
    chunks,
    get_content_type,
    get_user_group_ids,
    log_info,
    user_info,
)
from youwol.utils.context import Context
from youwol.utils.http_clients.assets_backend.models import (
    AccessPolicyResp,
    AssetResponse,
    FormData,
    GroupAccess,
    ParsedFile,
    ReadPolicyEnumFactory,
    SharePolicyEnumFactory,
)

flatten = itertools.chain.from_iterable


async def init_resources(config: Configuration):
    log_info("Ensure database resources")
    headers = config.admin_headers if config.admin_headers else {}

    log_info("Successfully retrieved authorization for resources creation")
    log_info("Ensure assets table")
    await config.doc_db_asset.ensure_table(headers=headers)
    log_info("Ensure assets bucket")
    await config.storage.ensure_bucket(headers=headers)
    log_info("Ensure access policy table")
    await asyncio.gather(config.doc_db_access_policy.ensure_table(headers=headers))
    log_info("Ensure access history table")
    await asyncio.gather(config.doc_db_access_history.ensure_table(headers=headers))
    log_info("resources initialization done")


def group_scope_to_owner(scope: str) -> Union[str, None]:
    if scope == "private":
        return None
    return scope


def group_scope_to_id(scope: str) -> str:
    if scope == "private":
        return "private"
    b = str.encode(scope)
    return base64.urlsafe_b64encode(b).decode()


async def format_image(filename: str, file: UploadFile) -> ParsedFile:
    return ParsedFile(
        content=await file.read(), name=filename, extension=filename.split(".")[-1]
    )


def get_thumbnail(file: ParsedFile, size: Tuple[int, int]) -> ParsedFile:
    ext_dict = {"jpg": "JPEG", "JPG": "JPEG", "png": "PNG", "PNG": "PNG"}
    image = Image.open(io.BytesIO(file.content))
    image.thumbnail(size)
    with io.BytesIO() as output:
        image.save(output, format=ext_dict[file.extension])
        contents = output.getvalue()

    return ParsedFile(content=contents, name=file.name, extension=file.extension)


def to_doc_db_id(related_id: str) -> str:
    b = str.encode(related_id)
    return base64.urlsafe_b64encode(b).decode()


def get_raw_record_permissions(request: Request, group_id: str):
    user = user_info(request)
    allowed_groups = get_user_group_ids(user)
    return {"read": group_id in allowed_groups, "write": group_id in allowed_groups}


def format_asset(doc: JSON, _: Request):
    return AssetResponse(
        assetId=doc["asset_id"],
        kind=doc["kind"],
        rawId=doc["related_id"],
        name=doc["name"],
        images=doc["images"],
        thumbnails=doc["thumbnails"],
        tags=doc["tags"],
        description=doc["description"],
        groupId=doc["group_id"],
    )


def format_record_history(doc):
    return {
        "recordId": doc["record_id"],
        "assetId": doc["asset_id"],
        "relatedId": doc["related_id"],
        "username": doc["username"],
        "timestamp": doc["timestamp"],
    }


def to_snake_case(key: str):
    conv = {"assetId": "asset_id", "relatedId": "related_id", "groupId": "group_id"}
    return key if key not in conv else conv[key]


def format_download_form(file_path: Path, base_path: Path, dir_path: Path) -> FormData:
    with open(str(file_path), "rb") as fp:
        data = fp.read()
        path_bucket = base_path / file_path.relative_to(dir_path)

        return FormData(
            objectName=path_bucket,
            objectData=data,
            objectSize=len(data),
            content_type=get_content_type(file_path.name),
            content_encoding="",
        )


async def post_storage_by_chunk(
    storage: Storage, forms: List[FormData], count: int, headers: Dict[str, str]
):
    for _, chunk in enumerate(chunks(forms, count)):
        await asyncio.gather(
            *[storage.post_file(form=form, headers=headers) for form in chunk]
        )


async def post_indexes(
    doc_db: DocDb, data: Any, count: int, group: str, headers: Dict[str, str]
):
    for chunk in chunks(data, count):
        await asyncio.gather(
            *[doc_db.create_document(d, headers=headers, owner=group) for d in chunk]
        )


async def switch_data(
    asset_id: str,
    asset: any,
    kind: str,
    from_group: Union[str, None],
    to_group: Union[str, None],
    storage: Storage,
    headers: Mapping[str, str],
):
    if not asset["images"]:
        return
    files = [
        img.replace("/api/assets-backend/assets", f"{kind}")
        for img in asset["images"] + asset["thumbnails"]
    ]
    files_data = await asyncio.gather(
        *[
            storage.get_bytes(path=file, owner=from_group, headers=headers)
            for file in files
        ]
    )

    await asyncio.gather(
        *[
            storage.post_object(
                path=file,
                owner=to_group,
                content=data,
                content_type=get_content_type(file),
                headers=headers,
            )
            for data, file in zip(files_data, files)
        ]
    )
    await storage.delete_group(
        prefix=f"{kind}/{asset_id}", owner=from_group, headers=headers
    )


async def db_get(asset_id: str, configuration: Configuration, context: Context):
    async with context.start(action="db_get") as ctx:  # type: Context
        docdb = configuration.doc_db_asset
        asset = await docdb.get_document(
            partition_keys={"asset_id": asset_id},
            clustering_keys={},
            owner=Constants.public_owner,
            headers=ctx.headers(),
        )
        return asset


async def db_query(query: QueryBody, configuration: Configuration, context: Context):
    async with context.start(action="db_query") as ctx:  # type: Context
        doc_db = configuration.doc_db_asset
        r = await doc_db.query(
            query_body=query, owner=Constants.public_owner, headers=ctx.headers()
        )
        return r["documents"]


async def db_delete(asset: any, configuration: Configuration, context: Context):
    async with context.start(action="db_delete") as ctx:  # type: Context
        storage, doc_db = configuration.storage, configuration.doc_db_asset
        asset_id = asset["asset_id"]

        await asyncio.gather(
            storage.delete_group(
                prefix=Path(asset["kind"]) / asset_id,
                owner=Constants.public_owner,
                headers=ctx.headers(),
            ),
            doc_db.delete_document(
                doc=asset, owner=Constants.public_owner, headers=ctx.headers()
            ),
        )

        return asset


async def db_post(doc, configuration: Configuration, context: Context):
    # only owning group can put/post
    async with context.start(action="db_post") as ctx:  # type: Context
        doc_db = configuration.doc_db_asset
        return await doc_db.update_document(
            doc, owner=Constants.public_owner, headers=ctx.headers()
        )


def access_policy_record_id(asset_id: str, group_id: str):
    return asset_id + "_" + group_id


def format_policy(policy: AccessPolicyResp) -> GroupAccess:
    if policy.read not in ReadPolicyEnumFactory:
        raise RuntimeError("Read policy not known")

    if policy.share not in SharePolicyEnumFactory:
        raise RuntimeError("Share policy not known")

    expiration = None
    if policy.read == "expiration-date":
        deadline = policy.timestamp + policy.parameters["period"]
        expiration = str(datetime.fromtimestamp(deadline))

    return GroupAccess(
        read=ReadPolicyEnumFactory[policy.read],
        expiration=expiration,
        share=SharePolicyEnumFactory[policy.share],
    )


def get_file_path(
    asset_id: str, kind: str, file_path: Optional[Union[Path, str]] = None
) -> str:
    return (
        f"{kind}/{asset_id}/files/{file_path}"
        if file_path
        else f"{kind}/{asset_id}/files/"
    )


async def log_asset(asset: Dict[str, str], context: Context):
    await context.info(text="asset retrieved", data=asset)
