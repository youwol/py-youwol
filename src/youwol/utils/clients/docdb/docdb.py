# standard library
from dataclasses import dataclass, field
from enum import Enum

# typing
from typing import Dict, List, NamedTuple, Union

# third parties
import aiohttp

from aiohttp import ClientResponse

# Youwol utilities
from youwol.utils.clients.docdb.models import (
    Query,
    QueryBody,
    SecondaryIndex,
    TableBody,
    WhereClause,
)
from youwol.utils.clients.utils import aiohttp_resp_parameters
from youwol.utils.exceptions import raise_exception_from_response


def patch_query_body(query_body: QueryBody, table_body: TableBody) -> QueryBody:
    """
    This function is a workaround for queries involving columns with types ['int','bigint']
    (maybe other types suffer from the same problem but have not been revealed so far).
    In those cases, 'where_clauses.term' should be 'str(target_value)' and not 'target_value' as one can expect.
    """
    column_types = {col.name: col.type for col in table_body.columns}

    def patch_clause(clause: WhereClause, types: Dict[str, str]) -> WhereClause:
        if types[clause.column] in ["int", "bigint"]:
            return WhereClause(
                column=clause.column, relation=clause.relation, term=f"{clause.term}"
            )
        return clause

    query_body_corrected = QueryBody(
        allow_filtering=query_body.allow_filtering,
        max_results=query_body.max_results,
        iterator=query_body.iterator,
        mode=query_body.mode,
        distinct=query_body.distinct,
        select_clauses=query_body.select_clauses,
        query=Query(
            where_clause=[
                patch_clause(c, column_types) for c in query_body.query.where_clause
            ],
            ordering_clause=query_body.query.ordering_clause,
        ),
    )
    return query_body_corrected


def post_keyspace_body(name: str, replication_factor: int):
    return {
        "name": name,
        "replication": {
            "class": "SimpleStrategy",
            "replication_factor": replication_factor,
        },
        "durable_writes": True,
    }


class UpdateType(Enum):
    MINOR_UPDATE = 1
    MAJOR_UPDATE = 2
    NONE = 3


class Update(NamedTuple):
    type: UpdateType
    current_minor: Union[int, None]
    current_major: Union[int, None]
    new_minor: int
    new_major: int


def get_update_description(previous_table: Dict[str, any], current_version: str):
    new_major = int(current_version.split(".")[0])
    new_minor = int(current_version.split(".")[1])

    current_version = previous_table["table_options"]["comment"].split("#")[1]
    current_major = int(current_version.split(".")[0])
    current_minor = int(current_version.split(".")[1])

    if new_major == current_major and new_minor == current_minor:
        return Update(
            type=UpdateType.NONE,
            current_major=current_major,
            current_minor=current_minor,
            new_major=new_major,
            new_minor=new_minor,
        )

    if new_major != current_major:
        return Update(
            type=UpdateType.MAJOR_UPDATE,
            current_major=current_major,
            current_minor=current_minor,
            new_major=new_major,
            new_minor=new_minor,
        )

    return Update(
        type=UpdateType.MINOR_UPDATE,
        current_major=current_major,
        current_minor=current_minor,
        new_major=new_major,
        new_minor=new_minor,
    )


@dataclass(frozen=True)
class DocDbClient:
    version_service = "v0-alpha1"
    table_body: TableBody
    url_base: str
    keyspace_name: str

    replication_factor: int

    headers: Dict[str, str] = field(default_factory=lambda: {})
    connector = aiohttp.TCPConnector(verify_ssl=False)

    secondary_indexes: List[SecondaryIndex] = field(default_factory=lambda: [])

    async def raise_exception(self, resp: ClientResponse, **kwargs):
        params = {
            "url_base": self.url_base,
            "keyspace": self.keyspace_name,
            "table": self.table_name,
            "replication_factor": self.replication_factor,
        }
        await raise_exception_from_response(
            resp, **kwargs, **params, **aiohttp_resp_parameters(resp)
        )

    @property
    def table_name(self):
        return self.table_body.name

    @property
    def keyspaces_url(self):
        return f"{self.url_base}/{self.version_service}/keyspaces"

    @property
    def keyspace_url(self):
        return f"{self.url_base}/{self.version_service}/keyspace/{self.keyspace_name}"

    @property
    def post_keyspace_url(self):
        return f"{self.url_base}/{self.version_service}/keyspace"

    @property
    def tables_url(self):
        return f"{self.url_base}/{self.version_service}/{self.keyspace_name}/tables"

    @property
    def post_table_url(self):
        return f"{self.url_base}/{self.version_service}/{self.keyspace_name}/table"

    @property
    def table_url(self):
        return f"{self.url_base}/{self.version_service}/{self.keyspace_name}/table/{self.table_name}"

    @property
    def query_url(self):
        return f"{self.url_base}/{self.version_service}/{self.keyspace_name}/{self.table_name}/query"

    @property
    def post_index_url(self):
        return f"{self.url_base}/{self.version_service}/{self.keyspace_name}/{self.table_name}/index"

    @property
    def document_url(self):
        return f"{self.url_base}/{self.version_service}/{self.keyspace_name}/{self.table_name}/document"

    async def _keyspace_exists(self, **kwargs) -> bool:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=self.keyspaces_url, **kwargs) as resp:
                if resp.status == 200:
                    resp_json = await resp.json()
                    return self.keyspace_name in resp_json
                await self.raise_exception(resp, message="Can not get the keyspace")

    async def _table_exists(self, **kwargs) -> bool:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=self.tables_url, **kwargs) as resp:
                if resp.status == 200:
                    resp_json = await resp.json()
                    return self.table_name in resp_json
                await self.raise_exception(resp, message="Can not get the table")

    async def delete_table(self, **kwargs):
        if not await self._keyspace_exists(**kwargs) or not await self._table_exists(
            **kwargs
        ):
            return

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=self.table_url, **kwargs) as resp:
                if resp.status == 200:
                    resp_json = await resp.text()
                    print(f"table {self.table_name} deleted", resp_json)
                    return resp_json
                await self.raise_exception(resp, message="Deletion of the table failed")

    async def _create_keyspace(self, **kwargs):
        body_json = post_keyspace_body(self.keyspace_name, self.replication_factor)

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.post_keyspace_url, json=body_json, **kwargs
            ) as resp:
                if resp.status == 201:
                    print(f"keyspace '{self.keyspace_name}' created")
                    return

                await self.raise_exception(
                    resp, message="Creation of the keyspace failed"
                )

    async def _create_table(self, **kwargs):
        body = self.table_body.dict()
        body["table_options"]["comment"] += f" #{self.table_body.version}#"
        if not self.table_body.clustering_columns:
            del body["clustering_columns"]
            del body["table_options"]["clustering_order"]

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.post_table_url, json=body, **kwargs
            ) as resp:
                if resp.status == 201:
                    print(f"table '{self.table_name}' created")
                    return

                await self.raise_exception(resp, message="Creation of the table failed")

    async def _create_index(self, index: SecondaryIndex, **kwargs):
        body = index.dict()

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.post_index_url, json=body, **kwargs
            ) as resp:
                if resp.status == 201:
                    print(f"secondary index '{index.name}' created")
                    return

                await self.raise_exception(resp, message="Creation of the index failed")

    async def ensure_table(self, **kwargs):
        if not await self._keyspace_exists(**kwargs):
            print(f"keyspace {self.keyspace_name} does not exist")
            await self._create_keyspace(**kwargs)
        else:
            print(f"keyspace {self.keyspace_name} exists")

        table_exist = await self._table_exists(**kwargs)

        if table_exist:
            table = await self.get_table(**kwargs)
            update = get_update_description(table, self.table_body.version)

            if update.type == UpdateType.MAJOR_UPDATE:
                raise RuntimeError(
                    f"Major update needs to be manually done {str(update)}"
                )

            if update.type == UpdateType.MINOR_UPDATE:
                print(
                    f"Table '{self.table_name}' needs minor update, apply auto update ({str(update)})"
                )
                raise NotImplementedError("Auto update not implemented")

            if update.type == UpdateType.NONE:
                print(f"Table '{self.table_name}' schema up-to-date")

        if not table_exist:
            print(f"table '{self.table_name}' does not exist")
            await self._create_table(**kwargs)
            for index in self.secondary_indexes:
                await self._create_index(index, **kwargs)

    async def get_table(self, **kwargs):
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=self.table_url, **kwargs) as resp:
                if resp.status == 200:
                    table = await resp.json()
                    return table

                await self.raise_exception(resp, message="Can not get the table")

    async def get_document(
        self,
        partition_keys: Dict[str, any],
        clustering_keys: Dict[str, any],
        owner: Union[str, None],
        **kwargs,
    ):
        params = {"owner": owner}
        params_part = self.get_primary_key_query_parameters(
            {**partition_keys, **clustering_keys}
        )

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(
                url=self.document_url + params_part, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

                await self.raise_exception(
                    resp, message="Can not get the document", params=params
                )

    async def query(
        self, query_body: Union[QueryBody, str], owner: Union[str, None], **kwargs
    ):
        if isinstance(query_body, str):
            query_body = QueryBody.parse(query_body)

        query_body = patch_query_body(query_body=query_body, table_body=self.table_body)

        params = {"owner": owner} if owner else {}
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.query_url, json=query_body.dict(), params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return {"documents": resp["documents"][0 : query_body.max_results]}

                await self.raise_exception(
                    resp, message="Query failed", params=params, query_body=query_body
                )

    async def create_document(self, doc, owner: Union[str, None], **kwargs):
        params = {"owner": owner} if owner else {}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.document_url, json=doc, params=params, **kwargs
            ) as resp:
                if resp.status == 201:
                    return await resp.json()
                await self.raise_exception(
                    resp, message="Can not create the document", params=params, doc=doc
                )

    async def update_document(self, doc, owner: Union[str, None], **kwargs):
        params = {"owner": owner} if owner else {}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(
                url=self.document_url, json=doc, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                await self.raise_exception(
                    resp, message="Can not update the document", params=params, doc=doc
                )

    async def delete_document(
        self, doc: Dict[str, any], owner: Union[str, None], **kwargs
    ):
        params_part = self.get_primary_key_query_parameters(doc)
        params = {"owner": owner} if owner else {}
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(
                url=self.document_url + params_part, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                await self.raise_exception(
                    resp,
                    message="Can not delete the document",
                    params=params_part,
                    doc=doc,
                )

    def get_primary_key_query_parameters(self, doc: Dict[str, any]):
        if (
            len(self.table_body.partition_key) == 1
            and len(self.table_body.clustering_columns) == 0
        ):
            return f"?partitionKey={doc[self.table_body.partition_key[0]]}"

        if (
            len(self.table_body.partition_key) == 1
            and len(self.table_body.clustering_columns) == 1
        ):
            return (
                f"?partitionKey={doc[self.table_body.partition_key[0]]}&"
                + f"clusteringKey={doc[self.table_body.clustering_columns[0]]}"
            )

        if (
            len(self.table_body.partition_key) == 2
            and len(self.table_body.clustering_columns) == 1
        ):
            return (
                f"?partitionKey=({doc[self.table_body.partition_key[0]]},"
                + f"{doc[self.table_body.partition_key[1]]})& "
                + f"clusteringKey={doc[self.table_body.clustering_columns[0]]}"
            )

        if (
            len(self.table_body.partition_key) == 1
            and len(self.table_body.clustering_columns) == 2
        ):
            return (
                f"?partitionKey={doc[self.table_body.partition_key[0]]}&"
                + f"clusteringKey=({doc[self.table_body.clustering_columns[0]]}, "
                + f"{doc[self.table_body.clustering_columns[1]]})"
            )

        raise NotImplementedError()
