# standard library
from dataclasses import dataclass

# typing
from typing import Any, Generic, Protocol

# relative
from .computation import DigestComputation, HashUpdater
from .types import T_contra


class FnScalarToBytes(Protocol, Generic[T_contra]):
    """Type declaration for the function returning a bytes array representing the value"""

    def __call__(self, v: T_contra) -> bytes: ...


@dataclass(frozen=True, kw_only=True)
class UpdaterScalar(HashUpdater, Generic[T_contra]):
    """Generic implementation of HashUpdater for a scalar value.

    Will update the computation with:
    * the v_type
    * the bytes array returned by fn_value_to_bytes

    Expect its parent caller to handle tracing update"""

    fn_value_to_bytes: FnScalarToBytes[T_contra]
    """ Function to get the byte representation of the value """

    def update(self, v: T_contra, computation: DigestComputation):
        computation.trace(v_type=self.v_type)
        computation.update(self.v_type.encode())
        computation.update(self.fn_value_to_bytes(v))


@dataclass(frozen=True, kw_only=True)
class MemberComposite:
    """Helper type for a member of a parent composite value.

    Used by UpdaterComposite, which expect the FnMembers routine
     to return a list of MemberComposite"""

    v: Any
    """ Value of the member """
    trace_suffix: str = ""
    """ The suffix to add to the trace path (i.e the key or index in the parent composite value) """


class FnMembers(Protocol):
    """Type declaration for the function returning the members of a composite value"""

    def __call__(self, v: T_contra) -> list[MemberComposite]: ...


class FnTraceSuffix(Protocol):
    """Type declaration for the function returning the trace suffix for the composite value itself"""

    def __call__(self, v: T_contra) -> str: ...


@dataclass(frozen=True, kw_only=True)
class UpdaterComposite(HashUpdater, Generic[T_contra]):
    """Generic implementation of HashUpdater for a composite value.

    Will call computation.delegate_update() for the value of each MemberComposite returned by fn_members,
    with the suffix of that member appended to the trace path."""

    fn_members: FnMembers
    """ Function returning the members of the value """
    fn_trace_suffix: FnTraceSuffix | None = None
    """ Optional function returning a suffix for the trace path of the composite value itself """

    def update(self, v: T_contra, computation: DigestComputation):
        if self.fn_trace_suffix:
            computation = computation.clone(self.fn_trace_suffix(v))

        computation.trace(v_type=self.v_type)
        computation.update(self.v_type.encode())
        for member in self.fn_members(v):
            computation.clone(member.trace_suffix).delegate_update(member.v)


@dataclass(frozen=True, kw_only=True)
class DictEntry:
    """Helper type for an item to be process by UpdaterDictEntry"""

    key: Any
    """ The key of the item """
    value: Any
    """ The value of the item """
    key_repr: str
    """ The representation of the item, for the trace_path """


def encapsulated_dict_entry(
    key: Any, value: Any, key_repr: str | None = None
) -> MemberComposite:
    """Factory for a DictEntry encapsulated into a MemberComposite

    If key_repr is not provided, str(key) will be used instead.

    Note: the MemberComposite has no trace_suffix because
    UpdaterDictEntry is expected to handle it"""

    return MemberComposite(
        v=DictEntry(
            key=key, value=value, key_repr=str(key) if key_repr is None else key_repr
        )
    )


class UpdaterDictEntry(HashUpdater[DictEntry]):
    """Specialized implementation of HashUpdater for DictEntry.

    A UpdaterComposite can use the function encapsulated_dict_entry() to return
     a list of DictEntry, allowing better handling than
     a list of raw members (i.e. dict.items return tuples)"""

    def __init__(self):
        """Hard-code some attributes"""
        super().__init__(
            v_type="DICT_ENTRY", predicate=lambda v: isinstance(v, DictEntry)
        )

    def update(self, v: DictEntry, computation: DigestComputation):
        computation.update(self.v_type.encode())
        computation.clone(f"['{v.key_repr}'].key").delegate_update(v.key)
        computation.clone(f"['{v.key_repr}'].value").delegate_update(v.value)
