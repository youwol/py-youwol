# standard library
from dataclasses import dataclass, field

# relative
from .common import OwnerColumns, Table


@dataclass(kw_only=True, frozen=True)
class LibrariesRow(OwnerColumns, Table):
    library_name: str
    version_number: str
    aliases: list[str] = field(default_factory=list)
    bundle: str
    bundle_min: str
    dependencies: list[str]
    description: str
    fingerprint: str
    library_id: str
    namespace: str
    path: str
    tags: list[str]
    type: str
    version: str

    def __repr__(self) -> str:
        return f"{self.library_id}"

    @staticmethod
    def get_key_columns() -> list[str]:
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
