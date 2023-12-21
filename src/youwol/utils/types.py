# typing
from typing import Any, Dict, List, Union

# 'Any' should be 'JSON', but pydantic scream (most likely because of recursive definition)
JSON = Union[str, int, float, bool, None, Dict[str, Any], List]
"""
Basically means a valid JSON object.

The type definition is not rigorous (recursive definition cause problem with pydantic) .
"""
