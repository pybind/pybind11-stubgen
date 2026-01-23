from __future__ import annotations

import sys
from dataclasses import dataclass
from dataclasses import field as field_
from typing import Tuple, Union

if sys.version_info >= (3, 8):
    from typing import Literal

    Modifier = Literal["static", "class", None]
else:
    from typing import Optional

    Modifier = Optional[str]


class Identifier(str):
    pass


class Decorator(str):
    pass


class Docstring(str):
    pass


@dataclass
class InvalidExpression:
    text: str

    def __str__(self):
        return f"Invalid python expression `{self.text}`"


class QualifiedName(Tuple[Identifier, ...]):
    """Fully Qualified Name"""

    @classmethod
    def from_str(cls, name: str) -> QualifiedName:
        return QualifiedName(Identifier(part) for part in name.split("."))

    def __str__(self):
        return ".".join(self)

    @property
    def parent(self) -> QualifiedName:
        return QualifiedName(self[:-1])


@dataclass
class Value:
    repr: str
    is_print_safe: bool = False  # `self.repr` is valid python and safe to print as is

    def __str__(self):
        return self.repr


@dataclass
class ResolvedType:
    name: QualifiedName
    parameters: list[ResolvedType | Value | InvalidExpression] | None = field_(
        default=None
    )

    def __str__(self):
        if self.parameters:
            param_str = "[" + ", ".join(str(p) for p in self.parameters) + "]"
        else:
            param_str = ""
        return f"{self.name}{param_str}"


@dataclass
class Alias:
    name: Identifier
    origin: QualifiedName


Annotation = Union[ResolvedType, Value, InvalidExpression]


@dataclass
class TypeVar_:
    name: Identifier
    constraints: list[Annotation] = field_(default_factory=list)
    bound: Annotation | None = field_(default=None)
    covariant: bool = field_(default=False)
    contravariant: bool = field_(default=False)

    def __str__(self) -> str:
        return (
            f'{self.name} = typing.TypeVar("{self.name}"'
            + (", " if self.constraints else "")
            + (", ".join(str(c) for c in self.constraints))
            + (f", bound={str(self.bound)}" if self.bound is not None else "")
            + (f", covariant={self.covariant}" if self.covariant else "")
            + (f", contravariant={self.contravariant}" if self.contravariant else "")
            + ")"
        )


@dataclass
class Attribute:
    name: Identifier
    value: Value | None
    annotation: Annotation | None = field_(default=None)
    doc: Docstring | None = field_(default=None)


@dataclass
class Argument:
    name: Identifier | None
    pos_only: bool = field_(default=False)
    kw_only: bool = field_(default=False)
    variadic: bool = field_(default=False)  # *args
    kw_variadic: bool = field_(default=False)  # **kwargs
    default: Value | InvalidExpression | None = field_(default=None)
    annotation: Annotation | None = field_(default=None)

    def __str__(self):
        result = []
        if self.variadic:
            result += ["*"]
        if self.kw_variadic:
            result += ["**"]
        result += [f"{self.name}"]
        if self.annotation:
            result += [f": {self.annotation}"]
        if self.default:
            result += [f" = {self.default}"]

        return "".join(result)


@dataclass
class Function:
    name: Identifier
    args: list[Argument] = field_(default_factory=list)
    returns: Annotation | None = field_(default=None)
    doc: Docstring | None = field_(default=None)
    decorators: list[Decorator] = field_(default_factory=list)

    def __str__(self):
        return (
            f"{self.name}({', '.join(str(arg) for arg in self.args)}) -> {self.returns}"
        )


@dataclass
class Property:
    name: Identifier
    modifier: Modifier
    doc: Docstring | None = field_(default=None)
    getter: Function | None = field_(default=None)
    setter: Function | None = field_(default=None)


@dataclass
class Method:
    function: Function
    modifier: Modifier


@dataclass
class Field:
    attribute: Attribute
    modifier: Modifier


@dataclass
class Class:
    name: Identifier
    doc: Docstring | None = field_(default=None)
    bases: list[QualifiedName] = field_(default_factory=list)
    classes: list[Class] = field_(default_factory=list)
    fields: list[Field] = field_(default_factory=list)
    methods: list[Method] = field_(default_factory=list)
    properties: list[Property] = field_(default_factory=list)
    aliases: list[Alias] = field_(default_factory=list)


@dataclass(eq=True, frozen=True)
class Import:
    name: Identifier | None
    origin: QualifiedName


@dataclass
class Module:
    name: Identifier
    doc: Docstring | None = field_(default=None)
    classes: list[Class] = field_(default_factory=list)
    functions: list[Function] = field_(default_factory=list)
    sub_modules: list[Module] = field_(default_factory=list)
    attributes: list[Attribute] = field_(default_factory=list)
    imports: set[Import] = field_(default_factory=set)
    aliases: list[Alias] = field_(default_factory=list)
    type_vars: list[TypeVar_] = field_(default_factory=list)
    is_package: bool = field_(default=False)
