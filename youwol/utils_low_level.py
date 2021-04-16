import asyncio
import shutil
import tempfile
from collections import Callable
from enum import Enum
from pathlib import Path, PosixPath
from typing import Any, Union, Mapping, List
import re

from pydantic import BaseModel

JSON = Union[str, int, float, bool, None, Mapping[str, 'JSON'], List['JSON']]


def to_json(obj: BaseModel) -> JSON:

    def to_serializable(v):
        if isinstance(v, Path):
            return str(v)
        if isinstance(v, PosixPath):
            return str(v)
        if isinstance(v, Callable):
            return "function"
        if isinstance(v, Enum):
            return v.name
        return v

    base = obj.dict()

    def to_json_rec(_obj: Any):

        if isinstance(_obj, dict):
            for k, v in _obj.items():
                if not isinstance(v, dict) and not isinstance(v, list):
                    _obj[k] = to_serializable(v)
                if isinstance(v, dict):
                    to_json_rec(v)
                if isinstance(v, list):
                    for i, e in enumerate(v):
                        if not isinstance(e, dict) and not isinstance(e, list):
                            _obj[k][i] = to_serializable(e)
                        else:
                            to_json_rec(e)

    to_json_rec(base)
    return base


async def merge(*iterables):
    # https://stackoverflow.com/questions/50901182/watch-stdout-and-stderr-of-a-subprocess-simultaneously
    iter_next = {it.__aiter__(): None for it in iterables}
    while iter_next:
        for it, it_next in iter_next.items():
            if it_next is None:
                fut = asyncio.ensure_future(it.__anext__())
                fut._orig_iter = it
                iter_next[it] = fut
        done, _ = await asyncio.wait(iter_next.values(),
                                     return_when=asyncio.FIRST_COMPLETED)
        for fut in done:
            iter_next[fut._orig_iter] = None
            try:
                ret = fut.result()
            except StopAsyncIteration:
                del iter_next[fut._orig_iter]
                continue
            yield ret


def sed_inplace(filename, pattern, repl):
    """"
    Perform the pure-Python equivalent of in-place `sed` substitution: e.g.,
    `sed -i -e 's/'${pattern}'/'${repl}' "${filename}"`.
    """
    # For efficiency, precompile the passed regular expression.
    pattern_compiled = re.compile(pattern)

    # For portability, NamedTemporaryFile() defaults to mode "w+b" (i.e., binary
    # writing with updating). This is usually a good thing. In this case,
    # however, binary writing imposes non-trivial encoding constraints trivially
    # resolved by switching to text writing. Let's do that.
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        with open(filename) as src_file:
            for line in src_file:
                tmp_file.write(pattern_compiled.sub(repl, line))

    # Overwrite the original file with the munged temporary file in a
    # manner preserving file attributes (e.g., permissions).
    shutil.copystat(filename, tmp_file.name)
    shutil.move(tmp_file.name, filename)
