# standard library
import uuid

from collections import OrderedDict as OrderedDict
from collections.abc import Generator

# typing
from typing import NamedTuple

# third parties
from _typeshed import Incomplete
from ordered_set import OrderedSet

class np_type: ...

np_array_factory: str
np_ndarray = np_type
np_bool_ = np_type
np_int8 = np_type
np_int16 = np_type
np_int32 = np_type
np_int64 = np_type
np_uint8 = np_type
np_uint16 = np_type
np_uint32 = np_type
np_uint64 = np_type
np_intp = np_type
np_uintp = np_type
np_float32 = np_type
np_float64 = np_type
np_float_ = np_type
np_complex64 = np_type
np_complex128 = np_type
np_complex_ = np_type
numpy_numbers: Incomplete
numpy_dtypes: Incomplete
numpy_dtype_str_to_type: Incomplete
logger: Incomplete
py_major_version: Incomplete
py_minor_version: Incomplete
py_current_version: Incomplete
py2: Incomplete
py3: Incomplete
py4: Incomplete
dict_ = dict
pypy3: Incomplete
strings: Incomplete
unicode_type = str
bytes_type = bytes
only_numbers: Incomplete
datetimes: Incomplete
uuids = uuid.UUID
times: Incomplete
numbers: Incomplete
booleans: Incomplete

class IndexedHash(NamedTuple):
    indexes: Incomplete
    item: Incomplete

current_dir: Incomplete
ID_PREFIX: str
ZERO_DECIMAL_CHARACTERS: Incomplete
KEY_TO_VAL_STR: str
TREE_VIEW: str
TEXT_VIEW: str
DELTA_VIEW: str

def short_repr(item, max_length: int = ...): ...

class ListItemRemovedOrAdded: ...
class OtherTypes: ...
class Skipped(OtherTypes): ...
class Unprocessed(OtherTypes): ...
class NotHashed(OtherTypes): ...
class NotPresent: ...
class CannotCompare(Exception): ...

unprocessed: Incomplete
skipped: Incomplete
not_hashed: Incomplete
notpresent: Incomplete
RemapDict = dict_

class indexed_set(set): ...

JSON_CONVERTOR: Incomplete

def json_convertor_default(default_mapping: Incomplete | None = ...): ...
def add_to_frozen_set(parents_ids, item_id): ...
def convert_item_or_items_into_set_else_none(items): ...

RE_COMPILED_TYPE: Incomplete

def convert_item_or_items_into_compiled_regexes_else_none(items): ...
def get_id(obj): ...
def get_type(obj): ...
def numpy_dtype_string_to_type(dtype_str): ...
def type_in_type_group(item, type_group): ...
def type_is_subclass_of_type_group(item, type_group): ...
def get_doc(doc_filename): ...

number_formatting: Incomplete

def number_to_string(number, significant_digits, number_format_notation: str = ...): ...

class DeepDiffDeprecationWarning(DeprecationWarning): ...

def cartesian_product(a, b) -> Generator[Incomplete, None, None]: ...
def cartesian_product_of_shape(dimentions, result: Incomplete | None = ...): ...
def get_numpy_ndarray_rows(
    obj, shape: Incomplete | None = ...
) -> Generator[Incomplete, None, None]: ...

class _NotFound:
    def __eq__(self, other): ...
    __req__ = __eq__

not_found: Incomplete

class OrderedSetPlus(OrderedSet):
    def lpop(self): ...

class RepeatedTimer:
    interval: Incomplete
    function: Incomplete
    args: Incomplete
    start_time: Incomplete
    kwargs: Incomplete
    is_running: bool
    def __init__(self, interval, function, *args, **kwargs) -> None: ...
    def start(self) -> None: ...
    def stop(self): ...

LITERAL_EVAL_PRE_PROCESS: Incomplete

def literal_eval_extended(item): ...
def time_to_seconds(t): ...
def datetime_normalize(truncate_datetime, obj): ...
def get_truncate_datetime(truncate_datetime): ...
def cartesian_product_numpy(*arrays): ...
def diff_numpy_array(A, B): ...

PYTHON_TYPE_TO_NUMPY_TYPE: Incomplete

def get_homogeneous_numpy_compatible_type_of_seq(seq): ...
def detailed__dict__(obj, ignore_private_variables: bool = ...): ...
