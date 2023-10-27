# standard library
from dataclasses import dataclass, field

# typing
from typing import List

# relative
from .common import OwnerColumns, Table


@dataclass(kw_only=True, frozen=True)
class LibrariesRow(OwnerColumns, Table):
    library_name: str
    version_number: str
    aliases: List[str] = field(default_factory=list)
    bundle: str
    bundle_min: str
    dependencies: List[str]
    description: str
    fingerprint: str
    library_id: str
    namespace: str
    path: str
    tags: List[str]
    type: str
    version: str

    def __repr__(self) -> str:
        return f"{self.library_id}"

    @staticmethod
    def get_key_columns() -> List[str]:
        return [
            "library_name",
            "owner_id",
            "owner_name",
            "owner_kind",
            "version_number",
        ]

    @staticmethod
    def get_keyspace_table() -> (str, str):
        return "prod_cdn", "libraries"
