# standard library
from enum import Enum

# third parties
from _typeshed import Incomplete
from deepdiff.base import Base as Base
from deepdiff.helper import KEY_TO_VAL_STR as KEY_TO_VAL_STR
from deepdiff.helper import add_to_frozen_set as add_to_frozen_set
from deepdiff.helper import (
    convert_item_or_items_into_compiled_regexes_else_none as convert_item_or_items_into_compiled_regexes_else_none,
)
from deepdiff.helper import (
    convert_item_or_items_into_set_else_none as convert_item_or_items_into_set_else_none,
)
from deepdiff.helper import datetime_normalize as datetime_normalize
from deepdiff.helper import dict_ as dict_
from deepdiff.helper import get_doc as get_doc
from deepdiff.helper import get_id as get_id
from deepdiff.helper import get_truncate_datetime as get_truncate_datetime
from deepdiff.helper import not_hashed as not_hashed
from deepdiff.helper import number_to_string as number_to_string
from deepdiff.helper import numbers as numbers
from deepdiff.helper import short_repr as short_repr
from deepdiff.helper import strings as strings
from deepdiff.helper import times as times
from deepdiff.helper import type_in_type_group as type_in_type_group
from deepdiff.helper import (
    type_is_subclass_of_type_group as type_is_subclass_of_type_group,
)
from deepdiff.helper import unprocessed as unprocessed

logger: Incomplete
UNPROCESSED_KEY: Incomplete
EMPTY_FROZENSET: Incomplete
INDEX_VS_ATTRIBUTE: Incomplete
HASH_LOOKUP_ERR_MSG: str

def sha256hex(obj): ...
def sha1hex(obj): ...

default_hasher = sha256hex

def combine_hashes_lists(items, prefix): ...

class BoolObj(Enum):
    TRUE: int
    FALSE: int

def prepare_string_for_hashing(
    obj,
    ignore_string_type_changes: bool = ...,
    ignore_string_case: bool = ...,
    encodings: Incomplete | None = ...,
    ignore_encoding_errors: bool = ...,
): ...

doc: Incomplete

class DeepHash(Base):
    __doc__ = doc
    hashes: Incomplete
    exclude_types_tuple: Incomplete
    ignore_repetition: Incomplete
    exclude_paths: Incomplete
    exclude_regex_paths: Incomplete
    hasher: Incomplete
    significant_digits: Incomplete
    truncate_datetime: Incomplete
    number_format_notation: Incomplete
    ignore_type_in_groups: Incomplete
    ignore_string_type_changes: Incomplete
    ignore_numeric_type_changes: Incomplete
    ignore_string_case: Incomplete
    exclude_obj_callback: Incomplete
    apply_hash: Incomplete
    type_check_func: Incomplete
    number_to_string: Incomplete
    ignore_private_variables: Incomplete
    encodings: Incomplete
    ignore_encoding_errors: Incomplete
    def __init__(
        self,
        obj,
        *,
        hashes: Incomplete | None = ...,
        exclude_types: Incomplete | None = ...,
        exclude_paths: Incomplete | None = ...,
        exclude_regex_paths: Incomplete | None = ...,
        hasher: Incomplete | None = ...,
        ignore_repetition: bool = ...,
        significant_digits: Incomplete | None = ...,
        truncate_datetime: Incomplete | None = ...,
        number_format_notation: str = ...,
        apply_hash: bool = ...,
        ignore_type_in_groups: Incomplete | None = ...,
        ignore_string_type_changes: bool = ...,
        ignore_numeric_type_changes: bool = ...,
        ignore_type_subclasses: bool = ...,
        ignore_string_case: bool = ...,
        exclude_obj_callback: Incomplete | None = ...,
        number_to_string_func: Incomplete | None = ...,
        ignore_private_variables: bool = ...,
        parent: str = ...,
        encodings: Incomplete | None = ...,
        ignore_encoding_errors: bool = ...,
        **kwargs,
    ) -> None: ...
    sha256hex = sha256hex
    sha1hex = sha1hex
    def __getitem__(self, obj, extract_index: int = ...): ...
    def __contains__(self, obj) -> bool: ...
    def get(self, key, default: Incomplete | None = ..., extract_index: int = ...): ...
    @staticmethod
    def get_key(
        hashes, key, default: Incomplete | None = ..., extract_index: int = ...
    ): ...
    def __eq__(self, other): ...
    __req__ = __eq__
    def __bool__(self) -> bool: ...
    def keys(self): ...
    def values(self): ...
    def items(self): ...
