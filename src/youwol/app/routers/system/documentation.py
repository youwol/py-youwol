# standard library
import dataclasses
import functools
import importlib
import inspect
import os
import re

from pathlib import Path, PosixPath
from types import ModuleType

# typing
from typing import Literal, cast

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
    DocCrossLinkErrorResponse,
    DocDecoratorResponse,
    DocDocstringSectionResponse,
    DocFileResponse,
    DocFunctionResponse,
    DocModuleResponse,
    DocParameterResponse,
    DocReturnsResponse,
    DocTypeResponse,
)

# Youwol utilities
from youwol.utils import log_error

INIT_FILENAME = "__init__.py"
YOUWOL_MODULE = "youwol"


@dataclasses.dataclass(frozen=True)
class ModuleElements:
    modules: list[Module]
    files: list[Module]
    classes: list[Class]
    functions: list[Function]
    attributes: list[Attribute]


def extract_module(griffe_doc: Module) -> ModuleElements:

    no_alias = {k: v for k, v in griffe_doc.modules.items() if not isinstance(v, Alias)}

    modules = [
        v
        for k, v in no_alias.items()
        if isinstance(v.filepath, PosixPath)
        and v.filepath.name == INIT_FILENAME
        and v.docstring
    ]
    files = [v for k, v in no_alias.items() if k not in modules]
    classes = [
        c
        for v in files
        for c in v.classes.values()
        if isinstance(c, Class) and c.docstring
    ]
    functions = [
        f
        for v in files
        for f in v.functions.values()
        if isinstance(f, Function) and f.docstring
    ]
    attributes = [
        a
        for v in files
        for a in v.attributes.values()
        if isinstance(a, Attribute) and a.docstring
    ]
    return ModuleElements(
        modules=modules,
        files=files,
        classes=classes,
        functions=functions,
        attributes=attributes,
    )


def is_leaf_module(path: str) -> bool:
    module_doc = functools.reduce(
        lambda acc, e: acc.modules[e] if e else acc,
        path.replace("youwol.", "").split("."),
        DocCache.global_doc,
    )

    no_alias = {k: v for k, v in module_doc.modules.items() if not isinstance(v, Alias)}
    children = [
        k
        for k, v in no_alias.items()
        if isinstance(v.filepath, PosixPath)
        and v.filepath.name == INIT_FILENAME
        and v.docstring
    ]
    return len(children) == 0


def format_module_doc(griffe_doc: Module, path: str) -> DocModuleResponse:

    elements = extract_module(griffe_doc=griffe_doc)
    modules = [format_child_module_doc(m) for m in elements.modules]
    classes = [format_class_doc(c) for c in elements.classes]
    functions = [format_function_doc(f) for f in elements.functions]
    attributes = [format_attribute_doc(a) for a in elements.attributes]
    files = [format_file_doc(f) for f in elements.files]
    sections = get_docstring_sections(griffe_doc)

    return DocModuleResponse(
        name=griffe_doc.name,
        path=path,
        docstring=format_detailed_docstring(sections=sections, parent=griffe_doc),
        childrenModules=sorted(modules, key=lambda m: m.name),
        attributes=sorted(attributes, key=lambda m: m.name),
        classes=sorted(classes, key=lambda c: c.name),
        functions=sorted(functions, key=lambda c: c.name),
        files=sorted(files, key=lambda c: c.name),
    )


def get_symbol_path(griffe_doc: Class | Function | Attribute | Module) -> str:
    path = griffe_doc.name
    it = griffe_doc
    while it.parent:
        path = f"{it.parent.name}.{path}"
        it = it.parent

    return path


def get_docstring_sections(
    griffe_doc: Class | Function | Attribute | Module,
) -> list[DocstringSection]:
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


def format_child_module_doc(griffe_doc: Module) -> DocChildModulesResponse:
    return DocChildModulesResponse(
        name=griffe_doc.name,
        path=griffe_doc.canonical_path,
        isLeaf=is_leaf_module(path=griffe_doc.canonical_path),
    )


def format_file_doc(griffe_doc: Module) -> DocFileResponse:
    return DocFileResponse(
        name=griffe_doc.name,
        path=griffe_doc.canonical_path,
        docstring=format_detailed_docstring(
            get_docstring_sections(griffe_doc), parent=griffe_doc
        ),
    )


def format_class_doc(griffe_doc: Class) -> DocClassResponse:
    parent_module = ".".join(griffe_doc.canonical_path.split(".")[0:-1])
    my_module = importlib.import_module(parent_module)
    my_class = getattr(my_module, griffe_doc.name)
    inherited = get_classes_inheriting_from(my_class)

    return DocClassResponse(
        name=griffe_doc.name,
        docstring=format_detailed_docstring(
            get_docstring_sections(griffe_doc), parent=griffe_doc
        ),
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


def format_code_doc(griffe_doc: Class | Function | Attribute) -> DocCodeResponse:
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

    formatted = format_detailed_docstring(sections, parent=griffe_doc)
    returns_doc = None
    if returns:
        try:
            returns_doc = DocReturnsResponse(
                type=format_type_annotation_doc(griffe_doc.returns),
                docstring=replace_links(
                    returns.value.description, from_module=griffe_doc.canonical_path
                ),
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
        parameters=[
            format_parameter_doc(p, params, function=griffe_doc)
            for p in griffe_doc.parameters
        ],
        returns=returns_doc,
        code=format_code_doc(griffe_doc),
    )


cross_ref_pattern = re.compile(
    r"\[(.*?)]\(@yw-nav-(mod|class|attr|meth|glob|func):(.*?)\)"
)

CrossLink = Literal["mod", "class", "attr", "meth", "func", "glob"]


def get_cross_link_candidates(
    link_type: CrossLink, short_link: str, all_symbols: list[str]
):

    short_link_sanitized = (
        short_link if short_link.startswith("youwol") else f".{short_link}"
    )
    parent = ".".join(short_link_sanitized.split(".")[0:-1])

    return (
        [s for s in all_symbols if s.endswith(short_link_sanitized)]
        if link_type in {"mod", "class", "func", "glob"}
        else [s for s in all_symbols if s.endswith(parent)]
    )


def replace_links(text: str, from_module: str) -> str:

    def pick_best_candidate(candidates: list[str]) -> str | None:
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]
        longest_prefix = [
            os.path.commonprefix([from_module, candidate]) for candidate in candidates
        ]
        best_index, _ = max(enumerate(longest_prefix), key=lambda x: len(x[1]))
        return candidates[best_index]

    def replace_function(match):
        title = match.group(1)
        link_type: CrossLink = match.group(2)
        short_link: str = match.group(3)
        candidates = get_cross_link_candidates(
            link_type=match.group(2),
            short_link=match.group(3),
            all_symbols=DocCache.all_symbols,
        )

        best = pick_best_candidate(candidates)
        if link_type in {"mod", "class", "func", "glob"}:
            return f"[{title}](@yw-nav-{link_type}:{best or short_link})"

        if not best:
            return f"[{title}](@yw-nav-{link_type}:{short_link})"

        return f"[{title}](@yw-nav-{link_type}:{best}.{short_link.split('.')[-1]})"

    return re.sub(cross_ref_pattern, replace_function, text)


def format_detailed_docstring(
    sections: list[DocstringSection], parent: Function | Class | Attribute | Module
) -> list[DocDocstringSectionResponse]:
    def admonition(v: DocstringSectionAdmonition) -> DocDocstringSectionResponse:
        return DocDocstringSectionResponse(
            type="admonition",
            title=v.title,
            tag=v.value.annotation,
            text=replace_links(v.value.description, from_module=parent.canonical_path),
        )

    def text(v: DocstringSectionText) -> DocDocstringSectionResponse:
        return DocDocstringSectionResponse(
            type="text",
            title=v.title,
            text=replace_links(v.value, from_module=parent.canonical_path),
        )

    def factory(v: DocstringSection):
        if isinstance(v, DocstringSectionAdmonition):
            return admonition(v)
        if isinstance(v, DocstringSectionText):
            return text(v)
        return None

    formatted = [factory(s) for s in sections]

    return [s for s in formatted if s]


def format_parameter_doc(
    griffe_doc: Parameter,
    parameters: DocstringSectionParameters | None,
    function: Function,
) -> DocParameterResponse | None:
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
        docstring=docstring
        and replace_links(docstring, from_module=function.canonical_path),
    )


def format_attribute_doc(griffe_doc: Attribute) -> DocAttributeResponse:
    sections = get_docstring_sections(griffe_doc)
    docstring = format_detailed_docstring(sections=sections, parent=griffe_doc)
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
    griffe_doc: Expr | str,
) -> DocTypeResponse | list[DocTypeResponse] | None:
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


def format_docstring_doc(griffe_doc: Docstring | None) -> str | None:
    if not griffe_doc:
        return None
    return functools.reduce(lambda acc, e: acc + e.value, griffe_doc.parsed, "")


def patch_import_path(griffe_doc: Expr) -> str:
    if YOUWOL_MODULE not in griffe_doc.canonical_path:
        return griffe_doc.canonical_path

    parent_module = ".".join(griffe_doc.canonical_path.split(".")[0:-1])
    my_module = importlib.import_module(parent_module)
    if INIT_FILENAME not in str(my_module):
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


def init_classes(module: ModuleType = None, visited: set[ModuleType] = None):
    if not visited:
        visited = set()

    if not module:
        module = youwol
    visited.add(module)

    for name, obj in inspect.getmembers(module):
        if (
            not name.startswith("__")
            and YOUWOL_MODULE in str(obj)
            and inspect.isclass(obj)
        ):
            DocCache.flat_classes.add(obj)

    for _, submodule in inspect.getmembers(module, inspect.ismodule):
        if YOUWOL_MODULE in str(submodule) and submodule not in visited:
            init_classes(submodule, visited)


def init_symbols(module: Module, depth=0, max_depth=10) -> list[str]:
    if depth > max_depth:
        raise RecursionError("Maximum recursion depth reached")

    elements = extract_module(griffe_doc=module)
    functions = [f.canonical_path for f in elements.functions]
    classes = [c.canonical_path for c in elements.classes]
    attributes = [a.canonical_path for a in elements.attributes]
    sub_modules = [
        e
        for module in elements.modules
        for e in init_symbols(module=module, depth=depth + 1, max_depth=max_depth)
    ]
    return [module.canonical_path, *functions, *classes, *attributes, *sub_modules]


def get_classes_inheriting_from(target: type) -> set[type]:
    def is_inherited(c: type):
        if c == target:
            return False
        try:
            return issubclass(c, target)
        except TypeError:
            # Silently fails if somehow an element of `DocCache.flat_classes` can not be used in `issubclass` as type.
            # The return `False` is still correct.
            return False

    return {c for c in DocCache.flat_classes if is_inherited(c)}


def check_documentation(
    module: Module, depth=0, max_depth=10, all_symbols=None
) -> list[DocCrossLinkErrorResponse]:
    all_symbols = all_symbols or init_symbols(module)

    if depth > max_depth:
        raise RecursionError("Maximum recursion depth reached")

    def analyze(docstring: Docstring, match: list[str]):
        candidates = get_cross_link_candidates(
            link_type=cast(CrossLink, match[1]),
            short_link=match[2],
            all_symbols=all_symbols,
        )
        params = {
            "path": docstring.parent.canonical_path,
            "startLine": docstring.lineno,
            "endLine": docstring.endlineno,
        }
        if not candidates:
            return DocCrossLinkErrorResponse(
                error=f"No candidate found for {match[2]}", **params
            )
        if len(candidates) > 1:
            return DocCrossLinkErrorResponse(
                error=f"Multiple candidates found for {match[2]}: {candidates}",
                **params,
            )
        return None

    elements = extract_module(griffe_doc=module)
    docstrings = [
        f.docstring
        for f in [
            module,
            *elements.functions,
            *elements.classes,
            *elements.attributes,
            *elements.files,
        ]
        if f.docstring
    ]
    all_matches = [
        (docstring, cross_ref_pattern.findall(docstring.value))
        for docstring in docstrings
    ]
    errors = [
        analyze(docstring=docstring, match=match)
        for docstring, matches in all_matches
        for match in matches
    ]
    errors = [e for e in errors if e is not None]
    sub_modules = [
        e
        for module in elements.modules
        for e in check_documentation(
            module=module, depth=depth + 1, max_depth=max_depth, all_symbols=all_symbols
        )
    ]

    return [*errors, *sub_modules]
