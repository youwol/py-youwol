# third parties
from deepdiff import DeepSearch as DeepSearch
from deepdiff import Delta as Delta
from deepdiff.diff import (
    CUTOFF_DISTANCE_FOR_PAIRS_DEFAULT as CUTOFF_DISTANCE_FOR_PAIRS_DEFAULT,
)
from deepdiff.diff import (
    CUTOFF_INTERSECTION_FOR_PAIRS_DEFAULT as CUTOFF_INTERSECTION_FOR_PAIRS_DEFAULT,
)
from deepdiff.diff import DeepDiff as DeepDiff
from deepdiff.diff import logger as logger
from deepdiff.serialization import load_path_content as load_path_content
from deepdiff.serialization import save_content_to_path as save_content_to_path

def cli() -> None: ...
def diff(*args, **kwargs) -> None: ...
def patch(path, delta_path, backup, raise_errors, debug) -> None: ...
def grep(item, path, debug, **kwargs) -> None: ...
def extract(path_inside, path, debug) -> None: ...
