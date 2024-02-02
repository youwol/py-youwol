# standard library
import functools
import importlib
import inspect

from pathlib import Path, PosixPath
from types import ModuleType

# typing
from typing import List, Optional, Set, Type, Union

# third parties
from griffe.dataclasses import (
    Alias,
    Attribute,
    Class,
    Docstring,
    Function,
    Module,
    Parameter,
)
from griffe.docstrings.dataclasses import (
    DocstringSection,
    DocstringSectionAdmonition,
    DocstringSectionParameters,
    DocstringSectionText,
)
from griffe.expressions import (
    Expr,
    ExprAttribute,
    ExprBinOp,
    ExprList,
    ExprName,
    ExprSubscript,
    ExprTuple,
)

# Youwol
import youwol

# Youwol application
from youwol.app.routers.system.documentation_models import (
    DocAttributeResponse,
    DocCache,
    DocChildModulesResponse,
    DocClassResponse,
    DocCodeResponse,
    DocDecoratorResponse,
    DocDocstringSectionResponse,
    DocFunctionResponse,
    DocModuleResponse,
    DocParameterResponse,
    DocReturnsResponse,
    DocTypeResponse,
)

# Youwol utilities
from youwol.utils import log_error

__init__filename = "__init__.py"
youwol_module = "youwol"


def is_leaf_module(path: str) -> bool:
    module_doc = functools.reduce(
        lambda acc, e: acc.modules[e] if e else acc,
        path.split("."),
        DocCache.global_doc,
    )

    no_alias = {k: v for k, v in module_doc.modules.items() if not isinstance(v, Alias)}
    children = [
        k
        for k, v in no_alias.items()
        if isinstance(v.filepath, PosixPath)
        and v.filepath.name == __init__filename
        and v.docstring
    ]
    return len(children) == 0


def format_module_doc(griffe_doc: Module, path: str) -> DocModuleResponse:
    no_alias = {k: v for k, v in griffe_doc.modules.items() if not isinstance(v, Alias)}
    true_modules = [
        DocChildModulesResponse(
            name=k,
            path=f"{path}.{k}",
            isLeaf=is_leaf_module(path=f"{path}.{k}"),
        )
        for k, v in no_alias.items()
        if isinstance(v.filepath, PosixPath)
        and v.filepath.name == __init__filename
        and v.docstring
    ]
    files = {k: v for k, v in no_alias.items() if k not in true_modules}
    classes = [
        format_class_doc(c)
        for v in files.values()
        for c in v.classes.values()
        if isinstance(c, Class) and c.docstring
    ]
    functions = [
        format_function_doc(f)
        for v in files.values()
        for f in v.functions.values()
        if isinstance(f, Function) and f.docstring
    ]
    attributes = [
        format_attribute_doc(a)
        for v in files.values()
        for a in v.attributes.values()
        if isinstance(a, Attribute) and a.docstring
    ]
    sections = get_docstring_sections(griffe_doc)
    return DocModuleResponse(
        name=griffe_doc.name,
        path=path,
        docstring=format_detailed_docstring(sections=sections),
        childrenModules=sorted(true_modules, key=lambda m: m.name),
        attributes=sorted(attributes, key=lambda m: m.name),
        classes=sorted(classes, key=lambda c: c.name),
        functions=sorted(functions, key=lambda c: c.name),
    )


def get_symbol_path(griffe_doc: Union[Class, Function, Attribute, Module]) -> str:
    path = griffe_doc.name
    it = griffe_doc
    while it.parent:
        path = f"{it.parent.name}.{path}"
        it = it.parent

    return path


def get_docstring_sections(
    griffe_doc: Union[Class, Function, Attribute, Module]
) -> List[DocstringSection]:
    if not griffe_doc.docstring:
        # This should not normally happen because only symbols with docstring are reported.
        # However, it is possible to request the documentation of a module that do not
        # have docstring.
        log_error(f"No docstring available for '{get_symbol_path(griffe_doc)}'")

    docstring_text = griffe_doc.docstring.value if griffe_doc.docstring else ""

    docstring = Docstring(
        docstring_text,
        parent=griffe_doc,
    )
    return docstring.parse("google")


def format_class_doc(griffe_doc: Class) -> DocClassResponse:
    parent_module = ".".join(griffe_doc.canonical_path.split(".")[0:-1])
    my_module = importlib.import_module(parent_module)
    my_class = getattr(my_module, griffe_doc.name)
    inherited = get_classes_inheriting_from(my_class)

    return DocClassResponse(
        name=griffe_doc.name,
        docstring=format_detailed_docstring(get_docstring_sections(griffe_doc)),
        path=str(griffe_doc.path),
        inheritedBy=[
            DocTypeResponse(name=d.__name__, path=f"{d.__module__}.{d.__name__}")
            for d in inherited
        ],
        bases=[format_type_annotation_doc(base) for base in griffe_doc.bases],
        attributes=[
            format_attribute_doc(attr)
            for attr in griffe_doc.attributes.values()
            if attr.docstring
        ],
        methods=[
            format_function_doc(f)
            for f in griffe_doc.functions.values()
            if f and f.docstring
        ],
        code=format_code_doc(griffe_doc),
    )


def format_code_doc(griffe_doc: Union[Class, Function, Attribute]) -> DocCodeResponse:
    return DocCodeResponse(
        filePath=str(griffe_doc.filepath),
        startLine=griffe_doc.lineno,
        endLine=griffe_doc.endlineno,
        content=functools.reduce(lambda acc, e: f"{acc}\n{e}", griffe_doc.lines),
    )


def format_function_doc(griffe_doc: Function) -> DocFunctionResponse:
    parsed = get_docstring_sections(griffe_doc)
    sections = [
        p
        for p in parsed
        if isinstance(p, DocstringSectionText)
        or (isinstance(p, DocstringSectionAdmonition) and p.title != "Return")
    ]
    params = next(
        (p for p in parsed if isinstance(p, DocstringSectionParameters)), None
    )
    returns = next(
        (
            p
            for p in parsed
            if isinstance(p, DocstringSectionAdmonition) and p.title == "Return"
        ),
        None,
    )

    formatted = format_detailed_docstring(sections)
    returns_doc = None
    if returns:
        try:
            returns_doc = DocReturnsResponse(
                type=format_type_annotation_doc(griffe_doc.returns),
                docstring=returns.value.description,
            )
        except Exception as e:
            log_error(f"Failed to parse return of function {griffe_doc.name}: {e}")

    return DocFunctionResponse(
        name=griffe_doc.name,
        docstring=formatted,
        decorators=[
            DocDecoratorResponse(path=d.value.path) for d in griffe_doc.decorators
        ],
        path=str(griffe_doc.path),
        parameters=[format_parameter_doc(p, params) for p in griffe_doc.parameters],
        returns=returns_doc,
        code=format_code_doc(griffe_doc),
    )


def format_detailed_docstring(
    sections: List[DocstringSection],
) -> List[DocDocstringSectionResponse]:
    def admonition(v: DocstringSectionAdmonition) -> DocDocstringSectionResponse:
        return DocDocstringSectionResponse(
            type="admonition",
            title=v.title,
            tag=v.value.annotation,
            text=v.value.description,
        )

    def text(v: DocstringSectionText) -> DocDocstringSectionResponse:
        return DocDocstringSectionResponse(type="text", title=v.title, text=v.value)

    def factory(v: DocstringSection):
        if isinstance(v, DocstringSectionAdmonition):
            return admonition(v)
        if isinstance(v, DocstringSectionText):
            return text(v)
        return None

    formatted = [factory(s) for s in sections]

    return [s for s in formatted if s]


def format_parameter_doc(
    griffe_doc: Parameter, parameters: Optional[DocstringSectionParameters]
) -> Optional[DocParameterResponse]:
    docstring = (
        next(
            (p.description for p in parameters.value if p.name == griffe_doc.name), None
        )
        if parameters
        else None
    )
    return DocParameterResponse(
        name=griffe_doc.name,
        type=format_type_annotation_doc(griffe_doc.annotation),
        docstring=docstring,
    )


def format_attribute_doc(griffe_doc: Attribute) -> DocAttributeResponse:
    sections = get_docstring_sections(griffe_doc)
    docstring = format_detailed_docstring(sections=sections)
    if not griffe_doc.annotation:
        return DocAttributeResponse(
            name=griffe_doc.name,
            path=griffe_doc.canonical_path,
            docstring=docstring,
            code=format_code_doc(griffe_doc),
        )
    return DocAttributeResponse(
        name=griffe_doc.name,
        type=format_type_annotation_doc(griffe_doc.annotation),
        docstring=docstring,
        path=griffe_doc.canonical_path,
        code=format_code_doc(griffe_doc),
    )


def format_type_annotation_doc(
    griffe_doc: Union[Expr, str],
) -> Optional[Union[DocTypeResponse, List[DocTypeResponse]]]:
    if isinstance(griffe_doc, str):
        # The case of string literals
        return DocTypeResponse(name=griffe_doc)

    if isinstance(griffe_doc, ExprName):
        return DocTypeResponse(name=griffe_doc.name, path=patch_import_path(griffe_doc))

    if isinstance(griffe_doc, ExprSubscript):
        generics = format_type_annotation_doc(griffe_doc.slice)
        return DocTypeResponse(
            name=griffe_doc.canonical_name,
            path=griffe_doc.canonical_path,
            generics=generics if isinstance(generics, list) else [generics],
        )
    if isinstance(griffe_doc, ExprList):
        return DocTypeResponse(
            name="",
            path=griffe_doc.canonical_path,
            generics=[format_type_annotation_doc(e) for e in griffe_doc.elements],
        )

    if isinstance(griffe_doc, ExprAttribute):
        # This happens when e.g.  'import io' and use 'io.Bytes'
        return DocTypeResponse(
            name=griffe_doc.canonical_name,
            path=griffe_doc.canonical_path,
            generics=[],
        )

    if isinstance(griffe_doc, ExprTuple):
        return [format_type_annotation_doc(e) for e in griffe_doc.elements]

    if isinstance(griffe_doc, ExprBinOp) and griffe_doc.operator == "|":
        return DocTypeResponse(
            name="Union",
            path="typing.Union",
            generics=[
                format_type_annotation_doc(griffe_doc=griffe_doc.left),
                format_type_annotation_doc(griffe_doc=griffe_doc.right),
            ],
        )

    return None


def format_docstring_doc(griffe_doc: Optional[Docstring]) -> Optional[str]:
    if not griffe_doc:
        return None
    return functools.reduce(lambda acc, e: acc + e.value, griffe_doc.parsed, "")


def patch_import_path(griffe_doc: Expr) -> str:
    if youwol_module not in griffe_doc.canonical_path:
        return griffe_doc.canonical_path

    parent_module = ".".join(griffe_doc.canonical_path.split(".")[0:-1])
    my_module = importlib.import_module(parent_module)
    if __init__filename not in str(my_module):
        return griffe_doc.canonical_path
    module_file_path = Path(my_module.__file__).parent

    try:
        # There are problems in the following try at least for some type aliasing definition.
        my_class = getattr(my_module, griffe_doc.canonical_name)
        filename = Path(inspect.getfile(my_class)).relative_to(module_file_path)
        relative_import = ".".join(filename.with_suffix("").parts)
        path = f"{parent_module}.{relative_import}.{griffe_doc.canonical_name}"
        return path
    except (RuntimeError, TypeError):
        if griffe_doc.canonical_path in DocCache.module_to_file_issues:
            return DocCache.module_to_file_issues[griffe_doc.canonical_path]
        log_error(f"Can not find parent file of symbol {griffe_doc.canonical_path}")
        return griffe_doc.canonical_path


def init_classes(module: ModuleType = None, visited: Set[ModuleType] = None):
    if not visited:
        visited = set()

    if not module:
        module = youwol
    visited.add(module)

    for name, obj in inspect.getmembers(module):
        if (
            not name.startswith("__")
            and youwol_module in str(obj)
            and inspect.isclass(obj)
        ):
            DocCache.flat_classes.add(obj)

    for _, submodule in inspect.getmembers(module, inspect.ismodule):
        if youwol_module in str(submodule) and submodule not in visited:
            init_classes(submodule, visited)


def get_classes_inheriting_from(target: Type) -> Set[Type]:
    def is_inherited(c: Type):
        if c == target:
            return False
        try:
            return issubclass(c, target)
        except TypeError:
            # Silently fails if somehow an element of `DocCache.flat_classes` can not be used in `issubclass` as type.
            # The return `False` is still correct.
            return False

    return {c for c in DocCache.flat_classes if is_inherited(c)}
