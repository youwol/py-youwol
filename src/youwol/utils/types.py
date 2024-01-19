# typing
from typing import Any, Union

# 'Any' should be 'JSON', but pydantic scream (most likely because of recursive definition)
JSON = Union[str, int, float, bool, None, dict[str, Any], list]

AnyDict = dict[str, Any]
