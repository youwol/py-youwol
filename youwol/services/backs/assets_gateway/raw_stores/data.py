import asyncio
import json
import uuid
from abc import ABC
from typing import Union

from dataclasses import dataclass
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from youwol_utils import (
    user_info, get_all_individual_groups, get_group, RecordsResponse, RecordsTable, RecordsKeyspace, RecordsDocDb,
    RecordsStorage, RecordsBucket, to_group_id,
    )
from youwol_utils.clients.data_api.data import DataClient
from .interface import (RawStore, RawId, AssetMeta, AssetImg)


mime_types_text = ["application/json", "text/html", "application/javascript", "text/plain", "text/markdown",
                   "application/x-yaml", "text/yaml", "text/javascript"]
mime_types_images = ["image/png", "image/jpeg", "image/gif", "image/bmp", "image/x-icon", "image/tiff",
                     "image/webp", "image/svg+xml"]


@dataclass(frozen=True)
class DataStore(RawStore, ABC):
    client: DataClient
    path_name = 'data'
    owner = '/youwol-users'

    async def create_asset(self, request: Request, metadata: AssetMeta, headers) -> (RawId, AssetMeta):

        raw_id = str(uuid.uuid4())
        file = (await request.form()).get('file')

        doc = {"file_id": raw_id,
               "file_name": file.filename,
               "content_type": file.content_type,
               "content_encoding": ""
               }
        storage, docdb = self.client.storage, self.client.docdb
        content = await file.read()
        await asyncio.gather(
            storage.post_object(path=raw_id, content=content, content_type=file.content_type,
                                owner=self.owner, headers=headers),
            docdb.create_document(doc=doc, owner=self.owner, headers=headers)
            )

        dynamic_fields = {
            "content_type": file.content_type,
            "content_encoding": ""
            }
        images = [AssetImg(name=file.filename, content=content)] if file.content_type in mime_types_images else None
        meta = AssetMeta(name=file.filename, images=images, dynamic_fields=dynamic_fields)
        return raw_id, meta

    async def sync_asset_metadata(self, request: Request, raw_id: str, metadata: AssetMeta, headers):

        docdb = self.client.docdb
        user = user_info(request)
        groups = get_all_individual_groups(user["memberof"])
        owner = await get_group("file_id", raw_id, groups, docdb, headers)
        doc = await docdb.get_document(partition_keys={"file_id": raw_id}, clustering_keys={},
                                       owner=owner, headers=headers)

        if metadata.name:
            doc['file_name'] = metadata.name

        await docdb.create_document(doc=doc, owner=self.owner, headers=headers)
        return doc

    async def update_asset(self, request: Request, raw_id: str,  metadata: AssetMeta, rest_of_path: str, headers):

        if rest_of_path != "metadata":
            raise HTTPException(status_code=404, detail="End point not found")

        doc = await self.client.docdb.get_document(partition_keys={"file_id": raw_id}, clustering_keys={},
                                                   owner=self.owner, headers=headers)
        body = json.loads((await request.body()).decode('utf8'))

        if 'contentType' in body:
            doc['content_type'] = body['contentType']

        if 'contentEncoding' in body:
            doc['content_encoding'] = body['contentEncoding']

        if metadata.name:
            doc['file_name'] = metadata.name

        await self.client.docdb.create_document(doc=doc, owner=self.owner, headers=headers)
        return doc

    async def get_asset(self, request: Request, raw_id: str,  rest_of_path: Union[str, None], headers):

        storage, docdb = self.client.storage, self.client.docdb

        file, meta = await asyncio.gather(
            storage.get_bytes(path=raw_id, owner=self.owner, headers=headers),
            docdb.get_document(partition_keys={"file_id": raw_id}, clustering_keys={},
                               owner=self.owner, headers=headers))

        return Response(content=file, headers={
            "Content-Encoding": meta["content_encoding"],
            "Content-Type": meta["content_type"],
            "cache-control": "public, max-age=31536000"
            })

    async def get_asset_metadata(self, request: Request, raw_id: str, rest_of_path: Union[str, None], headers):

        docdb = self.client.docdb

        meta = await docdb.get_document(partition_keys={"file_id": raw_id}, clustering_keys={},
                                        owner=self.owner, headers=headers)

        if rest_of_path == "preview" and meta["content_encoding"] == "" and meta["content_type"] in mime_types_text:
            file = await self.client.storage.get_bytes(path=raw_id, owner=self.owner, headers=headers)
            decoded = file.decode('utf8')
            content = decoded if len(decoded) < 10000 else \
                decoded[0:10000] + "\n /!\\ content truncated from here /!\\"
            return {
                "kind": "text",
                "content": content
                }
        if rest_of_path == "preview" and meta["content_type"] in mime_types_images:
            return {
                "kind": "image",
                "content": f"/api/assets-gateway/raw/data/{raw_id}"
                }
        if rest_of_path == "preview":
            return {
                "kind": "unknown",
                "content": ""
                }

        return {
            "contentEncoding": meta["content_encoding"],
            "contentType": meta["content_type"]
            }

    async def delete_asset(self, request: Request, raw_id: str, headers):

        storage, docdb = self.client.storage, self.client.docdb

        await asyncio.gather(
            storage.delete(path=raw_id, owner=self.owner, headers=headers),
            docdb.delete_document(doc={"file_id": raw_id}, owner=self.owner, headers=headers)
            )

    async def get_records(self, request: Request, raw_ids: str, group_id: str, headers):

        storage, docdb = self.client.storage, self.client.docdb
        table = RecordsTable(id=docdb.table_name, primaryKey="file_id", values=raw_ids)
        keyspace = RecordsKeyspace(id=docdb.keyspace_name, groupId=to_group_id(self.owner), tables=[table])

        bucket = RecordsBucket(id=storage.bucket_name, groupId=to_group_id(self.owner), paths=raw_ids)
        response = RecordsResponse(docdb=RecordsDocDb(keyspaces=[keyspace]), storage=RecordsStorage(buckets=[bucket]))
        return response
