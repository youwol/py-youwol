# third parties
from _typeshed import Incomplete
from deepdiff.deephash import DeepHash as DeepHash
from deepdiff.helper import DELTA_VIEW as DELTA_VIEW
from deepdiff.helper import CannotCompare as CannotCompare
from deepdiff.helper import add_to_frozen_set as add_to_frozen_set
from deepdiff.helper import cartesian_product_numpy as cartesian_product_numpy
from deepdiff.helper import dict_ as dict_
from deepdiff.helper import (
    get_homogeneous_numpy_compatible_type_of_seq as get_homogeneous_numpy_compatible_type_of_seq,
)
from deepdiff.helper import not_found as not_found
from deepdiff.helper import np_array_factory as np_array_factory
from deepdiff.helper import np_float64 as np_float64
from deepdiff.helper import np_ndarray as np_ndarray
from deepdiff.helper import numbers as numbers
from deepdiff.helper import only_numbers as only_numbers
from deepdiff.helper import strings as strings
from deepdiff.helper import time_to_seconds as time_to_seconds

DISTANCE_CALCS_NEEDS_CACHE: str

class DistanceMixin: ...

TYPES_TO_DIST_FUNC: Incomplete

def get_numeric_types_distance(num1, num2, max_): ...
