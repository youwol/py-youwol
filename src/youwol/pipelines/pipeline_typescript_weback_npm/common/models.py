# standard library
from enum import Enum
from pathlib import Path

# typing
from typing import Optional

# third parties
from pydantic import BaseModel

# Youwol application
from youwol.app.environment import UploadTarget, UploadTargets
from youwol.app.routers.projects.models_project import Project

# Youwol utilities
from youwol.utils import JSON, CommandException, execute_shell_cmd
from youwol.utils.context import Context


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

    - **external** : :class:`Dict[str, str]`  The dependencies not included in bundles.
    - **includedInBundle** : :class:`Dict[str, str]` The dependencies included in the bundles.

    Note: All dependencies listed in 'external' must be available in YouWol ecosystem.
    """

    externals: dict[str, str] = {}
    includedInBundle: dict[str, str] = {}


class Dependencies(BaseModel):
    """
    Description of the dependencies of the package.

    Attributes:

    - **runTime** : :class:`RunTimeDeps` Dependencies required at run time
    - **devTime** : :class:`Dict[str, str]`  Additional dependencies required only during development cycles
    """

    runTime: RunTimeDeps = RunTimeDeps()
    devTime: dict[str, str] = {}


class DevServer(BaseModel):
    """
    Description of the DevServer in case of application.

    Attributes:

    - **port** : :class:`int` dev-server's port
    """

    port: int


class MainModule(BaseModel):
    """
       This class defines the main bundle of the package

    Attributes:

    - **entryFile** : :class:`str` file entry point relative to the 'src' folder
    - **loadDependencies** : :class:`List[str]` the dependencies required to load the module.
    """

    entryFile: str
    loadDependencies: list[str] = []
    aliases: list[str] = []


class AuxiliaryModule(MainModule):
    """
    Description of an auxiliary module of the package.
    Secondary entry are usually used to eventually load additional features of the package latter on after the
    initial load.

    Attributes:

    - **name** : :class:`str` name to reference the entry (referenced when using 'setup.installEntry(name)')
        It will be used to generate filename of the bundle & exported symbol.
        E.g. for a package with exported symbol 'my-package', and a secondary entry point with name 'case-1',
        the exported symbol for the module 'case-1' will be 'my-package/case-1', the bundle will be located at
        'dist/my-package/case-1.js'.
    """

    name: str


class Bundles(BaseModel):
    """
    This class defines the bundles built by webpack

    Attributes:

    - **mainModule** : :class:`MainModule` The main module.
    - **auxiliaryModules** : :class:`List[AuxiliaryModule]` Auxiliaries modules of the package (lazy-loading).
    """

    mainModule: MainModule
    auxiliaryModules: list[AuxiliaryModule] = []


class Template(BaseModel):
    """
    This class gather required data to properly set-up skeleton of the various configuration files

    Attributes:

    - **path** : :class:`Path` The path of the project's folder
    - **type** : :class:`PackageType`  Type of the package (library or application)
    - **version** : :class:`str` Version of the package
    - **name** : :class:`str` Name of the package
    - **exportedSymbol** : :class:`str` Name of the exposed symbol of the library.
        If no requirements it is better to keep it empty (the name is used if not provided)
    - **shortDescription** : :class:`str` Short description of the package
    - **author** : :class:`str`  Main author of the package
    - **userGuide** : :class:`Optional[Union[bool, str]]`  optional link to a user guide using standard URL
    - **dependencies** : :class:`Dependencies` Dependencies of the package
    - **auxiliaryModules** : :class:`List[SecondaryEntry]` Auxiliaries modules of the package (lazy-loading).
    - **testConfig** : :class:`Optional[str]` An url to the test config used by py-youwol for tests, if need be
    - **devServer** : :class:`Optional[DevServer]` Dev. server configuration (relevant only for PackageType.Application)
    """

    path: Path
    type: PackageType
    version: str
    name: str
    inPackageJson: Optional[JSON] = {}
    exportedSymbol: Optional[str] = None
    shortDescription: str = ""
    author: Optional[str]
    userGuide: bool = False
    dependencies: Dependencies = Dependencies()
    bundles: Bundles
    testConfig: Optional[str]
    devServer: Optional[DevServer]


class NpmRepo(UploadTarget):
    name: str

    async def publish(self, project: Project, context: Context):
        raise NotImplementedError()


class PublicNpmRepo(NpmRepo):
    name: str

    async def publish(self, project: Project, context: Context):
        cmd = f"(cd {project.path} && yarn publish --access public)"
        exit_code, outputs = await execute_shell_cmd(
            f"(cd {project.path} && yarn publish --access public)", context=context
        )
        if exit_code != 0:
            raise CommandException(command=cmd, outputs=outputs)
        return outputs


class PackagesPublishNpm(UploadTargets):
    targets: list[NpmRepo]

    async def publish(self, target_name: str, project: Project, context: Context):
        target = next(t for t in self.targets if t.name == target_name)
        await target.publish(project, context)
