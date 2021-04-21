from typing import List, Any

from pydantic import BaseModel


class Column(BaseModel):
    name: str
    type: str
    static: bool = False
    primary_key: bool = False


class OrderingClause(BaseModel):
    name: str
    order: str = "ASC"


class TableOptions(BaseModel):
    clustering_order: List[OrderingClause] = []
    comment: str = ""


class TableBody(BaseModel):
    name: str
    columns: List[Column]
    partition_key: List[str]
    clustering_columns: List[str] = []
    table_options: TableOptions = TableOptions()


class IdentifierSI(BaseModel):
    column_name: str


class SecondaryIndex(BaseModel):
    name: str
    identifier: IdentifierSI


class SelectClause(BaseModel):
    selector: str


class WhereClause(BaseModel):
    column: str
    relation: str
    term: Any


class Query(BaseModel):
    where_clause: List[WhereClause] = []
    ordering_clause: List[OrderingClause] = []


class QueryBody(BaseModel):
    allow_filtering: bool = False
    max_results: int = 100
    iterator: str = None
    mode: str = "documents"
    distinct: List[str] = []
    select_clauses: List[SelectClause] = []
    query: Query

    @staticmethod
    def parse(query_str):
        remaining = query_str
        where_clauses_str = query_str
        select_clauses_str = None
        count_str = None
        if '@' in query_str:
            [where_clauses_str, remaining] = query_str.split('@')
            if '#' in remaining:
                [select_clauses_str, count_str] = remaining.split('#')
        elif '#' in remaining:
            [where_clauses_str, count_str] = query_str.split('#')

        if where_clauses_str == "":
            where_clauses = []
        else:
            where_clauses = [WhereClause(column=w.split('=')[0], relation='eq', term=w[w.find('=') + 1:])
                             for w in where_clauses_str.split(',')]

        select_clauses = [SelectClause(selector=w) for w in select_clauses_str.split(',')] if select_clauses_str else []
        return QueryBody(max_results=int(count_str) if count_str else 100,
                         select_clauses=select_clauses,
                         query=Query(where_clause=where_clauses))
