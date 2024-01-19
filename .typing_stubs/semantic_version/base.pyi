# standard library
from collections.abc import Generator

# third parties
from _typeshed import Incomplete

class MaxIdentifier:
    def __eq__(self, other): ...

class NumericIdentifier:
    value: Incomplete
    def __init__(self, value) -> None: ...
    def __eq__(self, other): ...
    def __lt__(self, other): ...

class AlphaIdentifier:
    value: Incomplete
    def __init__(self, value) -> None: ...
    def __eq__(self, other): ...
    def __lt__(self, other): ...

class Version:
    version_re: Incomplete
    partial_version_re: Incomplete
    major: Incomplete
    minor: Incomplete
    patch: Incomplete
    prerelease: Incomplete
    build: Incomplete
    partial: Incomplete
    def __init__(
        self,
        version_string: Incomplete | None = ...,
        major: Incomplete | None = ...,
        minor: Incomplete | None = ...,
        patch: Incomplete | None = ...,
        prerelease: Incomplete | None = ...,
        build: Incomplete | None = ...,
        partial: bool = ...,
    ) -> None: ...
    def next_major(self): ...
    def next_minor(self): ...
    def next_patch(self): ...
    def truncate(self, level: str = ...): ...
    @classmethod
    def coerce(cls, version_string, partial: bool = ...): ...
    @classmethod
    def parse(cls, version_string, partial: bool = ..., coerce: bool = ...): ...
    def __iter__(self): ...
    def __hash__(self): ...
    @property
    def precedence_key(self): ...
    def __cmp__(self, other): ...
    def __eq__(self, other): ...
    def __ne__(self, other): ...
    def __lt__(self, other): ...
    def __le__(self, other): ...
    def __gt__(self, other): ...
    def __ge__(self, other): ...

class SpecItem:
    KIND_ANY: str
    KIND_LT: str
    KIND_LTE: str
    KIND_EQUAL: str
    KIND_SHORTEQ: str
    KIND_EMPTY: str
    KIND_GTE: str
    KIND_GT: str
    KIND_NEQ: str
    KIND_CARET: str
    KIND_TILDE: str
    KIND_COMPATIBLE: str
    KIND_ALIASES: Incomplete
    re_spec: Incomplete
    kind: Incomplete
    spec: Incomplete
    def __init__(self, requirement_string, _warn: bool = ...) -> None: ...
    @classmethod
    def parse(cls, requirement_string): ...
    @classmethod
    def from_matcher(cls, matcher): ...
    def match(self, version): ...
    def __eq__(self, other): ...
    def __hash__(self): ...

def compare(v1, v2): ...
def match(spec, version): ...
def validate(version_string): ...

DEFAULT_SYNTAX: str

class BaseSpec:
    SYNTAXES: Incomplete
    @classmethod
    def register_syntax(cls, subclass): ...
    expression: Incomplete
    clause: Incomplete
    def __init__(self, expression) -> None: ...
    @classmethod
    def parse(cls, expression, syntax=...): ...
    def filter(self, versions) -> Generator[Incomplete, None, None]: ...
    def match(self, version): ...
    def select(self, versions): ...
    def __contains__(self, version) -> bool: ...
    def __eq__(self, other): ...
    def __hash__(self): ...

class Clause:
    def match(self, version) -> None: ...
    def __and__(self, other) -> None: ...
    def __or__(self, other) -> None: ...
    def __eq__(self, other): ...
    def prettyprint(self, indent: str = ...): ...
    def __ne__(self, other): ...
    def simplify(self): ...

class AnyOf(Clause):
    clauses: Incomplete
    def __init__(self, *clauses) -> None: ...
    def match(self, version): ...
    def simplify(self): ...
    def __hash__(self): ...
    def __iter__(self): ...
    def __eq__(self, other): ...
    def __and__(self, other): ...
    def __or__(self, other): ...

class AllOf(Clause):
    clauses: Incomplete
    def __init__(self, *clauses) -> None: ...
    def match(self, version): ...
    def simplify(self): ...
    def __hash__(self): ...
    def __iter__(self): ...
    def __eq__(self, other): ...
    def __and__(self, other): ...
    def __or__(self, other): ...

class Matcher(Clause):
    def __and__(self, other): ...
    def __or__(self, other): ...

class Never(Matcher):
    def match(self, version): ...
    def __hash__(self): ...
    def __eq__(self, other): ...
    def __and__(self, other): ...
    def __or__(self, other): ...

class Always(Matcher):
    def match(self, version): ...
    def __hash__(self): ...
    def __eq__(self, other): ...
    def __and__(self, other): ...
    def __or__(self, other): ...

class Range(Matcher):
    OP_EQ: str
    OP_GT: str
    OP_GTE: str
    OP_LT: str
    OP_LTE: str
    OP_NEQ: str
    PRERELEASE_ALWAYS: str
    PRERELEASE_NATURAL: str
    PRERELEASE_SAMEPATCH: str
    BUILD_IMPLICIT: str
    BUILD_STRICT: str
    operator: Incomplete
    target: Incomplete
    prerelease_policy: Incomplete
    build_policy: Incomplete
    def __init__(
        self, operator, target, prerelease_policy=..., build_policy=...
    ) -> None: ...
    def match(self, version): ...
    def __hash__(self): ...
    def __eq__(self, other): ...

class SimpleSpec(BaseSpec):
    SYNTAX: str

    class Parser:
        NUMBER: str
        NAIVE_SPEC: Incomplete
        @classmethod
        def parse(cls, expression): ...
        PREFIX_CARET: str
        PREFIX_TILDE: str
        PREFIX_COMPATIBLE: str
        PREFIX_EQ: str
        PREFIX_NEQ: str
        PREFIX_GT: str
        PREFIX_GTE: str
        PREFIX_LT: str
        PREFIX_LTE: str
        PREFIX_ALIASES: Incomplete
        EMPTY_VALUES: Incomplete
        @classmethod
        def parse_block(cls, expr): ...

class LegacySpec(SimpleSpec):
    def __init__(self, *expressions) -> None: ...
    @property
    def specs(self): ...
    def __iter__(self): ...

Spec = LegacySpec

class NpmSpec(BaseSpec):
    SYNTAX: str

    class Parser:
        JOINER: str
        HYPHEN: str
        NUMBER: str
        PART: str
        NPM_SPEC_BLOCK: Incomplete
        @classmethod
        def range(cls, operator, target): ...
        @classmethod
        def parse(cls, expression): ...
        PREFIX_CARET: str
        PREFIX_TILDE: str
        PREFIX_EQ: str
        PREFIX_GT: str
        PREFIX_GTE: str
        PREFIX_LT: str
        PREFIX_LTE: str
        PREFIX_ALIASES: Incomplete
        PREFIX_TO_OPERATOR: Incomplete
        EMPTY_VALUES: Incomplete
        @classmethod
        def parse_simple(cls, simple): ...
