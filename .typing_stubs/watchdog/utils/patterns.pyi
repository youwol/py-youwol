# standard library
from collections.abc import Generator

# third parties
from _typeshed import Incomplete

def filter_paths(
    paths,
    included_patterns: Incomplete | None = ...,
    excluded_patterns: Incomplete | None = ...,
    case_sensitive: bool = ...,
) -> Generator[Incomplete, None, None]: ...
def match_any_paths(
    paths,
    included_patterns: Incomplete | None = ...,
    excluded_patterns: Incomplete | None = ...,
    case_sensitive: bool = ...,
): ...
