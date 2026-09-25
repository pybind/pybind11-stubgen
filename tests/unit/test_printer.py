import ast

import pytest

from pybind11_stubgen.printer import Printer
from pybind11_stubgen.structs import (
    Argument,
    Attribute,
    Class,
    Decorator,
    Docstring,
    Function,
    Identifier,
    Import,
    InvalidExpression,
    Method,
    Module,
    Property,
    Value,
)
from unit_support import q, rt


@pytest.fixture
def printer():
    return Printer(invalid_expr_as_ellipses=True)


def test_argument_separators_annotations_defaults_and_decorator(printer):
    function = Function(
        Identifier("choose"),
        args=[
            Argument(Identifier("x"), annotation=rt("int"), pos_only=True),
            Argument(
                Identifier("count"), annotation=rt("int"), default=Value("2", True)
            ),
            Argument(
                Identifier("flag"),
                annotation=rt("bool"),
                default=Value("True", True),
                kw_only=True,
            ),
        ],
        returns=rt("str"),
        decorators=[Decorator("typing.overload")],
    )
    lines = printer.print_function(function)
    assert lines == [
        "@typing.overload",
        "def choose(x: int, /, count: int = 2, *, flag: bool = True) -> str:",
        "    ...",
    ]
    ast.parse("\n".join(lines))


def test_variadic_arguments_do_not_gain_an_extra_star(printer):
    function = Function(
        Identifier("collect"),
        args=[
            Argument(Identifier("args"), variadic=True),
            Argument(Identifier("flag"), kw_only=True),
            Argument(Identifier("kwargs"), kw_variadic=True),
        ],
    )
    assert printer.print_function(function) == [
        "def collect(*args, flag, **kwargs):",
        "    ...",
    ]


@pytest.mark.parametrize(
    ("modifier", "expected"),
    [(None, []), ("static", ["@staticmethod"]), ("class", ["@classmethod"])],
)
def test_method_modifier(printer, modifier, expected):
    assert printer.print_method(Method(Function(Identifier("f")), modifier)) == [
        *expected,
        "def f():",
        "    ...",
    ]


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (rt("typing.Optional", rt("int")), "int | None"),
        (rt("typing.Union", rt("int"), rt("str")), "int | str"),
        (rt("dict", rt("str"), rt("list", rt("int"))), "dict[str, list[int]]"),
    ],
)
def test_type_rendering(printer, annotation, expected):
    assert printer.print_annotation(annotation) == expected


@pytest.mark.parametrize(("ellipses", "expected"), [(True, "..."), (False, "C++")])
def test_invalid_expression_policy(ellipses, expected):
    printer = Printer(invalid_expr_as_ellipses=ellipses)
    assert printer.print_annotation(InvalidExpression("C++")) == expected
    assert (
        printer.print_argument(
            Argument(Identifier("x"), default=InvalidExpression("C++"))
        )
        == f"x = {expected}"
    )


@pytest.mark.parametrize(
    ("comments", "expected"),
    [(False, "value: int"), (True, "value: int  # value = <opaque>")],
)
def test_unsafe_value_comments(comments, expected):
    printer = Printer(invalid_expr_as_ellipses=True, print_value_comments=comments)
    assert printer.print_attribute(
        Attribute(Identifier("value"), Value("<opaque>", False), rt("int"))
    ) == [expected]
    assert (
        printer.print_argument(
            Argument(Identifier("x"), default=Value("<opaque>", False))
        )
        == "x = ..."
    )


def test_property_getter_setter_and_input_preservation(printer):
    getter = Function(
        Identifier("get_value"),
        args=[Argument(Identifier("self"))],
        returns=rt("int"),
    )
    setter = Function(
        Identifier("set_value"),
        args=[
            Argument(Identifier("self")),
            Argument(Identifier("value"), annotation=rt("int")),
        ],
        returns=rt("None"),
    )
    prop = Property(Identifier("value"), None, getter=getter, setter=setter)
    assert printer.print_property(prop) == [
        "@property",
        "def value(self) -> int:",
        "    ...",
        "@value.setter",
        "def value(self, value: int) -> None:",
        "    ...",
    ]
    assert getter.name == "get_value" and setter.name == "set_value"


def test_docstring_escaping_round_trips(printer):
    text = 'path \\data and """quote"""'
    lines = printer.print_docstring(Docstring(text))
    assert lines == ['"""', 'path \\\\data and \\"\\"\\"quote\\"\\"\\"', '"""']
    assert (
        ast.get_docstring(ast.parse("\n".join(lines)), clean=False)
        == "\n" + text + "\n"
    )


def test_module_imports_all_classes_functions_and_attributes(printer):
    module = Module(
        Identifier("sample"),
        imports={
            Import(None, q("typing")),
            Import(Identifier("annotations"), q("__future__.annotations")),
            Import(Identifier("P"), q("pathlib.Path")),
        },
        classes=[Class(Identifier("Thing"))],
        functions=[Function(Identifier("z")), Function(Identifier("a"))],
        attributes=[
            Attribute(Identifier("value"), Value("3", True), rt("int")),
            Attribute(Identifier("__all__"), Value("['Thing', 'a', 'z']", True)),
        ],
    )
    lines = printer.print_module(module)
    assert lines == [
        "from __future__ import annotations",
        "from pathlib import Path as P",
        "import typing",
        "__all__ = ['Thing', 'a', 'z']",
        "class Thing:",
        "    pass",
        "def a():",
        "    ...",
        "def z():",
        "    ...",
        "value: int = 3",
    ]
    ast.parse("\n".join(lines))
