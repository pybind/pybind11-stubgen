from __future__ import annotations

from pybind11_stubgen.structs import Identifier, QualifiedName


class ParserError(Exception):
    pass


class InvalidIdentifierError(ParserError):
    def __init__(self, name: Identifier, found_at: QualifiedName):
        super().__init__()
        self.name = name
        self.at = found_at

    def __str__(self):
        return f"Invalid identifier '{self.name}' at '{self.at}'"


class InvalidExpressionError(ParserError):
    def __init__(self, expression: str):
        super().__init__()
        self.expression: str = expression

    def __str__(self):
        return f"Invalid expression '{self.expression}'"


class NameResolutionError(ParserError):
    def __init__(self, name: QualifiedName):
        super().__init__()
        self.name = name

    def __str__(self):
        return f"Can't find/import '{self.name}'"


class InspectError(ParserError):
    def __init__(self, path: QualifiedName, class_: type, msg: str):
        super().__init__()
        self.path = path
        self.class_ = class_
        self.msg = msg

    def __str__(self):
        return f"Can't get members of type {self.class_} at {self.path}: {self.msg}"
