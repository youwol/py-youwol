# standard library
from collections.abc import Generator

# third parties
from _typeshed import Incomplete

async def chain(*sources) -> Generator[Incomplete, None, None]: ...
async def zip(*sources) -> Generator[Incomplete, None, None]: ...
def map(
    source,
    func,
    *more_sources,
    ordered: bool = ...,
    task_limit: Incomplete | None = ...,
): ...
def merge(*sources): ...
def ziplatest(*sources, partial: bool = ..., default: Incomplete | None = ...): ...
