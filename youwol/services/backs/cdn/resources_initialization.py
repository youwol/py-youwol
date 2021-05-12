import asyncio
import os

from youwol_utils import WhereClause, QueryBody, Query, Path, flatten
from .configurations import Configuration

from .utils import format_download_form, post_storage_by_chunk, md5_from_folder
from .utils_indexing import format_doc_db_record, post_indexes


async def init_resources(config: Configuration):
    print("### Ensure database resources ###")
    headers = await config.admin_headers if config.admin_headers else {}
    doc_db = config.doc_db
    storage = config.storage
    table_ok, bucket_ok = await asyncio.gather(
        doc_db.ensure_table(headers=headers),
        storage.ensure_bucket(headers=headers)
        )
    if bucket_ok and not table_ok:
        print("Need to re-index stuffs of bucket")
        raise Exception("The table index is not up-to-date w/ bucket content, manual index-synchronisation needed")

    clauses = [[WhereClause(column="library_name", relation="eq", term=lib.split("#")[0]),
                WhereClause(column="version", relation="eq", term=lib.split("#")[1])]
               for lib in Configuration.required_libs]
    bodies = [QueryBody(query=Query(where_clause=c)) for c in clauses]

    responses = await asyncio.gather(*[doc_db.query(query_body=b, owner=Configuration.owner, headers=headers)
                                       for b in bodies])

    if all([len(r['documents']) == 1 for r in responses]):
        print("Found required resources")
        return

    print("post initial resources")
    await synchronize( Path(__file__).parent / "initial_resources", "", config, headers=headers)

    print("### resources initialization done ###")


async def synchronize(dir_path: Path, zip_dir_name: str, configuration: any, headers: any):

    paths = flatten([[Path(root) / f for f in files] for root, _, files in os.walk(str(dir_path))])
    paths = list(paths)
    forms = [format_download_form(path, Path(), dir_path / zip_dir_name, False) for path in paths]

    await post_storage_by_chunk(configuration.storage, forms, 1, headers)

    paths_index = flatten([[Path(root) / f for f in files if f == "package.json"]
                           for root, _, files in os.walk(str(dir_path))])

    check_dum = md5_from_folder(dir_path)

    indexes = [format_doc_db_record(package_path=path, fingerprint=check_dum) for path in paths_index]
    namespaces = {d["namespace"] for d in indexes}
    await post_indexes(configuration.doc_db, indexes, 25, headers)

    return len(forms), len(indexes), namespaces
