# standard library
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Awaitable, Callable, List, Tuple, Union

OnProjectsCountUpdate = Callable[[Tuple[List[Path], List[Path]]], Awaitable[None]]
ConfigPath = Union[str, Path]


@dataclass(frozen=True)
class ApiConfiguration:
    open_api_prefix: str
    base_path: str


class IPipelineFactory:
    """
    This class should not be used: instead use IPipelineFactory from youwol.app.environment.models_project.
    It is here for backward compatibility purpose & will disappear soon.
    """


class ProjectsFinderHandler:
    """
    Abstract class for ProjectsFinderHandler strategies.

    Derived classes need to implement the **'initialize'**, **'refresh'** and **'release'** method.
    """

    async def initialize(self):
        raise NotImplementedError()

    async def refresh(self):
        raise NotImplementedError()

    def release(self):
        # Does nothing by default
        pass
