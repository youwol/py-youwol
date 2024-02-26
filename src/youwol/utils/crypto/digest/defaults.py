# standard library
import hashlib
import inspect

from pathlib import Path
from types import CoroutineType, FunctionType

# typing
from typing import Any

# relative
from .implementations import (
    MemberComposite,
    UpdaterComposite,
    UpdaterDictEntry,
    UpdaterScalar,
    encapsulated_dict_entry,
    update_hash_any,
)
from .traces import noop_fn_trace
from .types import (
    DigestComputationParams,
    DigestExclude,
    FnHash,
    FnTrace,
    UpdateWithDigestValue,
)

default_updaters: list[UpdateWithDigestValue] = [
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
            encapsulated_dict_entry(k=key, v=value) for key, value in sorted(v.items())
        ],
    ),
    UpdaterDictEntry(),
    UpdaterComposite[object](
        predicate=lambda v: hasattr(v, "__class__"),
        v_type="OBJECT",
        fn_trace_suffix=lambda v: f"({v.__class__.__name__})",
        fn_members=lambda v: [
            MemberComposite(v=i, trace_suffix=f"=>{k}")
            for k, i in sorted(v.__dict__.items())
            if k != "__pydantic_initialised__"
        ],
    ),
]

DEFAULT_HASH_FUNCTION: FnHash = hashlib.sha1

DEFAULT_FN_TRACE: FnTrace = noop_fn_trace

DEFAULT_TRACE_PATH_ROOT = "ROOT"


def compute_digest(
    v: Any,
    hash_updaters: list[UpdateWithDigestValue] | None = None,
    fn_hash: FnHash = DEFAULT_HASH_FUNCTION,
    fn_trace: FnTrace = DEFAULT_FN_TRACE,
    trace_path_root: str = DEFAULT_TRACE_PATH_ROOT,
) -> bytes:
    """Compute the digest of a value with the default parameters"""
    computation = DigestComputationParams(
        updaters=(hash_updaters if hash_updaters else default_updaters),
        hash=(fn_hash(trace_path_root.encode())),
        trace_path=trace_path_root,
        fn_trace=fn_trace,
    )
    update_hash_any(v, computation=computation)
    return computation.digest()
