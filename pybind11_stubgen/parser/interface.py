from __future__ import annotations

import abc
import types
from typing import Any

from pybind11_stubgen.parser.errors import ParserError
from pybind11_stubgen.structs import (
    Alias,
    Argument,
    Attribute,
    Class,
    Docstring,
    Field,
    Function,
    Import,
    InvalidExpression,
    Method,
    Module,
    Property,
    QualifiedName,
    ResolvedType,
    Value,
)


class IParser(abc.ABC):
    @abc.abstractmethod
    def handle_alias(self, path: QualifiedName, origin: Any) -> Alias | None: ...

    @abc.abstractmethod
    def handle_attribute(self, path: QualifiedName, attr: Any) -> Attribute | None: ...

    @abc.abstractmethod
    def handle_bases(
        self, path: QualifiedName, bases: tuple[type, ...]
    ) -> list[QualifiedName]: ...

    @abc.abstractmethod
    def handle_class(self, path: QualifiedName, class_: type) -> Class | None: ...

    @abc.abstractmethod
    def handle_class_member(
        self, path: QualifiedName, class_: type, obj: Any
    ) -> Docstring | Alias | Class | list[Method] | Field | Property | None: ...

    @abc.abstractmethod
    def handle_docstring(self, path: QualifiedName, doc: Any) -> Docstring | None: ...

    @abc.abstractmethod
    def handle_field(self, path: QualifiedName, field: Any) -> Field | None: ...

    @abc.abstractmethod
    def handle_function(self, path: QualifiedName, func: Any) -> list[Function]: ...

    @abc.abstractmethod
    def handle_import(self, path: QualifiedName, origin: Any) -> Import | None: ...

    @abc.abstractmethod
    def handle_method(self, path: QualifiedName, method: Any) -> list[Method]: ...

    @abc.abstractmethod
    def handle_module(
        self, path: QualifiedName, module: types.ModuleType
    ) -> Module | None: ...

    @abc.abstractmethod
    def handle_module_member(
        self, path: QualifiedName, module: types.ModuleType, obj: Any
    ) -> (
        Docstring | Import | Alias | Class | list[Function] | Attribute | Module | None
    ): ...

    @abc.abstractmethod
    def handle_property(self, path: QualifiedName, prop: Any) -> Property | None: ...

    @abc.abstractmethod
    def handle_type(self, type_: type) -> QualifiedName: ...

    @abc.abstractmethod
    def handle_value(self, value: Any) -> Value: ...

    @abc.abstractmethod
    def parse_args_str(self, args_str: str) -> list[Argument]: ...

    @abc.abstractmethod
    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value: ...

    @abc.abstractmethod
    def parse_value_str(self, value: str) -> Value | InvalidExpression: ...

    @abc.abstractmethod
    def report_error(self, error: ParserError) -> None: ...

    @abc.abstractmethod
    def finalize(self): ...
