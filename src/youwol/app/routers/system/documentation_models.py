# future
from __future__ import annotations

# typing
from typing import Literal

# third parties
from griffe import Module
from pydantic import BaseModel


class DocDocstringSectionResponse(BaseModel):
    """
    Description of a section of a docstring.

    It can be of `type=='text'` => part of the main text of the section,
    or `type=='admonition'` => an admonition with given `tag`.

    Example:
        ```
        Some comment in docstring.
        It will go in a `DocDocstringSectionResponse` of type `text`.

        Admonition:
            Some other comment.
            It will go in a `DocDocstringSectionResponse` of type `admonition`.
        ```

        *  In the above example *Admonition* is the `title`, and `tag` is not relevant.

    Example:
        ```
        Some comment in docstring.
        It will go in a `DocDocstringSectionResponse` of type `text`.

        a-tag: Admonition
            Some other comment.
            It will go in a `DocDocstringSectionResponse` of type `admonition`.
        ```

        *  In the above example *Admonition* is the `title`, and `tag` is *a-tag*.
    """

    type: Literal["text", "admonition"]
    """
    Type of the section.
    """
    tag: str | None
    """
    Tag name for an admonition.
    """
    title: str | None
    """
    Title name for an admonition.
    """
    text: str
    """
    Content of the docstring section.
    """


class DocTypeResponse(BaseModel):
    """
    Description of a type annotation.
    """

    name: str
    """
    Name of the type.
    """

    path: str | None
    """
    path of the definition (e.g. youwol.app.environment.youwol_environment.YouwolEnvironment).
    """

    generics: list[DocTypeResponse | None] = []
    """
    The list of generics type.
    """


class DocCodeResponse(BaseModel):
    """
    Description of a code fragment.
    """

    filePath: str
    """
    Path the file.
    """

    content: str
    """
    Code fragment content.
    """

    startLine: int
    """
    Starting line number.
    """

    endLine: int
    """
    Ending line number.
    """


class DocParameterResponse(BaseModel):
    """
    Description of a method's parameter.
    """

    name: str
    """
    Name of the parameter.
    """

    type: DocTypeResponse | None
    """
    Type of the parameter if available.
    """

    docstring: str | None
    """
    Docstring associated if provided.
    """


class DocReturnsResponse(BaseModel):
    """
    Description of a method's return.
    """

    type: DocTypeResponse | None
    """
    Return type if provided.
    """

    docstring: str | None
    """
    Docstring associated if provided.
    """


class DocAttributeResponse(BaseModel):
    """
    Description of an attribute.
    """

    name: str
    """
    Name of the attribute.
    """

    type: DocTypeResponse | None
    """
    Attribute's type if provided.
    """

    docstring: list[DocDocstringSectionResponse]
    """
    Docstring associated if provided.
    """

    path: str
    """
    Path of the attribute (e.g. youwol.app.environment.youwol_environment.YouwolEnvironment.httpPort)
    """

    code: DocCodeResponse
    """
    Associated code snippet.
    """


class DocDecoratorResponse(BaseModel):
    """
    Description of a decorator
    """

    path: str


class DocFunctionResponse(BaseModel):
    """
    Description of a function.
    """

    name: str
    """
    Name of the function.
    """

    docstring: list[DocDocstringSectionResponse]
    """
    Docstring associated if provided.
    """

    path: str
    """
    Path of the function (e.g. youwol.app.environment.youwol_environment.yw_config).
    """

    decorators: list[DocDecoratorResponse]
    """
    List of the decorators.
    """

    parameters: list[DocParameterResponse]
    """
    List of the function parameters.
    """

    returns: DocReturnsResponse | None
    """
    Return description.
    """

    code: DocCodeResponse
    """
    Associated code snippet.
    """


class DocClassResponse(BaseModel):
    """
    Description of a class.
    """

    name: str
    """
    Name of the class.
    """

    docstring: list[DocDocstringSectionResponse]
    """
    Docstring associated.
    """

    bases: list[DocTypeResponse]
    """
    Description of the base classes.
    """

    path: str
    """
    Path of the class  (e.g. youwol.app.environment.youwol_environment.YouwolEnvironment).
    """

    attributes: list[DocAttributeResponse]
    """
    Description of the class's attributes.
    """

    methods: list[DocFunctionResponse]
    """
    Description of the class's methods.
    """

    code: DocCodeResponse
    """
    Associated code snippet.
    """

    inheritedBy: list[DocTypeResponse]
    """
    Classes inheriting this class.
    """


class DocChildModulesResponse(BaseModel):
    """
    Light description of a module.
    """

    name: str
    """
    Name of the module.
    """

    path: str
    """
    Path of the module (e.g. youwol.app.environment).
    """

    isLeaf: bool
    """
    Whether this child module is a leaf (does not contains anymore modules).
    """


class DocFileResponse(BaseModel):
    name: str
    """
    Name of the file  (e.g. `youwol_environment`).
    """

    path: str
    """
    Path of the file  (e.g. `youwol.app.environment.youwol_environment`).
    """

    docstring: list[DocDocstringSectionResponse]
    """
    Docstring associated.
    """


class DocModuleResponse(BaseModel):
    """
    Full description of a module.
    """

    name: str
    """
    Name of the module.
    """

    docstring: list[DocDocstringSectionResponse]
    """
    Associated docstring.
    """

    path: str
    """
    Path of the module (e.g. youwol.app.environment).
    """

    childrenModules: list[DocChildModulesResponse]
    """
    Description of its sub modules.
    """

    attributes: list[DocAttributeResponse]
    """
    Description of its attributes.
    """

    classes: list[DocClassResponse]
    """
    Description of its classes.
    """

    functions: list[DocFunctionResponse]
    """
    Description of its functions.
    """

    files: list[DocFileResponse]
    """
    Description of its files.
    """


class DocCrossLinkErrorResponse(BaseModel):
    """
    Describes an error regarding cross-linking in docstrings.
    """

    path: str
    """
    Canonical path of the symbol bound to the associated docstring.
    """
    startLine: int
    """
    Start line number of the associated docstring in the file.
    """
    endLine: int
    """
    End line number of the associated docstring in the file.
    """
    error: str
    """
    Error description.
    """


class DocAnalysisResponse(BaseModel):
    """
    Analysis report of the youwol's inlined documentation.
    """

    crossLinkErrors: list[DocCrossLinkErrorResponse]
    """
    Errors regarding cross-links.
    """


class DocCache:
    flat_classes: set[type] = set()
    all_symbols: list[str] = []
    # For some symbols, we can not get the parent file automatically, they are explicitly provided here.
    module_to_file_issues = {
        # This type alias definition cause trouble to retrieve the parent file.
        # We could look for all the files in the module with the substring e.g. 'JSON =', but seems inefficient.
        # Waiting like that until a better options is found.
        "youwol.utils.JSON": "youwol.utils.types.JSON"
    }
    global_doc: Module = None
    modules_doc: dict[str, DocModuleResponse] = {}
