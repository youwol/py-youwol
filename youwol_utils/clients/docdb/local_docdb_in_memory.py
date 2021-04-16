import json
from pathlib import Path
from typing import Mapping, Union, Any, Dict, List

from dataclasses import dataclass, field
from fastapi import HTTPException

from youwol_utils.clients.docdb.models import TableBody, QueryBody, Query, WhereClause, SecondaryIndex
from youwol_utils.clients.utils import get_default_owner


@dataclass(frozen=False)
class LocalDocDbInMemoryClient:

    root_path: Path
    keyspace_name: str

    table_body: TableBody
    version_table: str
    secondary_indexes: List[SecondaryIndex] = field(default_factory=lambda: [])
    data: Any = None

    @property
    def table_name(self):
        return self.table_body.name

    @property
    def base_path(self):
        return self.root_path / self.keyspace_name / self.table_name

    @property
    def data_path(self):
        return self.base_path / "data.json"

    def primary_key_id(self, doc: Dict[str, any]):
        return str([[k, doc[k]] for k in self.table_body.partition_key] +
                   [[k, doc[k]] for k in self.table_body.clustering_columns])

    def __post_init__(self):
        self.data = json.loads(self.data_path.read_text())

    async def delete_table(self, **_kwargs):
        pass

    async def ensure_table(self, **_kwargs):
        pass

    async def clear_data(self, **_kwargs):
        self.data["documents"] = []

    async def get_document(self,  partition_keys: Dict[str, any], clustering_keys: Dict[str, any],
                           owner: Union[str, None], **kwargs):

        where_clauses = [{"column": k, "relation": "eq", "term": partition_keys[k]}
                         for k in self.table_body.partition_key] + \
                        [{"column": k, "relation": "eq", "term": clustering_keys[k]}
                         for k in self.table_body.clustering_columns]

        query = QueryBody(
            max_results=1,
            query=Query(where_clause=where_clauses)
            )

        response = await self.query(
            query_body=query,
            owner=owner,
            **kwargs)

        if not response["documents"]:
            raise HTTPException(status_code=404, detail="document not found in doc_db")

        return response["documents"][0]

    async def query(self, query_body: Union[QueryBody, str],  owner: Union[str, None],
                    headers: Mapping[str, str] = None, **_kwargs):

        if not headers:
            headers = {}
        if not owner:
            owner = get_default_owner(headers)

        if isinstance(query_body, str):
            query_body = QueryBody.parse(query_body)

        if len(query_body.query.ordering_clause) > 1:
            raise Exception("Ordering emulated only for 1 ordering clause")

        eq_clauses = [clause for clause in query_body.query.where_clause if clause.relation == "eq"] + \
                     [WhereClause(column="owner", relation="eq", term=owner)]

        data = self.data["documents"]

        r = [d for d in data if all([d[clause.column] == clause.term for clause in eq_clauses])]
        for ordering in self.table_body.table_options.clustering_order:
            order = ordering.order
            col = ordering.name
            sorted_result = sorted(r, key=lambda doc: doc[col])
            r = sorted_result
            if order == "DESC":
                r.reverse()

        return {"documents": r[0:query_body.max_results]}

    async def create_document(self, doc, owner: Union[str, None], headers: Mapping[str, str] = None, **_kwargs):

        return await self.update_document(doc, owner, headers, **_kwargs)

    async def update_document(self, doc, owner: Union[str, None], headers: Mapping[str, str] = None, **_kwargs):

        if not headers:
            headers = {}
        if not owner:
            owner = get_default_owner(headers)

        doc["owner"] = owner

        index = [i for i, d in enumerate(self.data["documents"]) if self.primary_key_id(d) == self.primary_key_id(doc)]
        if len(index) == 1:
            self.data["documents"][index[0]] = doc
        else:
            self.data["documents"].append(doc)

        return {}

    async def delete_document(self, doc, owner: Union[str, None],  headers: Mapping[str, str] = None,
                              **_kwargs):
        if not headers:
            headers = {}
        if not owner:
            owner = get_default_owner(headers)

        self.data["documents"] = [d for d in self.data["documents"]
                                  if not(self.primary_key_id(d) == self.primary_key_id(doc) and d["owner"] == owner)]

        return {}
