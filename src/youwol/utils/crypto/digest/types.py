# future
from __future__ import annotations

# typing
from typing import Any, Protocol, TypeVar


class NoDigestComputationForValueError(RuntimeError):
    """Raise when trying to compute digest for an unknown type"""

    def __init__(self, t: str):
        self.t = t


class FnTrace(Protocol):
    """Type declaration for the trace function

    Will be called with `v_type`, a string naming the type of the value, and `trace_path`,
    a string representing the path from the root value.
    """

    def __call__(self, v_type: str, trace_path: str) -> None: ...


T_contra = TypeVar("T_contra", contravariant=True)


class Hash(Protocol):
    """Type declaration for duck typing return objects of functions from hashlib"""

    def digest(self) -> bytes: ...
    def update(self, buffer: bytes): ...


class FnHash(Protocol):
    """Type declaration for functions from hashlib"""

    def __call__(self, string: bytes) -> Hash: ...


class FnPredicate(Protocol):
    """Type declaration for a predicate based on a value"""

    def __call__(self, v: Any) -> bool: ...


class DigestExclude:
    """Class marker for the objects to exclude for the digest computation"""
