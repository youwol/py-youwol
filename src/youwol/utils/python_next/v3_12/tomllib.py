"""Surrogate for tomllib
TODO: to be replaced by standard library `tomllib` once python 3.11 supported is dropped
"""

# typing
from typing import Any, BinaryIO

# third parties
import tomlkit


def load(fp: BinaryIO) -> dict[str, Any]:
    """Replacement for `tommlib.load()`"""
    return tomlkit.load(fp)
