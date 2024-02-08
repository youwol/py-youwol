# standard library
from dataclasses import dataclass, field
from enum import Enum

# typing
from typing import Any, NamedTuple

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
from youwol.utils.exceptions import upstream_exception_from_response
from youwol.utils.types import AnyDict


def patch_query_body(query_body: QueryBody, table_body: TableBody) -> QueryBody:
    """
    This function is a workaround for queries involving columns with types ['int','bigint']
    (maybe other types suffer from the same problem but have not been revealed so far).
    In those cases, 'where_clauses.term' should be 'str(target_value)' and not 'target_value' as one can expect.
    """
    column_types = {col.name: col.type for col in table_body.columns}

    def patch_clause(clause: WhereClause, types: dict[str, str]) -> WhereClause:
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
    current_minor: int | None
    current_major: int | None
    new_minor: int
    new_major: int


def get_update_description(previous_table: dict[str, Any], current_version: str):
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
    """

    Remote indexed database implementation following [scyllaDB](https://www.scylladb.com/) concepts.
    """

    version_service = "v0-alpha1"

    table_body: TableBody
    """
    Table definition.
    """

    url_base: str
    """
    Base URL serving the remote service.
    """

    keyspace_name: str
    """
    Keyspace name
    """

    replication_factor: int
    """
    Replication factor
    """

    headers: dict[str, str] = field(default_factory=lambda: {})
    """
    Default headers to pass to the HTTP calls.
    """
    connector = aiohttp.TCPConnector(verify_ssl=False)
    """
    Connector use for HTTP calls.
    """

    secondary_indexes: list[SecondaryIndex] = field(default_factory=lambda: [])
    """
    Secondary indexes pf the table.
    """

    async def get_upstsream_exception(self, resp: ClientResponse, **kwargs):
        params = {
            "url_base": self.url_base,
            "keyspace": self.keyspace_name,
            "table": self.table_name,
            "replication_factor": self.replication_factor,
        }
        return await upstream_exception_from_response(
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
                raise await self.get_upstsream_exception(
                    resp, message="Can not get the keyspace"
                )

    async def _table_exists(self, **kwargs) -> bool:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=self.tables_url, **kwargs) as resp:
                if resp.status == 200:
                    resp_json = await resp.json()
                    return self.table_name in resp_json
                raise await self.get_upstsream_exception(
                    resp, message="Can not get the table"
                )

    async def delete_table(self, **kwargs) -> AnyDict:
        """
        Delete the table.

        Parameters:
            kwargs: keywords arg. forwarded to internal calls.

        Return:
            Response of the service.
        """
        if not await self._keyspace_exists(**kwargs) or not await self._table_exists(
            **kwargs
        ):
            return {}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(url=self.table_url, **kwargs) as resp:
                if resp.status == 200:
                    resp_json = await resp.json()
                    print(f"table {self.table_name} deleted", resp_json)
                    return resp_json
                raise await self.get_upstsream_exception(
                    resp, message="Deletion of the table failed"
                )

    async def _create_keyspace(self, **kwargs):
        body_json = post_keyspace_body(self.keyspace_name, self.replication_factor)

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.post_keyspace_url, json=body_json, **kwargs
            ) as resp:
                if resp.status == 201:
                    print(f"keyspace '{self.keyspace_name}' created")
                    return

                raise await self.get_upstsream_exception(
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

                raise await self.get_upstsream_exception(
                    resp, message="Creation of the table failed"
                )

    async def _create_index(self, index: SecondaryIndex, **kwargs):
        body = index.dict()

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.post_index_url, json=body, **kwargs
            ) as resp:
                if resp.status == 201:
                    print(f"secondary index '{index.name}' created")
                    return

                raise await self.get_upstsream_exception(
                    resp, message="Creation of the index failed"
                )

    async def ensure_table(self, **kwargs):
        """
        Ensure the table exists, creates it if needed.

        Parameters:
            kwargs: keywords arg. forwarded to internal calls.

        Return:
            Response of the service.
        """
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

    async def get_table(self, **kwargs) -> AnyDict:
        """
        Get description of a table.

        Parameters:
            kwargs: keywords arg. forwarded to internal calls.

        Return:
            Response of the service.
        """
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(url=self.table_url, **kwargs) as resp:
                if resp.status == 200:
                    table = await resp.json()
                    return table

                raise await self.get_upstsream_exception(
                    resp, message="Can not get the table"
                )

    async def get_document(
        self,
        partition_keys: dict[str, Any],
        clustering_keys: dict[str, Any],
        owner: str | None,
        **kwargs,
    ) -> AnyDict:
        """
        Get a document based on partition and clustering keys.

        Parameters:
            partition_keys: The partition keys.
            clustering_keys: The clustering keys.
            owner: The owner of the document. Please provide always `youwol-users`.
            kwargs:  keywords arg. forwarded to internal calls.

        Return:
            The retrieved document.
        """
        params = {"owner": owner}
        params_part = self.get_primary_key_query_parameters(
            {**partition_keys, **clustering_keys}
        )

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.get(
                url=self.document_url + params_part, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()

                raise await self.get_upstsream_exception(
                    resp, message="Can not get the document", params=params
                )

    async def query(
        self,
        query_body: QueryBody | str,
        owner: str | None,
        **kwargs,
    ) -> AnyDict:
        """
        Execute a query on the table.

        Parameters:
            query_body: The query body.
            owner: The owner of the document. Please provide always `youwol-users`.
            kwargs:  keywords arg. forwarded to internal calls.

        Return:
            The query result.
        """
        typed_query_body = patch_query_body(
            query_body=(
                QueryBody.parse(query_body)
                if isinstance(query_body, str)
                else query_body
            ),
            table_body=self.table_body,
        )

        params = {"owner": owner} if owner else {}
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.query_url,
                json=typed_query_body.dict(),
                params=params,
                **kwargs,
            ) as resp:
                if resp.status == 200:
                    resp_json_body = await resp.json()
                    return {
                        "documents": resp_json_body["documents"][
                            0 : typed_query_body.max_results
                        ]
                    }

                raise await self.get_upstsream_exception(
                    resp,
                    message="Query failed",
                    params=params,
                    query_body=typed_query_body,
                )

    async def create_document(
        self, doc: AnyDict, owner: str | None, **kwargs
    ) -> AnyDict:
        """
        Create a new document in the database.

        Parameters:
            doc: The document to create.
            owner: The owner of the document. Please provide always `youwol-users`.
            kwargs:  keywords arg. forwarded to internal calls.

        Return:
            Response from the service.
        """
        params = {"owner": owner} if owner else {}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.post(
                url=self.document_url, json=doc, params=params, **kwargs
            ) as resp:
                if resp.status == 201:
                    return await resp.json()
                raise await self.get_upstsream_exception(
                    resp, message="Can not create the document", params=params, doc=doc
                )

    async def update_document(
        self, doc: AnyDict, owner: str | None, **kwargs
    ) -> AnyDict:
        """
        Update a new document in the database.

        Parameters:
            doc: Updated document.
            owner: The owner of the document. Please provide always `youwol-users`.
            kwargs:  keywords arg. forwarded to internal calls.

        Return:
            Response from the service.
        """
        params = {"owner": owner} if owner else {}

        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.put(
                url=self.document_url, json=doc, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                raise await self.get_upstsream_exception(
                    resp, message="Can not update the document", params=params, doc=doc
                )

    async def delete_document(self, doc: dict[str, Any], owner: str | None, **kwargs):
        """
        Delete a document from the database.

        Parameters:
            doc: Primary key of the document.
            owner: The owner of the document. Please provide always `youwol-users`.
            kwargs:  keywords arg. forwarded to internal calls.

        Return:
            Empty JSON object.
        """
        params_part = self.get_primary_key_query_parameters(doc)
        params = {"owner": owner} if owner else {}
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with await session.delete(
                url=self.document_url + params_part, params=params, **kwargs
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                raise await self.get_upstsream_exception(
                    resp,
                    message="Can not delete the document",
                    params=params_part,
                    doc=doc,
                )

    def get_primary_key_query_parameters(self, doc: dict[str, Any]):
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
