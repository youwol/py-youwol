# standard library
from dataclasses import dataclass
from pathlib import Path

# typing
from typing import Union

ConfigPath = Union[str, Path]
"""
Path specification that can be used in configuration.
"""


@dataclass(frozen=True)
class ApiConfiguration:
    """
    Defines element related to the global configuration of the API.
    """

    open_api_prefix: str
    """
    Global open API prefix.
    """
    base_path: str
    """
    Global base path used to serve the request.
    """


class IPipelineFactory:
    """
    This class should not be used: instead use IPipelineFactory from youwol.app.environment.models_project.
    It is here for backward compatibility purpose & will disappear soon.
    """
