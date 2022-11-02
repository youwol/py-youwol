from typing import Any, Union, List, Mapping

# 'Any' should be 'JSON', but pydantic scream (most likely because of recursive definition)
JSON = Union[str, int, float, bool, None, Mapping[str, Any], List]
