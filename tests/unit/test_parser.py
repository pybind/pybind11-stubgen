import logging
import sys

from pybind11_stubgen.structs import (
    Argument,
    Decorator,
    Docstring,
    Function,
    Identifier,
    Value,
)
from unit_support import q, rt


def test_python_signature(parser, caplog):
    def sample(value: int = 2, *args: str, enabled: bool = True, **kwargs: int) -> str:
        """Convert."""
        return str(value)

    assert parser.handle_function(q("unit.sample"), sample) == [
        Function(
            Identifier("sample"),
            args=[
                Argument(
                    Identifier("value"), annotation=rt("int"), default=Value("2", True)
                ),
                Argument(Identifier("args"), annotation=rt("str"), variadic=True),
                Argument(
                    Identifier("enabled"),
                    annotation=rt("bool"),
                    default=Value("True", True),
                    kw_only=True,
                ),
                Argument(Identifier("kwargs"), annotation=rt("int"), kw_variadic=True),
            ],
            returns=rt("str"),
            doc=Docstring("Convert."),
        )
    ]
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_docstring_argument_kinds(parser):
    args = parser.parse_args_str("x: int, /, count: int = 2, *, enabled: bool = True")
    assert args == [
        Argument(Identifier("x"), pos_only=True, annotation=rt("int")),
        Argument(Identifier("count"), annotation=rt("int"), default=Value("2", True)),
        Argument(
            Identifier("enabled"),
            kw_only=True,
            annotation=rt("bool"),
            default=Value("True", True),
        ),
    ]
    assert parser.parse_args_str("*args: int, **kwargs: str") == [
        Argument(Identifier("args"), variadic=True, annotation=rt("int")),
        Argument(Identifier("kwargs"), kw_variadic=True, annotation=rt("str")),
    ]


def test_docstring_overloads_reach_handle_function(parser):
    def choose(*args, **kwargs):
        pass

    choose.__doc__ = "\n".join(
        [
            "choose(*args, **kwargs)",
            "Overloaded function.",
            "",
            "1. choose(x: int) -> str",
            "",
            "Integer.",
            "",
            "2. choose(x: str) -> int",
            "",
            "Text.",
        ]
    )
    assert parser.handle_function(q("unit.choose"), choose) == [
        Function(
            Identifier("choose"),
            args=[Argument(Identifier("x"), annotation=rt("int"))],
            returns=rt("str"),
            doc=Docstring("Integer."),
            decorators=[Decorator("typing.overload")],
        ),
        Function(
            Identifier("choose"),
            args=[Argument(Identifier("x"), annotation=rt("str"))],
            returns=rt("int"),
            doc=Docstring("Text."),
            decorators=[Decorator("typing.overload")],
        ),
    ]


def test_non_signature_preserves_generic_fallback(parser):
    def unknown(*args, **kwargs):
        """Not a signature."""

    assert parser.parse_function_docstring(Identifier("unknown"), []) == []
    assert parser.parse_function_docstring(Identifier("unknown"), ["unknown("]) == []
    assert parser.handle_function(q("unit.unknown"), unknown) == [
        Function(
            Identifier("unknown"),
            args=[
                Argument(Identifier("args"), variadic=True),
                Argument(Identifier("kwargs"), kw_variadic=True),
            ],
            doc=Docstring("Not a signature."),
        )
    ]


def test_generic_docstring_version_boundary(parser):
    actual = parser.parse_function_docstring(
        Identifier("identity"), ["identity[T](value: T) -> T"]
    )
    if sys.version_info < (3, 12):
        assert actual == []  # The production parser rejects PEP 695 syntax here.
    else:
        assert actual == [
            Function(
                Identifier("identity"),
                args=[Argument(Identifier("value"), annotation=rt("T"))],
                returns=rt("T"),
                type_vars=["T"],
            )
        ]


def test_module_definition_order(parser, load_python_fixture):
    module = load_python_fixture("stubgen_test_python")
    parsed = parser.handle_module(q(module.__name__), module)
    assert parsed is not None
    assert [str(c.name) for c in parsed.classes] == ["ZBase", "ADerived"]
    assert parsed.classes[1].bases == [q("ZBase")]
    assert [str(f.name) for f in parsed.functions] == ["typed"]


def test_class_members_use_definition_order_and_resolve_descriptors(parser):
    class Parent:
        inherited = 1

    class Child(Parent):
        zed = 2
        alpha = 3

        @staticmethod
        def answer():
            return 42

    members = list(parser._iter_class_members(Child))
    names = [name for name, _ in members]
    assert names.index("zed") < names.index("alpha") < names.index("inherited")
    assert names.count("inherited") == 1
    assert dict(members)["answer"] is Child.answer
