# typing
from typing import TextIO

# relative
from .types import FnTrace


def __trace_as_string(v_type: str, trace_path: str) -> str:
    """Helper function to stringify FnTrace arguments"""
    return f"{v_type:>12} {trace_path}"


def noop_trace(v_type: str, trace_path: str) -> None:
    """Does nothing but do it well. Conform to the type FnTrace"""
    (_, _) = v_type, trace_path


def dump_trace_to_stdout(v_type: str, trace_path: str) -> None:
    """Dump each trace to stdout. Conform to the type FnTrace"""
    print(__trace_as_string(v_type=v_type, trace_path=trace_path))


def get_dump_trace_to_file(fp: TextIO) -> FnTrace:
    """Factory for a function dumping each trace to a file, hopefully open in writing"""

    def dump_trace_to_file(v_type: str, trace_path: str):
        fp.write(__trace_as_string(v_type=v_type, trace_path=trace_path))
        fp.write("\n")

    return dump_trace_to_file
