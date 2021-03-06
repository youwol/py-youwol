import asyncio
import base64
import io
import itertools
import os
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Tuple, Union, List, Mapping, Any, Dict
from uuid import uuid4

from PIL import Image
from fastapi import UploadFile
from starlette.requests import Request

from youwol_utils import (
    chunks, Storage, get_content_type, user_info,
    get_user_group_ids, ensure_group_permission, QueryBody, DocDb, log_info,
)
from youwol_assets_backend.configurations import Configuration, Constants
from youwol_utils.context import Context
from youwol_utils.http_clients.assets_backend.models import ParsedFile, FormData, AssetResponse, GroupAccess, \
    ReadPolicyEnumFactory, SharePolicyEnumFactory, AccessPolicyResp

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
    if scope == 'private':
        return None
    return scope


def group_scope_to_id(scope: str) -> str:
    if scope == 'private':
        return 'private'
    b = str.encode(scope)
    return base64.urlsafe_b64encode(b).decode()


async def format_image(
        filename: str,
        file: UploadFile
) -> ParsedFile:
    return ParsedFile(content=await file.read(), name=filename, extension=filename.split('.')[-1])


def get_thumbnail(
        file: ParsedFile,
        size: Tuple[int, int]
) -> ParsedFile:
    ext_dict = {
        "jpg": "JPEG",
        "JPG": "JPEG",
        "png": "PNG",
        "PNG": "PNG"
    }
    image = Image.open(io.BytesIO(file.content))
    image.thumbnail(size)
    with io.BytesIO() as output:
        image.save(output, format=ext_dict[file.extension])
        contents = output.getvalue()

    return ParsedFile(content=contents, name=file.name, extension=file.extension)


def to_doc_db_id(related_id: str) -> str:
    b = str.encode(related_id)
    return base64.urlsafe_b64encode(b).decode()


def get_raw_record_permissions(
        request: Request,
        group_id: str
):
    user = user_info(request)
    allowed_groups = get_user_group_ids(user)
    return {
        "read": group_id in allowed_groups,
        "write": group_id in allowed_groups
    }


def format_asset(doc, _: Request):
    return AssetResponse(assetId=doc["asset_id"], kind=doc["kind"], rawId=doc["related_id"], name=doc["name"],
                         images=doc["images"], thumbnails=doc["thumbnails"], tags=doc["tags"],
                         description=doc["description"], groupId=doc["group_id"])


def format_record_history(doc):
    return {
        "recordId": doc["record_id"],
        "assetId": doc["asset_id"],
        "relatedId": doc["related_id"],
        "username": doc["username"],
        "timestamp": doc["timestamp"]
    }


def to_snake_case(key: str):
    conv = {
        "assetId": "asset_id",
        "relatedId": "related_id",
        "groupId": "group_id"
    }
    return key if key not in conv else conv[key]


def create_tmp_folder(
        zip_filename: Union[str, Path]
) -> (Path, Path, str):
    dir_path = Path("./tmp_zips") / str(uuid4())
    zip_path = (dir_path / zip_filename).with_suffix('.zip')
    zip_dir_name = zip_filename.split('.')[0]
    os.makedirs(dir_path)
    return dir_path, zip_path, zip_dir_name


def extract_zip_file(
        file: UploadFile,
        zip_path: Union[Path, str],
        dir_path: Union[Path, str]
) -> (int, str):
    dir_path = str(dir_path)
    with open(zip_path, 'ab') as f:
        for chunk in iter(lambda: file.file.read(10000), b''):
            f.write(chunk)

    compressed_size = zip_path.stat().st_size
    md5_stamp = os.popen('md5sum ' + str(zip_path)).read().split(" ")[0]

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dir_path)

    os.remove(zip_path)
    return compressed_size, md5_stamp


def format_download_form(
        file_path: Path,
        base_path: Path,
        dir_path: Path
) -> FormData:
    data = open(str(file_path), 'rb').read()
    path_bucket = base_path / file_path.relative_to(dir_path)

    return FormData(objectName=path_bucket, objectData=data,
                    objectSize=len(data), content_type=get_content_type(file_path.name),
                    content_encoding="")


async def post_storage_by_chunk(
        storage: Storage,
        forms: List[FormData],
        count: int,
        headers: Dict[str, str]
):
    for i, chunk in enumerate(chunks(forms, count)):
        progress = 100 * i / (len(forms) / count)
        print(f"post files chunk, progress: {progress}")
        await asyncio.gather(*[storage.post_file(form=form, headers=headers) for form in chunk])


async def post_indexes(
        doc_db: DocDb,
        data: Any,
        count: int,
        group: str,
        headers: Dict[str, str]
):
    for chunk in chunks(data, count):
        await asyncio.gather(*[doc_db.create_document(d, headers=headers, owner=group) for d in chunk])


async def switch_data(
        asset_id: str,
        asset: any,
        kind: str,
        from_group: Union[str, None],
        to_group: Union[str, None],
        storage: Storage,
        headers: Mapping[str, str]
):
    if not asset["images"]:
        return
    files = [img.replace("/api/assets-backend/assets", f"{kind}") for img in asset["images"] + asset["thumbnails"]]
    files_data = await asyncio.gather(*[storage.get_bytes(path=file, owner=from_group, headers=headers)
                                        for file in files])

    await asyncio.gather(*[storage.post_object(path=file, owner=to_group, content=data,
                                               content_type=get_content_type(file), headers=headers)
                           for data, file in zip(files_data, files)])
    await storage.delete_group(prefix=f"{kind}/{asset_id}", owner=from_group, headers=headers)


async def ensure_get_permission(
        request: Request,
        asset_id: str,
        scope: str,
        configuration: Configuration,
        context: Context
):
    async with context.start(action="ensure_get_permission") as ctx:  # type: Context
        docdb = configuration.doc_db_asset
        asset = await docdb.get_document(partition_keys={"asset_id": asset_id}, clustering_keys={},
                                         owner=Constants.public_owner, headers=ctx.headers())
        # there is no restriction on access asset 'metadata' for now fo read
        if 'w' in scope:
            ensure_group_permission(request=request, group_id=asset["group_id"])
        return asset


async def ensure_query_permission(
        request: Request,
        query: QueryBody,
        scope: str,
        configuration: Configuration,
        context: Context
):
    # there is no restriction on access asset 'metadata' for now
    # ensure_group_permission(request=request, group_id=asset["group_id"])
    # ensure_group_permission(request=request, group_id=query.groupId)
    async with context.start(action="ensure_query_permission") as ctx:  # type: Context
        doc_db = configuration.doc_db_asset

        r = await doc_db.query(query_body=query, owner=Constants.public_owner, headers=ctx.headers())
        user = user_info(request)
        allowed_groups = get_user_group_ids(user)
        if 'w' in scope:
            return [d for d in r["documents"] if d["group_id"] in allowed_groups]
        return r["documents"]


async def ensure_delete_permission(
        request: Request,
        asset: any,
        configuration: Configuration,
        context: Context
):
    # only owning group can delete
    async with context.start(action="ensure_delete_permission") as ctx:  # type: Context
        ensure_group_permission(request=request, group_id=asset["group_id"])

        storage, doc_db = configuration.storage, configuration.doc_db_asset
        asset_id = asset["asset_id"]

        await asyncio.gather(
            storage.delete_group(prefix=Path(asset['kind']) / asset_id, owner=Constants.public_owner,
                                 headers=ctx.headers()),
            doc_db.delete_document(doc=asset, owner=Constants.public_owner, headers=ctx.headers()))

        return asset


async def ensure_post_permission(
        request: Request,
        doc,
        configuration: Configuration,
        context: Context
):
    # only owning group can put/post
    async with context.start(action="ensure_post_permission") as ctx:  # type: Context
        ensure_group_permission(request=request, group_id=doc["group_id"])
        doc_db = configuration.doc_db_asset
        return await doc_db.update_document(doc, owner=Constants.public_owner, headers=ctx.headers())


def access_policy_record_id(
        asset_id: str,
        group_id: str
):
    return asset_id + "_" + group_id


def format_policy(policy: AccessPolicyResp) -> GroupAccess:
    if policy.read not in ReadPolicyEnumFactory:
        raise RuntimeError("Read policy not known")

    if policy.share not in SharePolicyEnumFactory:
        raise RuntimeError("Share policy not known")

    expiration = None
    if policy.read == "expiration-date":
        deadline = policy.timestamp + policy.parameters['period']
        expiration = str(datetime.fromtimestamp(deadline))

    return GroupAccess(read=ReadPolicyEnumFactory[policy.read],
                       expiration=expiration,
                       share=SharePolicyEnumFactory[policy.share])
