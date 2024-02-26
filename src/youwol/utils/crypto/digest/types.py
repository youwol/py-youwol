# future
from __future__ import annotations

# standard library
from abc import ABC, abstractmethod
from dataclasses import dataclass

# typing
from typing import Any, Generic, Protocol, TypeVar


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

    def digest(self): ...
    def update(self, v: bytes): ...


class FnHash(Protocol):
    """Type declaration for functions from hashlib"""

    def __call__(self, string: bytes) -> Hash: ...


@dataclass(frozen=True, kw_only=True)
class DigestComputationParams:
    """Encapsulate parameters for the digest calculation"""

    hash: Hash
    """ the hash to be updated and finally returned"""
    updaters: list[UpdateWithDigestValue]
    """ A list of `HashUpdater` (see this type). Note that order DOES matter """
    fn_trace: FnTrace
    """ the function for tracing """
    trace_path: str
    """ the path of the value from the root value """

    def clone(self, trace_suffix: str = "") -> DigestComputationParams:
        return DigestComputationParams(
            updaters=self.updaters,
            hash=self.hash,
            fn_trace=self.fn_trace,
            trace_path=f"{self.trace_path}{trace_suffix}",
        )

    def find_updater(self, v: Any):
        return next(
            filter(
                lambda p: p.predicate(v),
                self.updaters,
            ),
            None,
        )

    def trace(self, v_type: str):
        self.fn_trace(v_type, trace_path=self.trace_path)

    def update(self, v: bytes):
        self.hash.update(v)

    def digest(self):
        return self.hash.digest()


class FnPredicate(Protocol):
    """Type declaration for the function deciding if the UpdateWithDigestValue is suitable for the value"""

    def __call__(self, v: Any) -> bool: ...


@dataclass(frozen=True, kw_only=True)
class UpdateWithDigestValue(ABC, Generic[T_contra]):
    """Declare a function for updating the hash with the digest of a value"""

    v_type: str
    """ The name of the value, used to seed the hash and for tracing"""
    predicate: FnPredicate = lambda v: True
    """ The predicate to decide to use that function for the given value """

    @abstractmethod
    def update_hash(self, v: T_contra, computation: DigestComputationParams):
        """Abstract method taking the value and the digest parameters
        and updating the hash"""


class DigestExclude:
    """Class marker for the objects to exclude for the digest computation"""
