import logging

import pytest

from pybind11_stubgen.printer import Printer, _topological_sort_classes
from pybind11_stubgen.structs import (
    Alias,
    Attribute,
    Class,
    Field,
    Identifier,
    Module,
    Value,
)
from unit_support import q


def names(classes):
    return [str(c.name) for c in classes]


@pytest.mark.parametrize("count", [0, 1])
def test_empty_and_singleton(count):
    classes = [Class(Identifier("Only"))] if count else []
    assert names(_topological_sort_classes(classes)) == (["Only"] if count else [])


def test_inheritance_and_stable_ready_priority():
    classes = [
        Class(Identifier("Child"), bases=[q("Base")]),
        Class(Identifier("Peer")),
        Class(Identifier("Base")),
        Class(Identifier("Tail")),
    ]
    ordered = _topological_sort_classes(classes)
    assert names(ordered) == ["Peer", "Base", "Child", "Tail"]
    assert names(classes) == ["Child", "Peer", "Base", "Tail"]
    assert ordered[2] is classes[0]


@pytest.mark.parametrize("kind", ["base", "alias", "field"])
def test_dotted_sibling_reference(kind):
    consumer = Class(Identifier("Consumer"))
    if kind == "base":
        consumer.bases = [q("Outer.Inner")]
    elif kind == "alias":
        consumer.aliases = [Alias(Identifier("Item"), q("Outer.Inner"))]
    else:
        consumer.fields = [
            Field(Attribute(Identifier("Item"), Value("Outer.Inner", True)), "static")
        ]
    classes = [consumer, Class(Identifier("Outer"))]
    assert names(_topological_sort_classes(classes)) == ["Outer", "Consumer"]


@pytest.mark.parametrize(
    ("expression", "safe"),
    [
        ("External.Item", True),
        ("Target", False),
        ("Target()", True),
        ("'Target'", True),
        ("Self.Item", True),
    ],
)
def test_irrelevant_field_references_keep_order(expression, safe):
    consumer = Class(
        Identifier("Self"),
        fields=[
            Field(Attribute(Identifier("Item"), Value(expression, safe)), "static")
        ],
    )
    assert names(
        _topological_sort_classes([consumer, Class(Identifier("Target"))])
    ) == [
        "Self",
        "Target",
    ]


def test_external_base_and_alias_do_not_add_local_edges():
    consumer = Class(
        Identifier("Consumer"),
        bases=[q("external.Base")],
        aliases=[
            Alias(Identifier("Item"), q("external.Item")),
            Alias(Identifier("Self"), q("Consumer")),
        ],
    )
    assert names(_topological_sort_classes([consumer, Class(Identifier("Peer"))])) == [
        "Consumer",
        "Peer",
    ]


def test_repeated_edges_do_not_leave_a_false_cycle(caplog):
    consumer = Class(
        Identifier("Child"),
        bases=[q("Base")],
        aliases=[Alias(Identifier("Item"), q("Base"))],
        fields=[Field(Attribute(Identifier("Other"), Value("Base", True)), "static")],
    )
    assert names(_topological_sort_classes([consumer, Class(Identifier("Base"))])) == [
        "Base",
        "Child",
    ]
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_cycle_warns_and_appends_remaining_input_order(caplog):
    classes = [
        Class(Identifier("B"), bases=[q("A")]),
        Class(Identifier("Free")),
        Class(Identifier("A"), bases=[q("B")]),
    ]
    with caplog.at_level(logging.WARNING, logger="pybind11_stubgen"):
        assert names(_topological_sort_classes(classes)) == ["Free", "B", "A"]
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(messages) == 1
    assert "Cycle detected" in messages[0] and "['B', 'A']" in messages[0]


def test_module_and_nested_classes_use_dependency_order():
    classes = [
        Class(Identifier("Child"), bases=[q("Base")]),
        Class(Identifier("Base")),
    ]
    printer = Printer(invalid_expr_as_ellipses=True)
    assert printer.print_module(Module(Identifier("sample"), classes=classes)) == [
        "class Base:",
        "    pass",
        "class Child(Base):",
        "    pass",
    ]
    assert printer.print_class(Class(Identifier("Outer"), classes=classes)) == [
        "class Outer:",
        "    class Base:",
        "        pass",
        "    class Child(Base):",
        "        pass",
    ]
