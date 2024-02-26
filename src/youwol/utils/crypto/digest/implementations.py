# standard library
from dataclasses import dataclass

# typing
from typing import Any, Generic, Protocol

# relative
from .types import (
    DigestComputationParams,
    NoDigestComputationForValueError,
    T_contra,
    UpdateWithDigestValue,
)


class FnScalarToBytes(Protocol, Generic[T_contra]):
    """Type declaration for the function getting a bytes array representing the value"""

    def __call__(self, v: T_contra) -> bytes: ...


@dataclass(frozen=True, kw_only=True)
class UpdaterScalar(UpdateWithDigestValue, Generic[T_contra]):
    """Generic implementation of UpdateWithDigestValue for a scalar value.

    Expect its parent caller to trace, does not call FnTrace nor update trace_acc"""

    fn_value_to_bytes: FnScalarToBytes[T_contra]
    """ Function to get the byte representation of the value """

    def update_hash(self, v: T_contra, computation: DigestComputationParams):
        computation.trace(v_type=self.v_type)
        computation.update(self.v_type.encode())
        computation.update(self.fn_value_to_bytes(v))


@dataclass(frozen=True, kw_only=True)
class MemberComposite:
    """Helper type for a value (either scalar or composite), member of a parent composite value"""

    v: Any
    """ Value """
    trace_suffix: str = ""
    """ The suffix to add to the trace path (i.e the key or index in the parent composite value) """


class FnMembers(Protocol):
    """Type declaration for the function returning the members of a composite value"""

    def __call__(self, v: T_contra) -> list[MemberComposite]: ...


class FnTraceSuffix(Protocol):
    """Type declaration for the function returning the suffix for the composite value"""

    def __call__(self, v: T_contra) -> str: ...


@dataclass(frozen=True, kw_only=True)
class UpdaterComposite(UpdateWithDigestValue, Generic[T_contra]):
    """Generic implementation of UpdateWithDigestValue for a composite value.

    Will call update_hash_any() for the value of each item returned by fn_members,
    with the suffix of that item appended to the trace path.
    """

    fn_members: FnMembers
    """ Function returning the members of the value """
    fn_trace_suffix: FnTraceSuffix | None = None
    """ Optional function returning a suffix for the trace path of the composite value itself (i.e. a class name) """

    def update_hash(self, v: T_contra, computation: DigestComputationParams):
        if self.fn_trace_suffix:
            computation = computation.clone(self.fn_trace_suffix(v))

        computation.trace(v_type=self.v_type)
        computation.update(self.v_type.encode())
        for member in self.fn_members(v):
            update_hash_any(
                member.v,
                computation=computation.clone(member.trace_suffix),
            )


@dataclass(frozen=True, kw_only=True)
class DictEntry:
    """Helper type for an item to be process by UpdaterDictEntry"""

    key: Any
    value: Any


def encapsulated_dict_entry(k: Any, v: Any) -> MemberComposite:
    """Return a DictEntry encapsulated in a ItemComposite

    Note: the ItemComposite has no trace_suffix because UpdaterDictEntry will handle it
    """
    return MemberComposite(v=DictEntry(key=k, value=v))


class UpdaterDictEntry(UpdateWithDigestValue[DictEntry]):
    """Specialized implementation of UpdateWithDigestValue for DictEntry.

    A UpdaterComposite can use the function encapsulated_dict_entry to return
     a list of DictEntry, allowing better handling than a list of row member
    """

    def __init__(self):
        """Hard-code some variables"""
        super().__init__(
            v_type="DICT_ENTRY", predicate=lambda v: isinstance(v, DictEntry)
        )

    def update_hash(self, v: DictEntry, computation: DigestComputationParams):
        computation.update(self.v_type.encode())
        update_hash_any(v.key, computation=computation.clone(f"['{v.key}'].key"))
        update_hash_any(v.value, computation=computation.clone(f"['{v.key}'].value"))


def update_hash_any(v: Any, computation: DigestComputationParams):
    """Recursively compute the digest of v, using `computation` as a shared state

    If `v` is None, it will update the hash and return immediately
    Else it will use the first suitable UpdateWithDigestValue implementation − order DOES matter.
    If no suitable UpdateWithDigestValue is found, it will throw NoDigestComputationForValueError
    """
    if v is None:
        computation.trace(v_type="NONE")
        computation.update(b"None")
        return

    impl = computation.find_updater(v)
    if impl:
        impl.update_hash(v, computation=computation)
        return

    raise NoDigestComputationForValueError(
        f"[{v=}:{computation.trace_path}] No compute digest implementation for type '{type(v)}'"
    )
