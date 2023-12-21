# typing
from typing import Any, Union

# 'Any' should be 'JSON', but pydantic scream (most likely because of recursive definition)
JSON = Union[str, int, float, bool, None, dict[str, Any], list]
"""
Basically means a valid JSON object.

The type definition is not rigorous (recursive definition cause problem with pydantic).
"""

AnyDict = dict[str, Any]
"""
A loosely type dictionary indexed by strings.
Often used to refers to a JSON object with no schema validation.
"""
