# future
from __future__ import annotations

# standard library
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# typing
from typing import Any, Generic

# relative
from .types import (
    FnPredicate,
    FnTrace,
    Hash,
    NoDigestComputationForValueError,
    T_contra,
)


@dataclass(frozen=True, kw_only=True)
class HashUpdater(ABC, Generic[T_contra]):
    """Abstract class declaring a function using DigestComputation
    to update the hash for a given value"""

    v_type: str
    """ A tag for the type of value, used to seed the hash and for tracing"""
    predicate: FnPredicate = lambda v: True
    """ The predicate to decide to use that function for the given value """

    @abstractmethod
    def update(self, v: T_contra, computation: DigestComputation) -> None:
        """Abstract method taking the value and the computation and
        updating the hash using DigestComputation"""


@dataclass(frozen=True, kw_only=True)
class DigestComputation:
    """Class handling the computation of the digest of a value,
    delegating update of the hash to a list of HashUpdater"""

    hash: Hash
    """ the hash to be updated and finally returned"""
    updaters: list[HashUpdater]
    """ A list of `HashUpdater` (see this type). Note that order DOES matter """
    fn_trace: FnTrace
    """ the function for tracing """
    trace_path: str
    """ the path of the value from the root value """
    visited: dict[int, str] = field(default_factory=dict)

    def clone(self, trace_suffix: str = "") -> DigestComputation:
        """Return a new DigestComputation with the same attributes, except that
        the trace_path is augmented with the suffix"""
        return DigestComputation(
            updaters=self.updaters,
            hash=self.hash,
            visited=self.visited,
            fn_trace=self.fn_trace,
            trace_path=f"{self.trace_path}{trace_suffix}",
        )

    def trace(self, v_type: str) -> None:
        """Trace a value of type v_type using the current trace_path"""
        self.fn_trace(v_type, trace_path=self.trace_path)

    def update(self, buffer: bytes) -> None:
        """Update the hash with the provided buffer"""
        self.hash.update(buffer)

    def delegate_update(self, v: Any):
        """Delegate the update to the first updater whose predicate match the
        value.

        If the value is None, the string "None" is used to update the hash
        instead.

        If there is no updater matching the value, raise
        NoDigestComputationForValueError.

        If this object (or its clones) already saw the value (using builtin
        id()), both the current trace_path and the previous trace_path will be
        used to update the hash instead."""

        updater = next(
            filter(
                lambda p: v is not None and p.predicate(v),
                self.updaters,
            ),
            None,
        )
        visited_path = self.visited.get(id(v))

        match (v, updater, visited_path):
            case (None, _, _):
                self.trace(v_type="NONE")
                self.update(b"None")
            case (_, None, _):
                raise NoDigestComputationForValueError(
                    f"[{self.trace_path} = {v=}:{type(v)}] No digest updater for value"
                )
            case (v, updater, None):
                self.visited[id(v)] = self.trace_path
                # mypy does not detect that updater cannot be None there
                updater.update(v, computation=self)  # type: ignore[union-attr]
            case (_, _, visited_path):
                computation = self.clone(f"<<<{visited_path}")
                computation.trace(v_type="VISITED")
                computation.update(computation.trace_path.encode())

    def compute(self, v: Any) -> bytes:
        """Call delegate_update() for the value then return the hash digest"""
        self.delegate_update(v)
        return self.hash.digest()
