import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Union, Dict, List

from fastapi import HTTPException

from youwol_utils.clients.docdb.models import TableBody, QueryBody, WhereClause, Query, SecondaryIndex
from youwol_utils.clients.utils import get_default_owner


@dataclass(frozen=True)
class LocalDocDbClient:

    root_path: Path
    keyspace_name: str
    table_body: TableBody
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

    def primary_key_id(self, doc: Dict[str, any]):
        return str([[k, doc[k]] for k in self.table_body.partition_key] +
                   [[k, doc[k]] for k in self.table_body.clustering_columns])

    async def delete_table(self, **_kwargs):
        if self.base_path.exists():
            shutil.rmtree(self.base_path)

    async def ensure_table(self, **_kwargs):

        self.base_path.mkdir(parents=True, exist_ok=True)

        if not self.data_path.exists():
            self.data_path.open('w').write('{"documents":[]}')

        return True

    async def clear_data(self, **_kwargs):
        self.data_path.open('w').write('{"documents":[]}')

    async def get_document(self, partition_keys: Dict[str, any], clustering_keys: Dict[str, any],
                           owner: Union[str, None], allow_filtering: bool = False,  **kwargs):

        valid_for_indexes = [all([k in partition_keys for k in self.table_body.partition_key])] +\
                            [len(partition_keys.keys()) == 1 and
                             index.identifier.column_name == list(partition_keys.keys())[0]
                             for index in self.secondary_indexes]

        query_valid = any(valid_for_indexes)

        if not allow_filtering and not query_valid:
            raise Exception("The query can not proceed")

        where_clauses = [{"column": k, "relation": "eq", "term": partition_keys[k]}
                         for k in partition_keys.keys()] + \
                        [{"column": k, "relation": "eq", "term": clustering_keys[k]}
                         for k in clustering_keys.keys()]

        query = QueryBody(
            max_results=1,
            query=Query(where_clause=where_clauses)
            )

        response = await self.query(
            query_body=query,
            owner=owner,
            **kwargs)

        if not response["documents"]:
            raise HTTPException(status_code=404, detail="document not found in doc_db: "+str(where_clauses))

        return response["documents"][0]

    async def query(self, query_body: Union[QueryBody, str], owner: Union[str, None],
                    headers: Mapping[str, str] = None, **_kwargs):

        if not headers:
            headers = {}

        if not owner:
            owner = get_default_owner(headers)

        if isinstance(query_body, str):
            query_body = QueryBody.parse(query_body)

        if len(query_body.query.ordering_clause) > 1:
            raise Exception("Ordering emulated only for 1 ordering clause")

        data = json.loads(self.data_path.read_text())["documents"]

        where_clauses = [WhereClause(column="owner", relation="eq", term=owner)] + query_body.query.where_clause

        def is_matching(doc):
            for clause in where_clauses:
                matching = clause.is_matching(doc)
                if not matching:
                    return False
            return True

        r = [doc for doc in data if is_matching(doc)]

        query_ordering = {clause.name: clause.order for clause in query_body.query.ordering_clause}
        for ordering in self.table_body.table_options.clustering_order:
            order = ordering.order
            col = ordering.name
            sorted_result = sorted(r, key=lambda doc: doc[col])
            r = sorted_result
            if order == "DESC" or (col in query_ordering and query_ordering[col] == "DESC"):
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

        data = json.load(self.data_path.open('r')) if self.data_path.exists() else {"documents": []}
        index = [i for i, d in enumerate(data["documents"]) if self.primary_key_id(d) == self.primary_key_id(doc)]
        if len(index) == 1:
            data["documents"][index[0]] = doc
        else:
            data["documents"].append(doc)

        self.data_path.open('w').write(json.dumps(data, indent=4))
        return {}

    async def delete_document(self, doc: Dict[str, any], owner: Union[str, None],  headers: Mapping[str, str] = None,
                              **_kwargs):

        if not headers:
            headers = {}
        if not owner:
            owner = get_default_owner(headers)

        data = json.load(self.data_path.open())

        data["documents"] = [d for d in data["documents"]
                             if not(self.primary_key_id(d) == self.primary_key_id(doc) and d["owner"] == owner)]

        self.data_path.write_text(json.dumps(data, indent=4))
        return {}
