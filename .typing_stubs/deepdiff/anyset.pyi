# third parties
from _typeshed import Incomplete
from deepdiff.deephash import DeepHash as DeepHash
from deepdiff.helper import dict_ as dict_

class AnySet:
    def __init__(self, items: Incomplete | None = ...) -> None: ...
    def add(self, item) -> None: ...
    def __contains__(self, item) -> bool: ...
    def pop(self): ...
    def __eq__(self, other): ...
    __req__ = __eq__
    def __len__(self) -> int: ...
    def __iter__(self): ...
    def __bool__(self) -> bool: ...
