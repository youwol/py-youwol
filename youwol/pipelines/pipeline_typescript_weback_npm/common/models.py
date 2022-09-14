from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel


class PackageType(Enum):
    """
    Description whether the package is an application or library
    """
    Library = "Library"
    Application = "Application"


class RunTimeDeps(BaseModel):
    """
    Description of the run-time dependencies of the project.

    Attributes:

    - load : :class:`Dict[str, str]`   Dependencies required at run time to load the package
    - differed : :class:`Dict[str, str]`  Additional dependencies required at some points after load
    - includedInBundle : :class:`List[str]` The dependencies to encapsulates in the package's bundle.

    Note: All dependencies listed in 'load' or 'differed' and not available in YouWol ecosystem must be included in
    'includedInBundle'.
    """
    load: Dict[str, str] = {}
    differed: Dict[str, str] = {}
    includedInBundle: List[str] = []


class Dependencies(BaseModel):
    """
    Description of the dependencies of the package.

    Attributes:

    - runTime : :class:`RunTimeDeps` Dependencies required at run time
    - devTime : :class:`Dict[str, str]`  Additional dependencies required only during development cycles
    """
    runTime: RunTimeDeps = RunTimeDeps()
    devTime: Dict[str, str] = {}


class DevServer(BaseModel):
    port: int


class Template(BaseModel):
    """
    This class gather required data to properly set-up skeleton of the various configuration files

    Attributes:

    - path : :class:`Path` The path of the project's folder
    - type : :class:`ModuleTypeInput`  Type of the package (library or application)
    - version : :class:`str` Version of the package
    - name : :class:`str` Name of the package
    - exportedSymbol : :class:`str` Name of the exposed symbol of the library.
        If no requirements it is better to keep it empty (the name is used if not provided)
    - shortDescription : :class:`str` Short description of the package
    - author : :class:`str`  Main author of the package
    - userGuide : :class:`Optional[Union[bool, str]]`  optional link to a user guide using standard URL
    - dependencies : :class:`Dependencies` Dependencies of the package
    - testConfig : :class:`Optional[str]` An url to the test config used by py-youwol for tests, if need be
    """
    path: Path
    type: PackageType
    version: Optional[str]
    name: Optional[str]
    exportedSymbol: Optional[str] = None
    shortDescription: Optional[str] = ""
    author: Optional[str]
    userGuide: bool = False
    dependencies: Dependencies = Dependencies()
    testConfig: Optional[str]
    devServer: Optional[DevServer]
