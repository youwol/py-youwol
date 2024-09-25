# standard library
from collections.abc import Callable

# typing
from typing import Any

# third parties
from pydantic import BaseModel


class Column(BaseModel):
    """
    Defines a column for a [scylla-db](https://www.scylladb.com/) table.
    """

    name: str
    """
    Name of the column.
    """
    type: str
    """
    Type of the column.
    """
    static: bool = False
    """
    Whether is it static.
    """
    primary_key: bool = False
    """
    Whether is it part of the primary key.
    """


class OrderingClause(BaseModel):
    """
    Defines ordering clause for a [scylla-db](https://www.scylladb.com/) table.
    """

    name: str
    """
    Name of the target column.
    """
    order: str = "ASC"
    """
    Ordering definition.
    """


class TableOptions(BaseModel):
    """
    Table options for a [scylla-db](https://www.scylladb.com/) table.
    """

    clustering_order: list[OrderingClause] = []
    """
    Clustering order definition.
    """
    comment: str = ""
    """
    Optional comment.
    """


class TableBody(BaseModel):
    """
    [Scylla-db](https://www.scylladb.com/) table definition.
    """

    name: str
    """
    Table name.
    """
    version: str
    """
    Table version.
    """
    columns: list[Column]
    """
    Columns definition.
    """
    partition_key: list[str]
    """
    Partition key definition.
    """
    clustering_columns: list[str] = []
    """
    Clustering columns definition.
    """
    table_options: TableOptions = TableOptions()
    """
    Table options
    """


class IdentifierSI(BaseModel):
    """
    Identifier for secondary index.
    """

    column_name: str
    """
    Column name.
    """


class SecondaryIndex(BaseModel):
    """
    Defines secondary indexes for a [scylla-db](https://www.scylladb.com/) table.
    """

    name: str
    """
    Name of the index.
    """
    identifier: IdentifierSI
    """
    Identifier for the secondary index.
    """


class SelectClause(BaseModel):
    """
    Specify a selector of a query to the indexed database.
    """

    selector: str
    """
    Selector value.
    """


class WhereClause(BaseModel):
    """
    Specify the 'where' clause of a query to the indexed database.
    """

    column: str
    """
    Name of the column.
    """
    relation: str
    """
    Relation expected.
    """
    term: Any
    """
    Term expected.
    """

    def is_matching(self, doc: dict[str, Any]) -> bool:
        factory_clauses: dict[str, Callable[[float, float], bool]] = {
            "eq": lambda _value, _target: value == target,
            "lt": lambda _value, _target: value < target,
            "leq": lambda _value, _target: value <= target,
            "gt": lambda _value, _target: value > target,
            "geq": lambda _value, _target: value >= target,
        }
        target = self.term
        value = doc[self.column]
        if isinstance(value, (float, int)):
            target = float(target)
        return factory_clauses[self.relation](value, target)


class Query(BaseModel):
    """
    Represents a query to the indexed database.
    """

    where_clause: list[WhereClause] = []
    """
    Where clause.
    """
    ordering_clause: list[OrderingClause] = []
    """
    Ordering clause.
    """


class QueryBody(BaseModel):
    """
    Represents the inputs to query entries to the indexed database.
    """

    allow_filtering: bool = False
    """
    Whether or not to allow filtering.
    """
    max_results: int = 100
    """
    Max results count.
    """
    iterator: str | None = None
    """
    Iterator for paging.
    """
    mode: str = "documents"
    distinct: list[str] = []
    select_clauses: list[SelectClause] = []
    """
    Select clauses.
    """
    query: Query
    """
    Actual query.
    """

    @staticmethod
    def parse(query_str):
        def parse_clause(clause: str):
            def parse_clause_specific(symbol, relation):
                return WhereClause(
                    column=clause.split(symbol)[0],
                    relation=relation,
                    term=clause[clause.find(symbol) + len(symbol) :],
                )

            if ">=" in clause:
                return parse_clause_specific(">=", "geq")
            if ">" in clause:
                return parse_clause_specific(">", "gt")
            if "<=" in clause:
                return parse_clause_specific("<=", "leq")
            if "<" in clause:
                return parse_clause_specific("<", "lt")
            if "=" in clause:
                return parse_clause_specific("=", "eq")

        remaining = query_str
        where_clauses_str = query_str
        select_clauses_str = None
        count_str = None
        if "@" in query_str:
            [where_clauses_str, remaining] = query_str.split("@")
            if "#" in remaining:
                [select_clauses_str, count_str] = remaining.split("#")
        elif "#" in remaining:
            [where_clauses_str, count_str] = query_str.split("#")

        if not where_clauses_str:
            where_clauses = []
        else:
            where_clauses = [parse_clause(w) for w in where_clauses_str.split(",")]

        select_clauses = (
            [SelectClause(selector=w) for w in select_clauses_str.split(",")]
            if select_clauses_str
            else []
        )
        return QueryBody(
            max_results=int(count_str) if count_str else 100,
            select_clauses=select_clauses,
            query=Query(where_clause=where_clauses),
        )
