from __future__ import annotations

import types
import typing
from typing import Any

from pybind11_stubgen.parser.errors import InvalidIdentifierError
from pybind11_stubgen.parser.interface import IParser
from pybind11_stubgen.structs import (
    Alias,
    Attribute,
    Class,
    Docstring,
    Field,
    Function,
    Identifier,
    Import,
    Method,
    Module,
    Property,
    QualifiedName,
)


class FilterTypingModuleAttributes(IParser):
    __sentinel = object()

    def handle_attribute(self, path: QualifiedName, attr: Any) -> Attribute | None:
        if getattr(typing, str(path[-1]), self.__sentinel) is attr:
            return None
        return super().handle_attribute(path, attr)


class FilterClassMembers(IParser):
    __attribute_blacklist: set[Identifier] = {
        *map(
            Identifier,
            (
                "__annotations__",
                "__builtins__",
                "__cached__",
                "__file__",
                "__firstlineno__",
                "__loader__",
                "__name__",
                "__package__",
                "__path__",
                "__spec__",
                "__static_attributes__",
            ),
        )
    }
    __class_member_blacklist: set[Identifier] = {
        *map(
            Identifier,
            (
                "__annotations__",
                "__class__",
                "__dict__",
                "__module__",
                "__qualname__",
                "__weakref__",
            ),
        )
    }

    __method_blacklist: set[Identifier] = {*map(Identifier, ("__dir__", "__sizeof__"))}

    def handle_class_member(
        self, path: QualifiedName, class_: type, member: Any
    ) -> Docstring | Alias | Class | list[Method] | Field | Property | None:
        name = path[-1]
        if name in self.__class_member_blacklist:
            return None
        if not hasattr(class_, "__dict__") or name not in class_.__dict__:
            # Skip members inherited from base classes
            return None
        return super().handle_class_member(path, class_, member)

    def handle_method(self, path: QualifiedName, value: Any) -> list[Method]:
        if path[-1] in self.__method_blacklist:
            return []
        return super().handle_method(path, value)

    def handle_attribute(self, path: QualifiedName, attr: Any) -> Attribute | None:
        if path[-1] in self.__attribute_blacklist:
            return None
        return super().handle_attribute(path, attr)


class FilterPybindInternals(IParser):
    __attribute_blacklist: set[Identifier] = {*map(Identifier, ("__entries",))}

    __class_blacklist: set[Identifier] = {*map(Identifier, ("pybind11_type",))}

    def handle_attribute(self, path: QualifiedName, value: Any) -> Attribute | None:
        if path[-1] in self.__attribute_blacklist:
            return None
        return super().handle_attribute(path, value)

    def handle_class_member(
        self, path: QualifiedName, class_: type, member: Any
    ) -> Docstring | Alias | Class | list[Method] | Field | Property | None:
        name = path[-1]
        if name in self.__class_blacklist:
            return None
        if name.startswith("__pybind11_module"):
            return None
        if name.startswith("_pybind11_conduit_v1_"):
            return None
        return super().handle_class_member(path, class_, member)


class FilterInvalidIdentifiers(IParser):
    def handle_module_member(
        self, path: QualifiedName, module: types.ModuleType, obj: Any
    ) -> (
        Docstring | Import | Alias | Class | list[Function] | Attribute | Module | None
    ):
        if not path[-1].isidentifier():
            self.report_error(InvalidIdentifierError(path[-1], path.parent))
            return None
        return super().handle_module_member(path, module, obj)

    def handle_class_member(
        self, path: QualifiedName, class_: type, obj: Any
    ) -> Docstring | Alias | Class | list[Method] | Field | Property | None:
        if not path[-1].isidentifier():
            self.report_error(InvalidIdentifierError(path[-1], path.parent))
            return None
        return super().handle_class_member(path, class_, obj)


class FilterPybind11ViewClasses(IParser):
    def handle_module_member(
        self, path: QualifiedName, module: types.ModuleType, obj: Any
    ) -> (
        Docstring | Import | Alias | Class | list[Function] | Attribute | Module | None
    ):
        result = super().handle_module_member(path, module, obj)

        if isinstance(result, Class) and str(result.name) in [
            "ItemsView",
            "KeysView",
            "ValuesView",
        ]:
            # TODO: check obj is a subclass of pybind11_object
            return None

        return result


class FilterPybind11NativeEnumMembers(IParser):
    @staticmethod
    def _is_sunder(name: str) -> bool:
        """Match CPython Enum's reserved ``_sunder_`` names.

        Keep this in sync with CPython's ``enum._is_sunder``:
        https://github.com/python/cpython/blob/3.14/Lib/enum.py#L57-L66

        These names are rejected by ``EnumDict.__setitem__`` unless explicitly
        allowlisted by ``enum`` itself:
        https://github.com/python/cpython/blob/3.14/Lib/enum.py#L342-L367
        """
        return (
            len(name) > 2
            and name[0] == name[-1] == "_"
            and name[1] != "_"
            and name[-2] != "_"
        )

    def handle_class_member(
        self, path: QualifiedName, class_: type, obj: Any
    ) -> Docstring | Alias | Class | list[Method] | Field | Property | None:
        name = str(path[-1])
        # py::native_enum exposes Enum internals via __dict__, but emitting them
        # into a stub that later gets executed as Python can fail at import time.
        if hasattr(class_, "__pybind11_native_enum__") and (
            name == "__pybind11_native_enum__" or self._is_sunder(name)
        ):
            return None
        return super().handle_class_member(path, class_, obj)
