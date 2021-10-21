import asyncio
import math
import time

from .configurations import Configuration
from youwol_utils import log_info


async def init_resources(config: Configuration):
    log_info("Ensure database resources")
    headers = await config.admin_headers if config.admin_headers else {}

    log_info("Successfully retrieved authorization for resources creation")
    await asyncio.gather(
        config.doc_db_stories.ensure_table(headers=headers),
        config.doc_db_documents.ensure_table(headers=headers),
        config.storage.ensure_bucket(headers=headers)
        )
    log_info("resources initialization done")


async def query_document(document_id: str, configuration: Configuration, headers):
    docs = await configuration.doc_db_documents.query(
        query_body=f"document_id={document_id}#1",
        owner=Configuration.default_owner,
        headers=headers
        )
    return docs['documents'][0]


def position_start():
    t = time.time()
    delta = t - math.floor(t)
    return position_format(5e5+delta)


def position_next(index: str):
    t = time.time()
    delta = t - math.floor(t)
    return position_format(math.floor(float(index))+1+delta)


def position_format(index: float):
    decimal = "{:.6f}".format(index)
    return (6-len(decimal.split('.')[0]))*"0"+decimal
