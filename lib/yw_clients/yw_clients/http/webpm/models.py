# typing
from typing import Any, Literal

# third parties
from pydantic import BaseModel

WebpmLibraryType = Literal["js/wasm", "backend", "pyodide"]
"""
The possible types for a package published in webpm.
"""
default_webpm_lib_type: WebpmLibraryType = "js/wasm"


class PublishResponse(BaseModel):
    """
    Publication summary response.
    """

    name: str
    """
    Name of the library.
    """
    id: str
    """
    ID of the library.
    """
    version: str
    """
    Version of the library.
    """
    fingerprint: str
    """
    Fingerprint of the library.
    """
    compressedSize: int
    """
    Compressed size of the library.
    """
    url: str
    """
    URL of the library.
    """


class UploadResponse(BaseModel):
    filesCount: int
    librariesCount: int
    compressedSize: int
    namespace: str


class PublishLibrariesResponse(BaseModel):
    filesCount: int
    librariesCount: int
    compressedSize: int
    namespaces: list[str]


class Release(BaseModel):
    """
    Describe a library release.
    """

    version: str
    """
    Version.
    """
    version_number: int
    """
    Version as integer preserving ordering.
    """
    fingerprint: str
    """
    Fingerprint.
    """


class ListVersionsResponse(BaseModel):
    """
    Describes a list of versions of a library.
    """

    name: str
    """
    Name of the library.
    """
    versions: list[str]
    """
    The list of version.
    """
    namespace: str
    """
    The namespace.
    """
    id: str
    """
    The library's ID.
    """
    releases: list[Release] = []
    """
    The list of releases.
    """


class ListLibsResponse(BaseModel):
    libraries: list[ListVersionsResponse]


Url = str


class DeleteBody(BaseModel):
    librariesName: list[str]


class DeleteLibraryResponse(BaseModel):
    """
    Describes the response when deleting a library.
    """

    deletedVersionsCount: int


class LoadingGraphResponse(BaseModel):
    graphType: str
    definition: list[list[Url]]


class Library(BaseModel):
    """
    Describe a library element in the CDN database.
    """

    name: str
    """
    Name of the library.
    """
    version: str
    """
    Version of the library.
    """
    id: str
    """
    ID of the library.
    """
    namespace: str
    """
    Namespace of the library, empty string if not applicable.
    """
    type: WebpmLibraryType
    """
    The type of the library.
    """
    fingerprint: str
    """
    Fingerprint.
    """
    # exportedSymbol is deprecated, use 'aliases' instead
    exportedSymbol: str
    aliases: list[str]
    """
    A list of aliases for the global symbol defined.
    """
    apiKey: str
    """
    API key (unique for all version that are compatible in terms of semantic versioning).
    """


class LoadingGraphResponseV1(BaseModel):
    """
    Describes the response when requesting the resolution of dependencies.
    """

    graphType: str
    lock: list[Library]
    """
    Describes the explicit version of the library involved.
    """

    definition: list[
        list[Any]
    ]  # 'Any' is actually Tuple[str, Url], but it leads to 500 when rendering the docs
    """
    The definition as an array of block that needs to be installed one after the other.
    Each block is itself an array, in which all elements can be installed in parallel.
    Each block's element is a tuple `(assetId, URL)` where URL is the entry-point URL.
    """


class DependenciesResponse(BaseModel):
    libraries: dict[str, str]
    loadingGraph: LoadingGraphResponse


class DependenciesResponseV1(BaseModel):
    libraries: dict[str, str]
    loadingGraph: LoadingGraphResponseV1


class DependenciesLatestBody(BaseModel):
    libraries: list[str]


class LibVersionsBody(BaseModel):
    name: str


class LibraryQuery(BaseModel):
    """
    Describes a library when requesting loading graph resolution.
    """

    name: str
    """
    Name of the library.
    """
    version: str
    """
    Semantic versioning (or version) of the target.
    """


class LibraryResolved(Library):
    dependencies: list[LibraryQuery]
    bundle: str
    exportedSymbol: str
    apiKey: str

    def full_exported_symbol(self):
        return f"{self.exportedSymbol}_APIv{self.apiKey}"


class LoadingGraphBody(BaseModel):
    """
    Body of the request to resolve loading graph.
    """

    libraries: list[LibraryQuery] | dict[str, str]
    """
    The requested libraries.
    """
    using: dict[str, str] = {}
    """
    Allows to pin the dependencies of some libraries to override the version that would normally be picked.
    In the form of a dict with key being library name and value the explicit version.
    """
    extraIndex: str | None = None
    """
    A brotli encoded dictionary of an extra CDN database to account for when resolving the dependencies.
    """


class LoadingGraphBodyV1(BaseModel):
    libraries: list[LibraryQuery]
    using: dict[str, str] = {}


class FileSummaryResponse(BaseModel):
    """
    Description of a file included in a library.
    """

    name: str
    """
    Name of the file.
    """
    size: int
    """
    Size of the file.
    """
    encoding: str
    """
    Encoding type.
    """


class FolderResponse(BaseModel):
    """
    Description of a folder included in a library.
    """

    name: str
    """
    Name of the folder.
    """
    path: str
    """
    Path of the folder (relative to the package root).
    """
    size: int = -1
    """
    Total size in bytes of the files included.
    """
    filesCount: int = (
        -1
    )  # prior to 06/07/2022 this property was not computed during publish
    """
    Number of files of the files included.
    """


class ExplorerResponse(BaseModel):
    """
    Describe the files content structure of a folder of a library.
    """

    # prior to some point, no explorer data were published the default is then returned
    size: int = -1
    """
    Total size in bytes.
    """
    filesCount: int = (
        -1
    )  # prior to 06/07/2022 this property was not computed during publish
    """
    Number of files in the folder.
    """
    files: list[FileSummaryResponse] = []
    """
    Files description.
    """
    folders: list[FolderResponse] = []
    """
    Folders description.
    """
