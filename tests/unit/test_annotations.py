import logging

import pytest

from pybind11_stubgen.structs import InvalidExpression, Value
from unit_support import rt


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("int", rt("int")),
        (
            "typing.Dict[str, typing.List[int | None]]",
            rt(
                "dict",
                rt("str"),
                rt("list", rt("typing.Union", rt("int"), rt("None"))),
            ),
        ),
        ("int | str", rt("typing.Union", rt("int"), rt("str"))),
        ("typing.Optional[int]", rt("typing.Optional", rt("int"))),
        (
            "typing.Literal['x,y', 3]",
            rt("typing.Literal", Value("'x,y'", True), Value("3", True)),
        ),
        (
            "typing.Annotated[int, 'units']",
            rt("typing.Annotated", rt("int"), Value("'units'", True)),
        ),
    ],
)
def test_annotation_structure(parser, caplog, text, expected):
    assert parser.parse_annotation_str(text) == expected
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


@pytest.mark.parametrize("text", ["list[", "std::vector<int>"])
def test_invalid_annotation_reports_expression(parser, caplog, text):
    with caplog.at_level(logging.ERROR, logger="pybind11_stubgen"):
        assert parser.parse_annotation_str(text) == InvalidExpression(text)
    assert [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR] == [
        f"In unit : Invalid expression '{text}'"
    ]


def test_invalid_expression_is_not_a_valid_value(parser, caplog):
    assert parser.parse_value_str("'a,b'") == Value("'a,b'", True)
    assert parser.parse_value_str("len('abc')") == Value("len('abc')", False)
    assert parser.parse_value_str("[") == InvalidExpression("[")
    assert any("Invalid expression '['" in r.getMessage() for r in caplog.records)
