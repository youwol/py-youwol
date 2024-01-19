# typing
from typing import Any


def compare_schemas(left: dict[str, Any], right: dict[str, Any]):
    left_dict = {c["name"]: c["type"] for c in left["columns"]}
    right_dict = {c["name"]: c["type"] for c in right["columns"]}
    left_ok = all(right_dict.get(k, None) == v for k, v in left_dict.items())
    right_ok = all(left_dict.get(k, None) == v for k, v in right_dict.items())

    partition_key_ok = str(left["partition_key"]) == str(right["partition_key"])
    clustering_ok = str(left["clustering_columns"]) == str(right["clustering_columns"])
    return left_ok and right_ok and partition_key_ok and clustering_ok


def patch_table_schema(table: dict[str, Any]):
    """
    When getting table the schema returned include implementation details as columns (e.g. owner_id, owner_name, etc.),
    we want to remove those columns here such that we recover the schema that we initially posted
    """
    to_remove = ["owner_id", "owner_name", "owner_kind"]
    return {
        "clustering_columns": table["clustering_columns"],
        "columns": [c for c in table["columns"] if c["name"] not in to_remove],
        "name": table["name"],
        "partition_key": [k for k in table["partition_key"] if k not in to_remove],
    }
