# third parties
from _typeshed import Incomplete
from deepdiff.helper import (
    convert_item_or_items_into_compiled_regexes_else_none as convert_item_or_items_into_compiled_regexes_else_none,
)

class BaseOperator:
    regex_paths: Incomplete
    types: Incomplete
    def __init__(
        self, regex_paths: Incomplete | None = ..., types: Incomplete | None = ...
    ) -> None: ...
    def match(self, level) -> bool: ...
    def give_up_diffing(self, level, diff_instance) -> bool: ...
