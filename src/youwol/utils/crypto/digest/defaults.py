# standard library
import hashlib
import inspect

from pathlib import Path
from types import (
    BuiltinFunctionType,
    CoroutineType,
    FunctionType,
    MethodDescriptorType,
    MethodType,
)

# typing
from typing import Any

# relative
from .computation import DigestComputation, HashUpdater
from .helpers import (
    MemberComposite,
    UpdaterComposite,
    UpdaterDictEntry,
    UpdaterScalar,
    encapsulated_dict_entry,
)
from .traces import noop_trace
from .types import DigestExclude, FnHash, FnTrace

default_updaters: list[HashUpdater] = [
    UpdaterScalar[DigestExclude](
        v_type="EXCLUDE",
        predicate=lambda v: isinstance(v, DigestExclude),
        fn_value_to_bytes=lambda v: b"EXCLUDE",
    ),
    UpdaterScalar[int](
        v_type="INT",
        predicate=lambda v: isinstance(v, int),
        # `fn_value_to_bytes=bytes` is not correctly typed
        fn_value_to_bytes=lambda v: bytes(v),  # pylint: disable=unnecessary-lambda
    ),
    UpdaterScalar[str](
        v_type="STRING",
        predicate=lambda v: isinstance(v, str),
        fn_value_to_bytes=lambda v: v.encode(),
    ),
    UpdaterScalar[float](
        v_type="FLOAT",
        predicate=lambda v: isinstance(v, float),
        fn_value_to_bytes=lambda v: v.hex().encode(),
    ),
    UpdaterScalar[Path](
        v_type="PATH",
        predicate=lambda v: isinstance(v, Path),
        fn_value_to_bytes=lambda v: str(v.absolute()).encode(),
    ),
    UpdaterScalar[FunctionType](
        v_type="ROUTINE",
        # `predicate=inspect.isfunction is not correctly typed`
        predicate=lambda v: inspect.isfunction(v),  # pylint: disable=unnecessary-lambda
        fn_value_to_bytes=lambda v: v.__code__.co_code,
    ),
    UpdaterScalar[MethodType](
        v_type="METHOD",
        # `predicate=inspect.isfunction is not correctly typed`
        predicate=lambda v: inspect.ismethod(v),  # pylint: disable=unnecessary-lambda
        fn_value_to_bytes=lambda v: v.__func__.__code__.co_code,
    ),
    UpdaterScalar[BuiltinFunctionType](
        v_type="BUILTIN",
        # `predicate=inspect.isbuiltin is not correctly typed`
        predicate=lambda v: inspect.isbuiltin(v),  # pylint: disable=unnecessary-lambda
        fn_value_to_bytes=lambda v: v.__qualname__.encode(),
    ),
    UpdaterScalar[MethodDescriptorType](
        v_type="METH_QUAL",
        predicate=lambda v: inspect.ismethoddescriptor(v)
        and hasattr(v, "__qualname__"),
        fn_value_to_bytes=lambda v: v.__qualname__.encode(),
    ),
    UpdaterScalar[MethodDescriptorType](
        v_type="METH_FUNC",
        predicate=lambda v: inspect.ismethoddescriptor(v) and hasattr(v, "__func__"),
        fn_value_to_bytes=lambda v: v.__func__.__qualname__.encode(),
    ),
    UpdaterScalar[CoroutineType](
        v_type="COROUTINE",
        # `predicate=inspect.iscoroutine is not correctly typed`
        # pylint: disable-next=unnecessary-lambda
        predicate=lambda v: inspect.iscoroutine(v),
        fn_value_to_bytes=lambda v: v.cr_code.co_code,
    ),
    UpdaterComposite[tuple](
        predicate=lambda v: isinstance(v, tuple),
        v_type="TUPLE",
        fn_members=lambda v: [
            MemberComposite(v=i, trace_suffix=f"[{idx}]")
            for idx, i in enumerate(list(v))
        ],
    ),
    UpdaterComposite[list](
        predicate=lambda v: isinstance(v, list),
        v_type="LIST",
        fn_members=lambda v: [
            MemberComposite(v=i, trace_suffix=f"[{idx}]") for idx, i in enumerate(v)
        ],
    ),
    UpdaterComposite[set](
        predicate=lambda v: isinstance(v, set),
        v_type="SET",
        fn_members=lambda v: [
            MemberComposite(v=i, trace_suffix=f"[{idx}]")
            for idx, i in enumerate(sorted(v))
        ],
    ),
    UpdaterComposite[dict](
        predicate=lambda v: isinstance(v, dict),
        v_type="DICT",
        fn_members=lambda v: [
            encapsulated_dict_entry(key=key, value=value)
            for key, value in sorted(v.items())
        ],
    ),
    UpdaterDictEntry(),
    UpdaterComposite[object](
        predicate=lambda v: hasattr(v, "__class__") and hasattr(v, "__dict__"),
        v_type="OBJECT",
        fn_trace_suffix=lambda v: f"({v.__class__.__name__})",
        fn_members=lambda v: [
            MemberComposite(v=i, trace_suffix=f"=>{k}")
            for k, i in sorted(v.__dict__.items())
            if k != "__pydantic_initialised__"
        ],
    ),
    UpdaterComposite[object](
        predicate=lambda v: hasattr(v, "__class__"),
        v_type="DIR",
        fn_trace_suffix=lambda v: f"({v.__class__.__name__})",
        fn_members=lambda v: [
            encapsulated_dict_entry(key=attr, value=getattr(v, attr))
            for attr in dir(v)
            if not attr.startswith("__")
        ],
    ),
]

DEFAULT_HASH_FUNCTION: FnHash = hashlib.sha1

DEFAULT_FN_TRACE: FnTrace = noop_trace

DEFAULT_TRACE_PATH_ROOT = "ROOT"


def compute_digest(
    v: Any,
    hash_updaters: list[HashUpdater] | None = None,
    fn_hash: FnHash = DEFAULT_HASH_FUNCTION,
    fn_trace: FnTrace = DEFAULT_FN_TRACE,
    trace_path_root: str = DEFAULT_TRACE_PATH_ROOT,
) -> bytes:
    """Compute the digest of a value with the default parameters,
    or those supplied by the caller"""
    return DigestComputation(
        updaters=(hash_updaters if hash_updaters else default_updaters),
        hash=(fn_hash(trace_path_root.encode())),
        trace_path=trace_path_root,
        fn_trace=fn_trace,
    ).compute(v)
