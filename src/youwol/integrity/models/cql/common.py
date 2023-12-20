# standard library
from abc import ABC, abstractmethod
from dataclasses import dataclass

# relative
from .constants import (
    COLUMN_OWNER_ID_VALUE,
    COLUMN_OWNER_KIND_VALUE,
    COLUMN_OWNER_NAME_VALUE,
)


@dataclass(kw_only=True, frozen=True)
class OwnerColumns:
    owner_id: str = COLUMN_OWNER_ID_VALUE
    owner_name: str = COLUMN_OWNER_NAME_VALUE
    owner_kind: str = COLUMN_OWNER_KIND_VALUE


class Table(ABC):
    @staticmethod
    @abstractmethod
    def get_key_columns() -> list[str]:
        pass

    @staticmethod
    @abstractmethod
    def get_keyspace_table() -> (str, str):
        pass

    def __getitem__(self, item):
        return getattr(self, item)
