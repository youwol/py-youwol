# third parties
from _typeshed import Incomplete
from deepdiff.base import Base as Base
from deepdiff.deephash import DeepHash as DeepHash
from deepdiff.deephash import combine_hashes_lists as combine_hashes_lists
from deepdiff.distance import DistanceMixin as DistanceMixin
from deepdiff.helper import DELTA_VIEW as DELTA_VIEW
from deepdiff.helper import KEY_TO_VAL_STR as KEY_TO_VAL_STR
from deepdiff.helper import TEXT_VIEW as TEXT_VIEW
from deepdiff.helper import TREE_VIEW as TREE_VIEW
from deepdiff.helper import CannotCompare as CannotCompare
from deepdiff.helper import IndexedHash as IndexedHash
from deepdiff.helper import ListItemRemovedOrAdded as ListItemRemovedOrAdded
from deepdiff.helper import OrderedSetPlus as OrderedSetPlus
from deepdiff.helper import RepeatedTimer as RepeatedTimer
from deepdiff.helper import add_to_frozen_set as add_to_frozen_set
from deepdiff.helper import booleans as booleans
from deepdiff.helper import bytes_type as bytes_type
from deepdiff.helper import (
    convert_item_or_items_into_compiled_regexes_else_none as convert_item_or_items_into_compiled_regexes_else_none,
)
from deepdiff.helper import (
    convert_item_or_items_into_set_else_none as convert_item_or_items_into_set_else_none,
)
from deepdiff.helper import datetime_normalize as datetime_normalize
from deepdiff.helper import detailed__dict__ as detailed__dict__
from deepdiff.helper import dict_ as dict_
from deepdiff.helper import get_doc as get_doc
from deepdiff.helper import get_numpy_ndarray_rows as get_numpy_ndarray_rows
from deepdiff.helper import get_truncate_datetime as get_truncate_datetime
from deepdiff.helper import get_type as get_type
from deepdiff.helper import notpresent as notpresent
from deepdiff.helper import np_ndarray as np_ndarray
from deepdiff.helper import number_to_string as number_to_string
from deepdiff.helper import numbers as numbers
from deepdiff.helper import strings as strings
from deepdiff.helper import times as times
from deepdiff.helper import type_in_type_group as type_in_type_group
from deepdiff.helper import (
    type_is_subclass_of_type_group as type_is_subclass_of_type_group,
)
from deepdiff.helper import unprocessed as unprocessed
from deepdiff.helper import uuids as uuids
from deepdiff.lfucache import DummyLFU as DummyLFU
from deepdiff.lfucache import LFUCache as LFUCache
from deepdiff.model import CUSTOM_FIELD as CUSTOM_FIELD
from deepdiff.model import AttributeRelationship as AttributeRelationship
from deepdiff.model import DictRelationship as DictRelationship
from deepdiff.model import DiffLevel as DiffLevel
from deepdiff.model import (
    NonSubscriptableIterableRelationship as NonSubscriptableIterableRelationship,
)
from deepdiff.model import NumpyArrayRelationship as NumpyArrayRelationship
from deepdiff.model import RemapDict as RemapDict
from deepdiff.model import ResultDict as ResultDict
from deepdiff.model import SetRelationship as SetRelationship
from deepdiff.model import (
    SubscriptableIterableRelationship as SubscriptableIterableRelationship,
)
from deepdiff.model import TextResult as TextResult
from deepdiff.model import TreeResult as TreeResult
from deepdiff.serialization import SerializationMixin as SerializationMixin

logger: Incomplete
MAX_PASSES_REACHED_MSG: str
MAX_DIFFS_REACHED_MSG: str
notpresent_indexed: Incomplete
doc: Incomplete
PROGRESS_MSG: str
DISTANCE_CACHE_HIT_COUNT: str
DIFF_COUNT: str
PASSES_COUNT: str
MAX_PASS_LIMIT_REACHED: str
MAX_DIFF_LIMIT_REACHED: str
DISTANCE_CACHE_ENABLED: str
PREVIOUS_DIFF_COUNT: str
PREVIOUS_DISTANCE_CACHE_HIT_COUNT: str
CANT_FIND_NUMPY_MSG: str
INVALID_VIEW_MSG: str
CUTOFF_RANGE_ERROR_MSG: str
VERBOSE_LEVEL_RANGE_MSG: str
PURGE_LEVEL_RANGE_MSG: str
CUTOFF_DISTANCE_FOR_PAIRS_DEFAULT: float
CUTOFF_INTERSECTION_FOR_PAIRS_DEFAULT: float
DEEPHASH_PARAM_KEYS: Incomplete

class DeepDiff(ResultDict, SerializationMixin, DistanceMixin, Base):
    __doc__ = doc
    CACHE_AUTO_ADJUST_THRESHOLD: float
    custom_operators: Incomplete
    ignore_order: Incomplete
    ignore_order_func: Incomplete
    ignore_numeric_type_changes: Incomplete
    ignore_string_type_changes: Incomplete
    ignore_type_in_groups: Incomplete
    report_repetition: Incomplete
    exclude_paths: Incomplete
    exclude_regex_paths: Incomplete
    exclude_types: Incomplete
    exclude_types_tuple: Incomplete
    ignore_type_subclasses: Incomplete
    type_check_func: Incomplete
    ignore_string_case: Incomplete
    exclude_obj_callback: Incomplete
    number_to_string: Incomplete
    iterable_compare_func: Incomplete
    ignore_private_variables: Incomplete
    ignore_nan_inequality: Incomplete
    hasher: Incomplete
    cache_tuning_sample_size: Incomplete
    group_by: Incomplete
    encodings: Incomplete
    ignore_encoding_errors: Incomplete
    significant_digits: Incomplete
    math_epsilon: Incomplete
    truncate_datetime: Incomplete
    number_format_notation: Incomplete
    verbose_level: Incomplete
    view: Incomplete
    max_passes: Incomplete
    max_diffs: Incomplete
    cutoff_distance_for_pairs: Incomplete
    cutoff_intersection_for_pairs: Incomplete
    progress_logger: Incomplete
    cache_size: Incomplete
    is_root: bool
    hashes: Incomplete
    deephash_parameters: Incomplete
    tree: Incomplete
    t1: Incomplete
    t2: Incomplete
    def __init__(
        self,
        t1,
        t2,
        cache_purge_level: int = ...,
        cache_size: int = ...,
        cache_tuning_sample_size: int = ...,
        custom_operators: Incomplete | None = ...,
        cutoff_distance_for_pairs=...,
        cutoff_intersection_for_pairs=...,
        encodings: Incomplete | None = ...,
        exclude_obj_callback: Incomplete | None = ...,
        exclude_paths: Incomplete | None = ...,
        exclude_regex_paths: Incomplete | None = ...,
        exclude_types: Incomplete | None = ...,
        get_deep_distance: bool = ...,
        group_by: Incomplete | None = ...,
        hasher: Incomplete | None = ...,
        hashes: Incomplete | None = ...,
        ignore_encoding_errors: bool = ...,
        ignore_nan_inequality: bool = ...,
        ignore_numeric_type_changes: bool = ...,
        ignore_order: bool = ...,
        ignore_order_func: Incomplete | None = ...,
        ignore_private_variables: bool = ...,
        ignore_string_case: bool = ...,
        ignore_string_type_changes: bool = ...,
        ignore_type_in_groups: Incomplete | None = ...,
        ignore_type_subclasses: bool = ...,
        iterable_compare_func: Incomplete | None = ...,
        log_frequency_in_sec: int = ...,
        math_epsilon: Incomplete | None = ...,
        max_diffs: Incomplete | None = ...,
        max_passes: int = ...,
        number_format_notation: str = ...,
        number_to_string_func: Incomplete | None = ...,
        progress_logger=...,
        report_repetition: bool = ...,
        significant_digits: Incomplete | None = ...,
        truncate_datetime: Incomplete | None = ...,
        verbose_level: int = ...,
        view=...,
        _original_type: Incomplete | None = ...,
        _parameters: Incomplete | None = ...,
        _shared_parameters: Incomplete | None = ...,
        **kwargs,
    ) -> None: ...
    def custom_report_result(
        self, report_type, level, extra_info: Incomplete | None = ...
    ) -> None: ...
    def get_stats(self): ...
