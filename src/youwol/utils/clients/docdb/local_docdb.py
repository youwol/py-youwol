# standard library
import json
import shutil

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

# typing
from typing import Any, Dict, List, Mapping, Optional, Union

# third parties
from fastapi import HTTPException

# Youwol utilities
from youwol.utils.clients.docdb.models import (
    Query,
    QueryBody,
    SecondaryIndex,
    TableBody,
    WhereClause,
)
from youwol.utils.clients.utils import get_default_owner
from youwol.utils.http_clients.cdn_backend.utils import (
    create_local_scylla_db_docs_file_if_needed,
)
from youwol.utils.utils import JSON


def get_local_nosql_instance(
    root_path: Path,
    keyspace_name: str,
    table_body: TableBody,
    secondary_indexes: List[SecondaryIndex],
):
    path = root_path / keyspace_name / table_body.name / "data.json"
    create_local_scylla_db_docs_file_if_needed(path)
    data = json.loads(path.read_text())
    return LocalDocDbClient(
        root_path=root_path,
        keyspace_name=keyspace_name,
        table_body=table_body,
        data=data,
        secondary_indexes=secondary_indexes,
    )


@dataclass(frozen=True)
class LocalDocDbClient:
    """
    Local indexed database implementation following [scyllaDB](https://www.scylladb.com/) concepts and supported
     by a single JSON file.

    The path of this file is `f"{self.root_path}/{self.keyspace_name}/{self.table_body.name}/data.json"`
    """

    __lock = Lock()
    """
    Lock handle to prevent concurrent issues.
    """

    root_path: Path
    """
    Root path part of the `data.json` file.
    """

    keyspace_name: str
    """
    Keyspace name.
    """

    table_body: TableBody
    """
    Table definition.
    """

    data: Any = field(default_factory=lambda: {"documents": []})
    secondary_indexes: List[SecondaryIndex] = field(default_factory=lambda: [])

    @property
    def table_name(self):
        return self.table_body.name

    @property
    def base_path(self):
        return self.root_path / self.keyspace_name / self.table_name

    @property
    def data_path(self):
        return self.base_path / "data.json"

    @property
    def metadata_path(self):
        return self.base_path / "metadata.json"

    def primary_key_id(self, doc: Dict[str, any]) -> str:
        """
        Get the primary key identifier for a document.

        Parameters:
            doc: The document.

        Return:
            The primary key identifier.
        """
        return str(
            [[k, doc[k]] for k in self.table_body.partition_key]
            + [[k, doc[k]] for k in self.table_body.clustering_columns]
        )

    async def delete_table(self, **_kwargs: Dict[str, Any]) -> None:
        """
        Delete the table and its data.

        Parameters:
            _kwargs: Additional keyword arguments.
        """
        if self.base_path.exists():
            shutil.rmtree(self.base_path)

    @staticmethod
    async def ensure_table() -> bool:
        """
        Ensure the existence of the table.

        Return:
            Whether the table already existed.
        """
        return True

    async def get_document(
        self,
        partition_keys: Dict[str, any],
        clustering_keys: Dict[str, any],
        owner: Optional[str] = None,
        allow_filtering: bool = False,
        **kwargs: Dict[str, Any],
    ) -> JSON:
        """
        Get a document based on partition and clustering keys.

        Parameters:
            partition_keys: The partition keys.
            clustering_keys: The clustering keys.
            owner: Deprecated: do not provide.
            allow_filtering: Whether to allow filtering (default: False).
            kwargs: Additional keyword arguments.

        Return:
            The retrieved document.
        """
        valid_for_indexes = [
            all(k in partition_keys for k in self.table_body.partition_key)
        ] + [
            len(partition_keys.keys()) == 1
            and index.identifier.column_name == list(partition_keys.keys())[0]
            for index in self.secondary_indexes
        ]

        query_valid = any(valid_for_indexes)

        if not allow_filtering and not query_valid:
            raise RuntimeError("The query can not proceed")

        where_clauses = [
            WhereClause(column=k, relation="eq", term=partition_keys[k])
            for k in partition_keys.keys()
        ] + [
            WhereClause(column=k, relation="eq", term=clustering_keys[k])
            for k in clustering_keys.keys()
        ]

        query = QueryBody(max_results=1, query=Query(where_clause=where_clauses))

        response = await self.query(query_body=query, owner=owner, **kwargs)

        if not response["documents"]:
            raise HTTPException(
                status_code=404,
                detail="document not found in doc_db: " + str(where_clauses),
            )

        return response["documents"][0]

    async def query(
        self,
        query_body: Union[QueryBody, str],
        owner: Union[str, None],
        headers: Mapping[str, str] = None,
        **_kwargs: Dict[str, Any],
    ) -> JSON:
        """
        Execute a query on the table.

        Parameters:
            query_body: The query body.
            owner: Deprecated: do not provide.
            headers: Deprecated: do not provide.
            _kwargs: Additional keyword arguments.

        Return:
            The query result.
        """

        if not headers:
            headers = {}

        if not owner:
            owner = get_default_owner(headers)

        if isinstance(query_body, str):
            query_body = QueryBody.parse(query_body)

        if len(query_body.query.ordering_clause) > 1:
            raise RuntimeError("Ordering emulated only for 1 ordering clause")

        where_clauses = [
            WhereClause(column="owner", relation="eq", term=owner)
        ] + query_body.query.where_clause

        def is_matching(doc):
            for clause in where_clauses:
                matching = clause.is_matching(doc)
                if not matching:
                    return False
            return True

        documents = self.data["documents"]
        r = [doc for doc in documents if is_matching(doc)]

        query_ordering = {
            clause.name: clause.order for clause in query_body.query.ordering_clause
        }
        for ordering in self.table_body.table_options.clustering_order:
            order = ordering.order
            col = ordering.name
            sorted_result = sorted(r, key=lambda doc, c=col: doc[c])
            r = sorted_result
            if order == "DESC" or (
                col in query_ordering and query_ordering[col] == "DESC"
            ):
                r.reverse()

        return {"documents": r[0 : query_body.max_results]}

    async def create_document(
        self,
        doc: JSON,
        owner: Optional[str] = None,
        headers: Mapping[str, str] = None,
        **_kwargs: Dict[str, Any],
    ) -> {}:
        """
        Create a new document in the database.

        Parameters:
            doc: The document to create.
            owner: Deprecated: do not provide.
            headers: Deprecated: do not provide.
            _kwargs: Additional keyword arguments.

        Return:
            Empty JSON object
        """
        return await self.update_document(doc, owner, headers, **_kwargs)

    async def update_document(
        self,
        doc: JSON,
        owner: Optional[str] = None,
        headers: Mapping[str, str] = None,
        **_kwargs: Dict[str, Any],
    ):
        """
        Update an existing document in the database.

        Parameters:
            doc: The document to create.
            owner: Deprecated: do not provide.
            headers: Deprecated: do not provide.
            _kwargs: Additional keyword arguments.

        Return:
            Empty JSON object
        """
        if not headers:
            headers = {}
        if not owner:
            owner = get_default_owner(headers)

        doc["owner"] = owner
        with self.__lock:
            documents = self.data["documents"]
            index = [
                i
                for i, d in enumerate(documents)
                if self.primary_key_id(d) == self.primary_key_id(doc)
            ]
            if len(index) == 1:
                documents[index[0]] = doc
            else:
                documents.append(doc)
            self.__persist()
        return {}

    async def delete_document(
        self,
        doc: JSON,
        owner: Optional[str] = None,
        headers: Mapping[str, str] = None,
        **_kwargs: Dict[str, Any],
    ) -> {}:
        """
        Delete a document from the database.

        Parameters:
            doc: Primary key of the document.
            owner: Deprecated: do not provide.
            headers: Deprecated: do not provide.
            _kwargs: Additional keyword arguments.

        Return:
            Empty JSON object.
        """

        if not headers:
            headers = {}
        if not owner:
            owner = get_default_owner(headers)

        with self.__lock:
            documents = self.data["documents"]
            items_to_remove = [
                d
                for d in documents
                if self.primary_key_id(d) == self.primary_key_id(doc)
                and d["owner"] == owner
            ]
            for item in items_to_remove:
                documents.remove(item)

            self.__persist()
        return {}

    def __persist(self):
        # should be called within a mutex section
        self.data_path.write_text(data=json.dumps(self.data, indent=4))

    def reset(self) -> None:
        """
        Reset the database to an empty state.
        """
        with self.__lock:
            self.data["documents"] = []
            self.__persist()
