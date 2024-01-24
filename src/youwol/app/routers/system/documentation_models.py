# future
from __future__ import annotations

# typing
from typing import Dict, List, Literal, Optional, Set, Type

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
    tag: Optional[str]
    """
    Tag name for an admonition.
    """
    title: Optional[str]
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

    path: Optional[str]
    """
    path of the definition (e.g. youwol.app.environment.youwol_environment.YouwolEnvironment).
    """

    generics: List[Optional[DocTypeResponse]] = []
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

    type: Optional[DocTypeResponse]
    """
    Type of the parameter if available.
    """

    docstring: Optional[str]
    """
    Docstring associated if provided.
    """


class DocReturnsResponse(BaseModel):
    """
    Description of a method's return.
    """

    type: Optional[DocTypeResponse]
    """
    Return type if provided.
    """

    docstring: Optional[str]
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

    type: Optional[DocTypeResponse]
    """
    Attribute's type if provided.
    """

    docstring: List[DocDocstringSectionResponse]
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

    docstring: List[DocDocstringSectionResponse]
    """
    Docstring associated if provided.
    """

    path: str
    """
    Path of the function (e.g. youwol.app.environment.youwol_environment.yw_config).
    """

    decorators: List[DocDecoratorResponse]
    """
    List of the decorators.
    """

    parameters: List[DocParameterResponse]
    """
    List of the function parameters.
    """

    returns: Optional[DocReturnsResponse]
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

    docstring: List[DocDocstringSectionResponse]
    """
    Docstring associated.
    """

    bases: List[DocTypeResponse]
    """
    Description of the base classes.
    """

    path: str
    """
    Path of the class  (e.g. youwol.app.environment.youwol_environment.YouwolEnvironment).
    """

    attributes: List[DocAttributeResponse]
    """
    Description of the class's attributes.
    """

    methods: List[DocFunctionResponse]
    """
    Description of the class's methods.
    """

    code: DocCodeResponse
    """
    Associated code snippet.
    """

    inheritedBy: List[DocTypeResponse]
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


class DocModuleResponse(BaseModel):
    """
    Full description of a module.
    """

    name: str
    """
    Name of the module.
    """

    docstring: List[DocDocstringSectionResponse]
    """
    Associated docstring.
    """

    path: str
    """
    Path of the module (e.g. youwol.app.environment).
    """

    childrenModules: List[DocChildModulesResponse]
    """
    Description of its sub modules.
    """

    attributes: List[DocAttributeResponse]
    """
    Description of its attributes.
    """

    classes: List[DocClassResponse]
    """
    Description of its classes.
    """

    functions: List[DocFunctionResponse]
    """
    Description of its functions.
    """


class DocCache:
    flat_classes: Set[Type] = set()
    # For some symbols, we can not get the parent file automatically, they are explicitly provided here.
    module_to_file_issues = {
        # This type alias definition cause trouble to retrieve the parent file.
        # We could look for all the files in the module with the substring e.g. 'JSON =', but seems inefficient.
        # Waiting like that until a better options is found.
        "youwol.utils.JSON": "youwol.utils.types.JSON"
    }
    global_doc: Module = None
    modules_doc: Dict[str, DocModuleResponse] = {}
