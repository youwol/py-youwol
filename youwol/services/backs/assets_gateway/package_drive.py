import asyncio
import json
import os
import shutil
import time
import uuid
import zipfile
from pathlib import Path

from fastapi import HTTPException
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import JSONResponse

from .configurations import Configuration
from youwol_utils import (
    generate_headers_downstream, itertools, flatten, to_group_owner, Union, RecordsResponse,
    RecordsBucket,
    )

from .routers.assets import put_asset_with_raw
from .utils import get_items_rec, chrono


class MockFile:

    def __init__(self, content_type, filename, content):
        self.content_type = content_type
        self.filename = filename
        self.content = content
        self.file = self

    async def read(self):
        return self.content


class MyRequest(Request):

    def __init__(self, scope, file: MockFile):
        super().__init__(scope)
        self.file = file

    async def form(self):
        return {'file': self.file}


async def pack_drive(
        request: Request,
        drive_id: str,
        configuration: Configuration
        ):

    headers = generate_headers_downstream(request.headers)
    assets_db, treedb_client = configuration.assets_client, configuration.treedb_client
    assets_stores = configuration.assets_stores()
    start_time = time.time()

    drive = await treedb_client.get_drive(drive_id=drive_id, headers=headers)
    drive_time, now = chrono(start_time)

    tree_records = await treedb_client.get_records(body={"folderId": drive_id}, headers=headers)
    tree_records = RecordsResponse(**tree_records)
    tree_records_time, now = chrono(now)

    assets = await get_items_rec(folder_id=drive_id, headers=headers, configuration=configuration)
    assets = [a for a in assets if a['type'] in configuration.to_package]
    group_id = drive['groupId']

    asset_ids = [asset['relatedId'] for asset in assets]

    assets_list_time, now = chrono(now)

    assets_records = await assets_db.get_records(body={"ids": asset_ids, "groupId": group_id}, headers=headers)
    assets_records = RecordsResponse(**assets_records)
    assets_records_time, now = chrono(now)

    assets = sorted(assets, key=lambda asset: asset['type'])
    records = []
    for kind, group in itertools.groupby(assets, lambda asset: asset['type']):
        store = next(store for store in assets_stores if store.path_name == kind)
        raw_ids = [json.loads(asset['metadata'])['relatedId'] for asset in group]
        record = await store.get_records(request=request, raw_ids=raw_ids, group_id=group_id, headers=headers)
        records.append(record)

    raw_stores_keyspaces = list(flatten([val.docdb.keyspaces for val in records]))
    all_keyspaces = tree_records.docdb.keyspaces + assets_records.docdb.keyspaces + raw_stores_keyspaces

    raw_stores_buckets = list(flatten([val.storage.buckets for val in records]))
    all_buckets = tree_records.storage.buckets + assets_records.storage.buckets + raw_stores_buckets

    raw_records_time, now = chrono(now)

    def get_coroutines_docdb(keyspace, table):
        doc_db = configuration.docdb_factory(keyspace.id, table.id, table.primaryKey)
        owner = to_group_owner(keyspace.groupId)
        return [{
            "keyspace": keyspace.id,
            "primaryKey": table.primaryKey,
            "table": table.id,
            "groupId": keyspace.groupId,
            "coroutine":
                doc_db.get_document(partition_keys={table.primaryKey: key},
                                    clustering_keys={},
                                    owner=owner,
                                    headers=headers)}
                for key in table.values]

    coroutines = flatten([[get_coroutines_docdb(keyspace, table) for table in keyspace.tables]
                          for keyspace in all_keyspaces])
    coroutines = list(flatten(coroutines))

    records = await asyncio.gather(*[c["coroutine"] for c in coroutines])
    records = [{"keyspace": c['keyspace'],
                "table": c["table"],
                "primaryKey": c["primaryKey"],
                "groupId": c["groupId"],
                'doc': d}
               for d, c in zip(records, coroutines)]

    def get_key(c):
        return c['keyspace'] + "@" + c["table"] + "@" + c["primaryKey"]

    records = sorted(records, key=lambda rec: get_key(rec))
    docdb_data = []
    for kind, group in itertools.groupby(records, lambda rec:  get_key(rec)):
        grp = list(group)
        first = next(g for g in grp)
        columns = list(first['doc'].keys())
        docdb_data.append({
            'keyspace': first['keyspace'],
            'table': first['table'],
            "primaryKey": first['primaryKey'],
            "groupId": first["groupId"],
            'columns': columns,
            "values": [[v['doc'][c] for c in columns] for v in grp]
            })

    docdb_fetch_time, now = chrono(now)

    def get_coroutines_storage(bucket: RecordsBucket):
        storage = configuration.storage_factory(bucket.id)
        owner = to_group_owner(bucket.groupId)
        return [{
            "bucket": bucket.id,
            "path": path,
            "uid": str(uuid.uuid4()),
            "groupId": bucket.groupId,
            "coroutine": storage.get_bytes(path=path, owner=owner, headers=headers)}
            for path in bucket.paths]

    coroutines = list(flatten([get_coroutines_storage(bucket) for bucket in all_buckets]))
    files = await asyncio.gather(*[c["coroutine"] for c in coroutines])

    storage_fetch_time, now = chrono(now)

    uid = str(uuid.uuid4())
    folder_path = Path('packages')/uid
    try:
        folder_path.mkdir(parents=True)

        for file, meta in zip(files, coroutines):
            file_path = folder_path / meta["uid"]
            file_path.write_bytes(file)
        storage_data = [{"bucket": meta['bucket'], "path": meta['path'], 'uid': meta['uid'],
                         "groupId": meta['groupId']}
                        for meta in coroutines]

        metadata = {
            "rootTreeId": drive['driveId'],
            "groupId": group_id
            }
        (folder_path / 'metadata.json').write_text(json.dumps(metadata, indent=4))
        docdb_json = {
            "keyspaces": docdb_data,
            }
        (folder_path / 'docdb_data.json').write_text(json.dumps(docdb_json, indent=4))

        storage_json = {
            "buckets": storage_data,
            }

        (folder_path / 'storage_data.json').write_text(json.dumps(storage_json, indent=4))

        shutil.make_archive(base_name=f"packages/{uid}", format='zip', root_dir=folder_path)

        zip_time, now = chrono(now)

        content = (Path('packages') / (uid+".zip")).read_bytes()

        file = MockFile(filename="drive-pack.zip", content=content, content_type="application/zip")
        my_req = MyRequest(request.scope, file=file)
        content = await put_asset_with_raw(my_req, "drive-pack", drive_id, group_id=group_id,
                                           configuration=configuration)

        post_zip_time, now = chrono(now)

        timings = f"drive_time;dur={drive_time}, tree_records_time;dur={drive_time}," + \
            f"assets_list_time;dur={assets_list_time},assets_records_time;dur={assets_records_time}," + \
            f"raw_records_time;dur={raw_records_time},docdb_fetch_time;dur={docdb_fetch_time}," +\
            f"storage_fetch_time;dur={storage_fetch_time},zip_time;dur={zip_time}, post_zip_time;dur={post_zip_time}"

        return JSONResponse(
            content=json.loads(content.body.decode('utf8')),
            headers={"Server-Timing": timings})

    finally:
        os.remove(Path('packages')/(uid + ".zip"))
        shutil.rmtree(folder_path)


def extract_zip_file(
        file: Union[UploadFile, MockFile],
        zip_path: Union[Path, str],
        dir_path: Union[Path, str]
        ):

    dir_path = str(dir_path)
    if isinstance(file, UploadFile):
        with open(zip_path, 'ab') as f:
            for chunk in iter(lambda: file.file.read(10000), b''):
                f.write(chunk)
    else:
        f = open(zip_path, 'wb')
        f.write(file.content)
        f.close()

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dir_path)


async def unpack_drive(
        request: Request,
        drive_id: str,
        file: Union[UploadFile, MockFile],
        configuration: Configuration
        ):

    headers = generate_headers_downstream(request.headers)

    assets_db, treedb_client = configuration.assets_client, configuration.treedb_client
    drive = await treedb_client.get_drive(drive_id=drive_id, headers=headers)
    dir_path = Path("./tmp_unzips")/str(uuid.uuid4())
    zip_path = (dir_path/file.filename).with_suffix('.zip')

    os.makedirs(dir_path)
    group_id = drive["groupId"]

    try:
        extract_zip_file(file, zip_path, dir_path)

        metadata = json.loads((zip_path.parent / 'metadata.json').read_text())

        if group_id != metadata["groupId"]:
            raise HTTPException(status_code=401, detail="You can unpack only in same group")

        docdb_text = (zip_path.parent / 'docdb_data.json')\
            .read_text()\
            .replace(metadata["rootTreeId"], drive_id)
        docdb_data = json.loads(docdb_text)

        for keyspace in docdb_data["keyspaces"]:
            docdb = configuration.docdb_factory(keyspace["keyspace"], keyspace["table"], keyspace["primaryKey"])
            owner = to_group_owner(keyspace["groupId"])

            def format_doc(attributes):
                doc = {column: attributes[i] for i, column in enumerate(keyspace["columns"])}
                return doc

            coroutines = [docdb.create_document(doc=format_doc(record), owner=owner, headers=headers)
                          for record in keyspace["values"]]
            await asyncio.gather(*coroutines)

        storage_data = json.loads((zip_path.parent / 'storage_data.json').read_text())
        buckets = sorted(storage_data["buckets"], key=lambda b: b["bucket"])

        for bucket, group in itertools.groupby(buckets, lambda b: b["bucket"]):
            storage = configuration.storage_factory(bucket)
            grp = list(group)
            files = {item['uid']: (zip_path.parent / item['uid']).read_bytes() for item in grp}
            coroutines = [storage.post_object(path=item['path'], content=files[item['uid']], content_type="",
                                              owner=to_group_owner(item["groupId"]), headers=headers)
                          for item in grp]
            await asyncio.gather(*coroutines)
    finally:
        shutil.rmtree(dir_path)

    return {}
