# Compiler-Free Production Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add focused compiler-free tests of existing generator contracts, with independent Python fixtures and installed-wheel verification on Python 3.10–3.13.

**Architecture:** Separate parser, annotation, class-ordering, printer, and writer tests under `tests/unit/`, plus small real-component pipeline checks. Use explicit expected models/text, standard-library fixtures, and existing pytest facilities rather than a second snapshot harness. Add explicit unit tox environments and a separate wheel-based CI matrix without changing the native matrix.

**Tech Stack:** Python 3.10–3.13, pytest>=8,<9, uv, tox with tox-uv, existing production dataclasses/parser/printer/writer, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-25-test-harness-phase-two-design.md` (approved).

## Global Constraints

- Phase two is test-only: production behavior is preserved.
- Preserve all files under `pybind11_stubgen/`; no testability refactors or runtime fixes.
- All reference contents and aliases under `tests/stubs/` and `tests/errors/` remain unchanged.
- Preserve native source/build configuration, `tests/install-demo-module.sh`, and the entire existing mixed Python/native demo package.
- Preserve existing snapshot comparison, update, normalization, and diagnostic behavior.
- Preserve the 13 native tox configurations, their default environment list, and native CI configurations. Keep their native execution serial locally.
- Preserve existing gemmi CLI jobs and publication trigger/credentials.
- Do not add a snapshot framework, coverage-percentage target, production dependency, broad dependency upgrade, or third-party fixture dependency.
- No push, pull request, remote workflow execution, or publication is part of this work.
- Do not change distribution package discovery: the existing installed distribution already contains test files.
- Report unexpected production bugs separately. No production fix, snapshot update, unexplained skip/xfail, or weaker expectation may make a task green.

## Workspace, verification protocol, and file map

Work in the existing `.worktrees/test-harness-phase-one` worktree on branch
`test-harness-phase-one`. Runtime/configuration baseline is `a306491`; the
approved spec was introduced in `640bccc`. Detect existing isolation with the
worktree skill rather than creating another worktree. Preserve unrelated work.
Read both the approved spec and this plan before implementing any task.

Read `superpowers:test-driven-development` and its `writing-good-tests.md`
reference. This is coverage of existing production, not permission to rewrite
it: add tests first, observe missing test-support failures where relevant, and
prove assertion sensitivity with the process-local negative controls below.
They deliberately break a real behavior in an isolated disposable process,
then run selected new tests and require pytest exit code 1 with the expected
assertion failure. Exit 2/3/4/5 is not valid red evidence. Run the unpatched tests
again afterward. Never edit/stage production to manufacture a red cycle.

For every test, state the realistic regression it detects in the task report.
Expected values must be literals or explicit dataclass construction, never
output recomputed by the production method under test. A support constructor
that only builds a dataclass is acceptable; a duplicate parser/sorter is not.
The examples below are complete starting test bodies; formatting may be
adjusted by existing hooks. Unexpected behavioral differences require diagnosis,
not copying observed output into the expectation.

All source-test and negative-control commands below run from the worktree root.
Unset inherited `VIRTUAL_ENV` to avoid accidentally using the root checkout's
development environment. Use these commands for focused development:

```sh
env -u VIRTUAL_ENV uv run --no-project --python 3.10 --with 'pytest>=8,<9' python -m pytest tests/unit -q
env -u VIRTUAL_ENV uv run --no-project --python 3.13 --with 'pytest>=8,<9' python -m pytest tests/unit tests/test_snapshot_helpers.py -q
```

Implementation-time correction (Task 7): Task 6 found that `--no-project`
can still reuse the worktree's `.venv` even with `VIRTUAL_ENV` unset. Add
`--isolated` to uv-managed source verification commands going forward; the
commands above and earlier task evidence are retained as historical context.
Fresh explicit source/wheel venvs and tox commands are unchanged.

Before new files exist, run only `tests/test_snapshot_helpers.py` with both
commands. The last recorded baseline was 97 passing tests on each interpreter;
record fresh results rather than relying on that history.

Each task ends with focused tests on 3.10 and 3.13, the cumulative fast suite,
`git diff --check`, hooks on changed files, a scoped commit, and review. Keep
commands/results, negative-control evidence and bug reports in ignored
`.superpowers/sdd/2026-09-25-test-harness-phase-two/`. Verify that directory is
ignored before writing reports. No new general-purpose report runner is shipped.

### Files and responsibilities

| Task | Files | Responsibility |
| --- | --- | --- |
| 1 | `tests/unit/conftest.py`, `tests/unit/unit_support.py`, `tests/unit/fixtures/stubgen_test_python.py`, `tests/unit/test_parser.py` | Fresh real parser, isolated fixture imports, installed-origin guard, signatures and traversal |
| 2 | `tests/unit/test_annotations.py` | Structured annotation normalization and invalid-input diagnostics |
| 3 | `tests/unit/test_class_ordering.py` | Stable dependency ordering, warnings, nested printer integration |
| 4 | `tests/unit/test_printer.py` | Exact rendering and options from explicit models |
| 5 | `tests/unit/test_writer.py` | Output paths, bytes and write failures with the real printer |
| 6 | `tests/unit/fixtures/stubgen_test_package/__init__.py`, `tests/unit/fixtures/stubgen_test_package/leaf.py`, `tests/unit/test_pipeline.py` | Small independently importable package and end-to-end file assertions |
| 7 | `tox.ini`, `.github/workflows/ci.yml`, `tests/README.md` | Compiler-free installed runs, CI wiring, documentation and full acceptance |

Do not add `__init__.py` to `tests/`, `tests/unit/`, or `tests/unit/fixtures/`.
Pytest's ordinary prepend import mode then adds test/support directories rather
than the repository root. Only the actual package fixture has `__init__.py`.
Installed-origin verification in the pytest process catches any shadowing.

Task 1 owns shared helpers and their names. Tasks 2–6 consume them but do not
independently redesign them. Run tasks sequentially with fresh implementer and
reviewer contexts; native acceptance must remain serial.

## Task 1: Real parser tests and isolated test support

**Files:** Create `tests/unit/test_parser.py`, `tests/unit/conftest.py`,
`tests/unit/unit_support.py`, and `tests/unit/fixtures/stubgen_test_python.py`.
Read `pybind11_stubgen/__init__.py:stub_parser_from_args`,
`parser/mixins/parse.py:BaseParser, ExtractSignaturesFromPybind11Docstrings,
ParserDispatchMixin`, and `parser/mixins/error_handlers.py:LocalErrors`.

**Interfaces:**
- `q(name: str) -> QualifiedName` and `rt(name: str, *parameters: Annotation) -> ResolvedType` in `unit_support` construct expected models only.
- `make_parser(*options: str) -> IParser` uses the real CLI factory, never a copied mixin stack.
- Pytest fixture `parser` yields a fresh composed parser inside a `LocalErrors` scope named `unit`; tests that exercise finalization call it explicitly.
- Fixture `load_python_fixture` yields a callable `(name: str) -> ModuleType` using normal imports from the independent fixture directory; all fixture module entries/import paths are restored after each test.
- `STUBGEN_TEST_INSTALLED=1` enables same-pytest-process installed-origin enforcement; unset means the documented source mode.

- [ ] **Step 1: Write the parser tests first.** Create `test_parser.py` with:

```python
import logging
import sys

from pybind11_stubgen.structs import Argument, Decorator, Docstring, Function, Identifier, Value
from unit_support import q, rt


def test_python_signature(parser, caplog):
    def sample(value: int = 2, *args: str, enabled: bool = True, **kwargs: int) -> str:
        """Convert."""
        return str(value)

    assert parser.handle_function(q("unit.sample"), sample) == [
        Function(
            Identifier("sample"),
            args=[
                Argument(Identifier("value"), annotation=rt("int"), default=Value("2", True)),
                Argument(Identifier("args"), annotation=rt("str"), variadic=True),
                Argument(Identifier("enabled"), annotation=rt("bool"), default=Value("True", True), kw_only=True),
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
        Argument(Identifier("enabled"), kw_only=True, annotation=rt("bool"), default=Value("True", True)),
    ]
    assert parser.parse_args_str("*args: int, **kwargs: str") == [
        Argument(Identifier("args"), variadic=True, annotation=rt("int")),
        Argument(Identifier("kwargs"), kw_variadic=True, annotation=rt("str")),
    ]


def test_docstring_overloads_reach_handle_function(parser):
    def choose(*args, **kwargs):
        pass

    choose.__doc__ = "\n".join([
        "choose(*args, **kwargs)", "Overloaded function.", "",
        "1. choose(x: int) -> str", "", "Integer.", "",
        "2. choose(x: str) -> int", "", "Text.",
    ])
    assert parser.handle_function(q("unit.choose"), choose) == [
        Function(Identifier("choose"), args=[Argument(Identifier("x"), annotation=rt("int"))], returns=rt("str"), doc=Docstring("Integer."), decorators=[Decorator("typing.overload")]),
        Function(Identifier("choose"), args=[Argument(Identifier("x"), annotation=rt("str"))], returns=rt("int"), doc=Docstring("Text."), decorators=[Decorator("typing.overload")]),
    ]


def test_non_signature_preserves_generic_fallback(parser):
    def unknown(*args, **kwargs):
        """Not a signature."""

    assert parser.parse_function_docstring(Identifier("unknown"), []) == []
    assert parser.parse_function_docstring(Identifier("unknown"), ["unknown("]) == []
    assert parser.handle_function(q("unit.unknown"), unknown) == [
        Function(Identifier("unknown"), args=[Argument(Identifier("args"), variadic=True), Argument(Identifier("kwargs"), kw_variadic=True)], doc=Docstring("Not a signature."))
    ]


def test_generic_docstring_version_boundary(parser):
    actual = parser.parse_function_docstring(Identifier("identity"), ["identity[T](value: T) -> T"])
    if sys.version_info < (3, 12):
        assert actual == []  # The production parser rejects PEP 695 syntax here.
    else:
        assert actual == [Function(Identifier("identity"), args=[Argument(Identifier("value"), annotation=rt("T"))], returns=rt("T"), type_vars=["T"])]


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
```

- [ ] **Step 2: Run `test_parser.py` before support exists.** Use the focused
  Python 3.10 command. Expect a missing `unit_support` collection error. Record
  this as setup-red only, not as evidence of a production regression.

- [ ] **Step 3: Add the minimal shared support.** `unit_support.py`:

```python
from pybind11_stubgen import CLIArgs, arg_parser, stub_parser_from_args
from pybind11_stubgen.parser.interface import IParser
from pybind11_stubgen.structs import Annotation, QualifiedName, ResolvedType


def q(name: str) -> QualifiedName:
    return QualifiedName.from_str(name)


def rt(name: str, *parameters: Annotation) -> ResolvedType:
    return ResolvedType(q(name), list(parameters) if parameters else None)


def make_parser(*options: str) -> IParser:
    args = arg_parser().parse_args([*options, "stubgen_test_python"], namespace=CLIArgs())
    return stub_parser_from_args(args)
```

`conftest.py`:

```python
import importlib
import os
import sys
from pathlib import Path

import pytest

from pybind11_stubgen.parser.mixins.error_handlers import LocalErrors
from unit_support import make_parser, q


@pytest.fixture(scope="session", autouse=True)
def enforce_installed_origin():
    if os.environ.get("STUBGEN_TEST_INSTALLED") != "1":
        return
    prefix = Path(sys.prefix).resolve()
    for name, module in list(sys.modules.items()):
        if name == "pybind11_stubgen" or name.startswith("pybind11_stubgen."):
            origin = getattr(module, "__file__", None)
            assert origin is not None, (name, origin)
            path = Path(origin).resolve()
            assert path.is_relative_to(prefix), (name, path, prefix)


@pytest.fixture
def parser():
    result = make_parser()
    with LocalErrors(q("unit"), set(), result.stack):
        yield result
    assert result.stack == []


@pytest.fixture
def load_python_fixture(monkeypatch):
    def is_fixture(name):
        return name.startswith("stubgen_test_")

    saved = {name: module for name, module in sys.modules.items() if is_fixture(name)}
    with monkeypatch.context() as scoped:
        scoped.syspath_prepend(str(Path(__file__).parent / "fixtures"))
        for name in saved:
            sys.modules.pop(name)
        try:
            yield importlib.import_module
        finally:
            for name in list(sys.modules):
                if is_fixture(name):
                    sys.modules.pop(name)
            sys.modules.update(saved)
            importlib.invalidate_caches()
```

`fixtures/stubgen_test_python.py`:

```python
__all__ = ["ADerived", "ZBase", "typed"]


class ZBase:
    pass


class ADerived(ZBase):
    pass


def typed(value: int, *, enabled: bool = True) -> str:
    """Convert."""
    return str(value)
```

- [ ] **Step 4: Run the focused tests on 3.10 and 3.13.** Require a green run
  against unchanged production. Do not add a `from __future__ import annotations`
  to the ordinary fixture merely for style: it intentionally covers real runtime
  type annotations. The generic docstring stays a string for floor compatibility.

- [ ] **Step 5: Prove parser assertion sensitivity without writing production.**

```sh
env -u VIRTUAL_ENV uv run --no-project --python 3.10 --with 'pytest>=8,<9' python - <<'PY'
from unittest.mock import patch
import pytest
from pybind11_stubgen.parser.mixins.parse import BaseParser
with patch.object(BaseParser, 'handle_function', return_value=[]):
    code = pytest.main(['tests/unit/test_parser.py::test_python_signature', '-q'])
assert code == pytest.ExitCode.TESTS_FAILED, code
PY
```

  Confirm an expected function/model comparison failure, then rerun the original
  test normally. Also exercise the installed guard's red path:

```sh
STUBGEN_TEST_INSTALLED=1 env -u VIRTUAL_ENV uv run --no-project --python 3.10 --with 'pytest>=8,<9' python -m pytest tests/unit/test_parser.py::test_python_signature -q
```

  Expect exit 1 with the source origin rejected by `enforce_installed_origin`.
  Rerun without `STUBGEN_TEST_INSTALLED` to restore the green source case. A
  genuine installed green path is verified in Task 7.

- [ ] **Step 6: Review isolation, run cumulative checks, and commit.** Check no
  native fixture imports or new dependencies. Commit only these four files as
  `test: cover parser contracts with independent Python fixtures`.

**Known boundary to investigate separately:** `BaseParser.handle_function` uses
`inspect.getfullargspec`, which does not distinguish positional-only names in
its `args` list. Do not assert that a real Python `/` signature is reconstructed
correctly without checking it. The planned positional-only contract is the
existing docstring route. Record any confirmed loss on the ordinary Python
route as a separate bug rather than codifying loss as a desired assertion.

## Task 2: Structured annotations and expected diagnostics

**Files:** Create `tests/unit/test_annotations.py`.
Read `parse.py:parse_annotation_str, parse_type_str, _parse_expression_str` and
`fix.py:FixPEP585CollectionNames, FixMissingImports`.

**Interfaces:** Consume Task 1's `parser`, `q`, and `rt`; produce no shared helper.
Direct parsing uses the fixture's real logger context so invalid-input tests
can assert diagnostics without suppressing them or hitting an empty logger stack.

- [ ] **Step 1: Add exact annotation and malformed-input cases.**

```python
import logging

import pytest

from pybind11_stubgen.structs import InvalidExpression, Value
from unit_support import rt


@pytest.mark.parametrize(("text", "expected"), [
    ("int", rt("int")),
    ("typing.Dict[str, typing.List[int | None]]", rt("dict", rt("str"), rt("list", rt("typing.Union", rt("int"), rt("None"))))),
    ("int | str", rt("typing.Union", rt("int"), rt("str"))),
    ("typing.Optional[int]", rt("typing.Optional", rt("int"))),
    ("typing.Literal['x,y', 3]", rt("typing.Literal", Value("'x,y'", True), Value("3", True))),
    ("typing.Annotated[int, 'units']", rt("typing.Annotated", rt("int"), Value("'units'", True))),
])
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
```

- [ ] **Step 2: Run on Python 3.10 and 3.13.** If a case reports an unexpected
  name-resolution error, inspect the actual parser/import context first; do not
  add ignore-all-errors or optional packages.

- [ ] **Step 3: Prove invalid-input assertions detect a lost error result.**

```sh
env -u VIRTUAL_ENV uv run --no-project --python 3.10 --with 'pytest>=8,<9' python - <<'PY'
from unittest.mock import patch
import pytest
from pybind11_stubgen.parser.mixins.parse import BaseParser
from pybind11_stubgen.structs import Value
with patch.object(BaseParser, '_parse_expression_str', return_value=Value('wrong', True)):
    code = pytest.main(['tests/unit/test_annotations.py::test_invalid_annotation_reports_expression', '-q'])
assert code == pytest.ExitCode.TESTS_FAILED, code
PY
```

- [ ] **Step 4: Rerun unpatched, cumulative tests and hooks; commit** as
  `test: cover annotation structure and invalid expressions`.

## Task 3: Stable dependency ordering and printer integration

**Files:** Create `tests/unit/test_class_ordering.py`.
Read `printer.py:_topological_sort_classes, _referenced_local_dependency_name,
Printer.print_class_body, Printer.print_module`.

**Interfaces:** Consume `q`; use `_topological_sort_classes` for focused graph
contracts and `Printer` for consumer-visible ordering. Produce no shared helper.

- [ ] **Step 1: Add graph contracts with literal expected orders.**

```python
import logging

import pytest

from pybind11_stubgen.printer import Printer, _topological_sort_classes
from pybind11_stubgen.structs import Alias, Attribute, Class, Field, Identifier, Module, Value
from unit_support import q


def names(classes):
    return [str(c.name) for c in classes]


@pytest.mark.parametrize("count", [0, 1])
def test_empty_and_singleton(count):
    classes = [Class(Identifier("Only"))] if count else []
    assert names(_topological_sort_classes(classes)) == (["Only"] if count else [])


def test_inheritance_and_stable_ready_priority():
    classes = [Class(Identifier("Child"), bases=[q("Base")]), Class(Identifier("Peer")), Class(Identifier("Base")), Class(Identifier("Tail"))]
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
        consumer.fields = [Field(Attribute(Identifier("Item"), Value("Outer.Inner", True)), "static")]
    classes = [consumer, Class(Identifier("Outer"))]
    assert names(_topological_sort_classes(classes)) == ["Outer", "Consumer"]


@pytest.mark.parametrize(("expression", "safe"), [("External.Item", True), ("Target", False), ("Target()", True), ("'Target'", True), ("Self.Item", True)])
def test_irrelevant_field_references_keep_order(expression, safe):
    consumer = Class(Identifier("Self"), fields=[Field(Attribute(Identifier("Item"), Value(expression, safe)), "static")])
    assert names(_topological_sort_classes([consumer, Class(Identifier("Target"))])) == ["Self", "Target"]


def test_external_base_and_alias_do_not_add_local_edges():
    consumer = Class(Identifier("Consumer"), bases=[q("external.Base")], aliases=[Alias(Identifier("Item"), q("external.Item")), Alias(Identifier("Self"), q("Consumer"))])
    assert names(_topological_sort_classes([consumer, Class(Identifier("Peer"))])) == ["Consumer", "Peer"]


def test_repeated_edges_do_not_leave_a_false_cycle(caplog):
    consumer = Class(Identifier("Child"), bases=[q("Base")], aliases=[Alias(Identifier("Item"), q("Base"))], fields=[Field(Attribute(Identifier("Other"), Value("Base", True)), "static")])
    assert names(_topological_sort_classes([consumer, Class(Identifier("Base"))])) == ["Base", "Child"]
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_cycle_warns_and_appends_remaining_input_order(caplog):
    classes = [Class(Identifier("B"), bases=[q("A")]), Class(Identifier("Free")), Class(Identifier("A"), bases=[q("B")])]
    with caplog.at_level(logging.WARNING, logger="pybind11_stubgen"):
        assert names(_topological_sort_classes(classes)) == ["Free", "B", "A"]
    messages = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert len(messages) == 1
    assert "Cycle detected" in messages[0] and "['B', 'A']" in messages[0]


def test_module_and_nested_classes_use_dependency_order():
    classes = [Class(Identifier("Child"), bases=[q("Base")]), Class(Identifier("Base"))]
    printer = Printer(invalid_expr_as_ellipses=True)
    assert printer.print_module(Module(Identifier("sample"), classes=classes)) == ["class Base:", "    pass", "class Child(Base):", "    pass"]
    assert printer.print_class(Class(Identifier("Outer"), classes=classes)) == ["class Outer:", "    class Base:", "        pass", "    class Child(Base):", "        pass"]
```

- [ ] **Step 2: Run focused tests on 3.10 and 3.13.** The expected stable order
  is hand-derived: after Base is emitted, the newly ready Child has earlier
  original input priority than Tail. Do not sort expected names alphabetically.

- [ ] **Step 3: Check the consumer catches bypassed sorting.**

```sh
env -u VIRTUAL_ENV uv run --no-project --python 3.10 --with 'pytest>=8,<9' python - <<'PY'
from unittest.mock import patch
import pytest
from pybind11_stubgen.printer import Printer
with patch.object(Printer, '_order_classes', lambda self, classes: classes):
    code = pytest.main(['tests/unit/test_class_ordering.py::test_module_and_nested_classes_use_dependency_order', '-q'])
assert code == pytest.ExitCode.TESTS_FAILED, code
PY
```

- [ ] **Step 4: Rerun unpatched, cumulative tests and hooks; commit** as
  `test: cover stable class dependencies and cycle fallback`.

## Task 4: Exact printer rendering from explicit models

**Files:** Create `tests/unit/test_printer.py`.
Read all rendering methods in `pybind11_stubgen/printer.py` and the relevant
model fields in `pybind11_stubgen/structs.py`.

**Interfaces:** Consume `q` and `rt`; construct `Printer` explicitly per test.
No production parser is used to construct the expected printer inputs.

- [ ] **Step 1: Add the following renderer tests.**

```python
import ast

import pytest

from pybind11_stubgen.printer import Printer
from pybind11_stubgen.structs import Argument, Attribute, Class, Decorator, Docstring, Function, Identifier, Import, InvalidExpression, Method, Module, Property, Value
from unit_support import q, rt


@pytest.fixture
def printer():
    return Printer(invalid_expr_as_ellipses=True)


def test_argument_separators_annotations_defaults_and_decorator(printer):
    function = Function(Identifier("choose"), args=[
        Argument(Identifier("x"), annotation=rt("int"), pos_only=True),
        Argument(Identifier("count"), annotation=rt("int"), default=Value("2", True)),
        Argument(Identifier("flag"), annotation=rt("bool"), default=Value("True", True), kw_only=True),
    ], returns=rt("str"), decorators=[Decorator("typing.overload")])
    lines = printer.print_function(function)
    assert lines == ["@typing.overload", "def choose(x: int, /, count: int = 2, *, flag: bool = True) -> str:", "    ..."]
    ast.parse("\n".join(lines))


def test_variadic_arguments_do_not_gain_an_extra_star(printer):
    function = Function(Identifier("collect"), args=[Argument(Identifier("args"), variadic=True), Argument(Identifier("flag"), kw_only=True), Argument(Identifier("kwargs"), kw_variadic=True)])
    assert printer.print_function(function) == ["def collect(*args, flag, **kwargs):", "    ..."]


@pytest.mark.parametrize(("modifier", "expected"), [(None, []), ("static", ["@staticmethod"]), ("class", ["@classmethod"])])
def test_method_modifier(printer, modifier, expected):
    assert printer.print_method(Method(Function(Identifier("f")), modifier)) == [*expected, "def f():", "    ..."]


@pytest.mark.parametrize(("annotation", "expected"), [
    (rt("typing.Optional", rt("int")), "int | None"),
    (rt("typing.Union", rt("int"), rt("str")), "int | str"),
    (rt("dict", rt("str"), rt("list", rt("int"))), "dict[str, list[int]]"),
])
def test_type_rendering(printer, annotation, expected):
    assert printer.print_annotation(annotation) == expected


@pytest.mark.parametrize(("ellipses", "expected"), [(True, "..."), (False, "C++")])
def test_invalid_expression_policy(ellipses, expected):
    printer = Printer(invalid_expr_as_ellipses=ellipses)
    assert printer.print_annotation(InvalidExpression("C++")) == expected
    assert printer.print_argument(Argument(Identifier("x"), default=InvalidExpression("C++"))) == f"x = {expected}"


@pytest.mark.parametrize(("comments", "expected"), [(False, "value: int"), (True, "value: int  # value = <opaque>")])
def test_unsafe_value_comments(comments, expected):
    printer = Printer(invalid_expr_as_ellipses=True, print_value_comments=comments)
    assert printer.print_attribute(Attribute(Identifier("value"), Value("<opaque>", False), rt("int"))) == [expected]
    assert printer.print_argument(Argument(Identifier("x"), default=Value("<opaque>", False))) == "x = ..."


def test_property_getter_setter_and_input_preservation(printer):
    getter = Function(Identifier("get_value"), args=[Argument(Identifier("self"))], returns=rt("int"))
    setter = Function(Identifier("set_value"), args=[Argument(Identifier("self")), Argument(Identifier("value"), annotation=rt("int"))], returns=rt("None"))
    prop = Property(Identifier("value"), None, getter=getter, setter=setter)
    assert printer.print_property(prop) == ["@property", "def value(self) -> int:", "    ...", "@value.setter", "def value(self, value: int) -> None:", "    ..."]
    assert getter.name == "get_value" and setter.name == "set_value"


def test_docstring_escaping_round_trips(printer):
    text = 'path \\data and """quote"""'
    lines = printer.print_docstring(Docstring(text))
    assert lines == ['"""', 'path \\\\data and \\"\\"\\"quote\\"\\"\\"', '"""']
    assert ast.get_docstring(ast.parse("\n".join(lines)), clean=False) == "\n" + text + "\n"


def test_module_imports_all_classes_functions_and_attributes(printer):
    module = Module(Identifier("sample"), imports={Import(None, q("typing")), Import(Identifier("annotations"), q("__future__.annotations")), Import(Identifier("P"), q("pathlib.Path"))}, classes=[Class(Identifier("Thing"))], functions=[Function(Identifier("z")), Function(Identifier("a"))], attributes=[Attribute(Identifier("value"), Value("3", True), rt("int")), Attribute(Identifier("__all__"), Value("['Thing', 'a', 'z']", True))])
    lines = printer.print_module(module)
    assert lines == ["from __future__ import annotations", "from pathlib import Path as P", "import typing", "__all__ = ['Thing', 'a', 'z']", "class Thing:", "    pass", "def a():", "    ...", "def z():", "    ...", "value: int = 3"]
    ast.parse("\n".join(lines))
```

- [ ] **Step 2: Run on 3.10 and 3.13.** Check the docstring string literal
  carefully: the expectation represents doubled backslashes and escaped triple
  quotes, while `ast.get_docstring(..., clean=False)` independently validates
  the underlying string. A syntax check never replaces exact output assertions.

- [ ] **Step 3: Show the invalid-expression option test detects ignored policy.**

```sh
env -u VIRTUAL_ENV uv run --no-project --python 3.10 --with 'pytest>=8,<9' python - <<'PY'
from unittest.mock import patch
import pytest
from pybind11_stubgen.printer import Printer
with patch.object(Printer, 'print_invalid_exp', return_value='...'):
    code = pytest.main(['tests/unit/test_printer.py::test_invalid_expression_policy', '-q'])
assert code == pytest.ExitCode.TESTS_FAILED, code
PY
```

- [ ] **Step 4: Rerun unpatched, cumulative tests and hooks; commit** as
  `test: cover exact printer output and rendering options`.

## Task 5: Writer paths, bytes, and failures

**Files:** Create `tests/unit/test_writer.py`.
Read `pybind11_stubgen/writer.py` in full.

**Interfaces:** Use the real `Writer`, real `Printer`, pytest `tmp_path`, and
explicit `Module` models. No global snapshot helper or external formatter.

- [ ] **Step 1: Add portable filesystem contract tests.**

```python
from pathlib import Path

import pytest

from pybind11_stubgen.printer import Printer
from pybind11_stubgen.structs import Docstring, Identifier, Module
from pybind11_stubgen.writer import Writer


def files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("extension", ["pyi", "py"])
def test_module_utf8_and_final_newline(tmp_path, extension):
    module = Module(Identifier("sample"), doc=Docstring("café"))
    Writer(extension).write_module(module, Printer(True), to=tmp_path)
    assert files(tmp_path) == {f"sample.{extension}": '"""\ncafé\n"""\n'.encode("utf-8")}


@pytest.mark.parametrize("extension", ["pyi", "py"])
def test_empty_package_gets_init_file(tmp_path, extension):
    Writer(extension).write_module(Module(Identifier("empty"), is_package=True), Printer(True), to=tmp_path)
    assert files(tmp_path) == {f"empty/__init__.{extension}": b""}


@pytest.mark.parametrize("extension", ["pyi", "py"])
def test_nested_submodule_layout(tmp_path, extension):
    leaf = Module(Identifier("leaf"), doc=Docstring("Leaf"))
    nested = Module(Identifier("nested"), sub_modules=[leaf])
    root = Module(Identifier("root"), sub_modules=[nested])
    Writer(extension).write_module(root, Printer(True), to=tmp_path)
    assert files(tmp_path) == {
        f"root/__init__.{extension}": b"from . import nested\n",
        f"root/nested/__init__.{extension}": b"from . import leaf\n",
        f"root/nested/leaf.{extension}": b'"""\nLeaf\n"""\n',
    }


def test_explicit_subdirectory_uses_init(tmp_path):
    Writer().write_module(Module(Identifier("sample"), doc=Docstring("Renamed")), Printer(True), to=tmp_path, sub_dir=Path("renamed"))
    assert files(tmp_path) == {"renamed/__init__.pyi": b'"""\nRenamed\n"""\n'}


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_invalid_output_root_is_rejected(tmp_path, kind):
    root = tmp_path / "output"
    if kind == "file":
        root.write_bytes(b"sentinel")
    with pytest.raises(AssertionError):
        Writer().write_module(Module(Identifier("sample")), Printer(True), to=root)
    assert files(tmp_path) == ({"output": b"sentinel"} if kind == "file" else {})


def test_write_error_propagates(tmp_path):
    # A directory at the output filename fails even when tests run as root.
    target = tmp_path / "sample.pyi"
    target.mkdir()
    with pytest.raises(OSError):
        Writer().write_module(Module(Identifier("sample")), Printer(True), to=tmp_path)
    assert target.is_dir()
    assert files(tmp_path) == {}
```

- [ ] **Step 2: Run on 3.10 and 3.13.** Empty modules intentionally produce empty
  files, not an invented newline. Nonempty rendered output ends in a newline.
  No chmod-based permission test or writer mock is needed.

- [ ] **Step 3: Demonstrate missing writes are caught.**

```sh
env -u VIRTUAL_ENV uv run --no-project --python 3.10 --with 'pytest>=8,<9' python - <<'PY'
from unittest.mock import patch
import pytest
from pybind11_stubgen.writer import Writer
with patch.object(Writer, 'write_module', return_value=None):
    code = pytest.main(['tests/unit/test_writer.py::test_module_utf8_and_final_newline', '-q'])
assert code == pytest.ExitCode.TESTS_FAILED, code
PY
```

- [ ] **Step 4: Rerun unpatched, cumulative tests and hooks; commit** as
  `test: cover writer layouts contents and error propagation`.

## Task 6: Compact pure-Python pipeline checks

**Files:** Create `tests/unit/test_pipeline.py`,
`tests/unit/fixtures/stubgen_test_package/__init__.py`, and
`tests/unit/fixtures/stubgen_test_package/leaf.py`.
Read `pybind11_stubgen/__init__.py:run` and `fix.py:FixMissing__all__Attribute`.

**Interfaces:** Consume `load_python_fixture`, `make_parser`, and the existing
`stubgen_test_python` fixture from Task 1. Use `run` so production finalization
and module-to-output orchestration are covered rather than reimplemented.

- [ ] **Step 1: Write pipeline tests with exact hand-checked output trees.**

```python
import ast
import logging

from pybind11_stubgen import run
from pybind11_stubgen.printer import Printer
from pybind11_stubgen.writer import Writer
from unit_support import make_parser


def test_python_module_pipeline(tmp_path, load_python_fixture, caplog):
    module = load_python_fixture("stubgen_test_python")
    run(make_parser(), Printer(True), [module.__name__], str(tmp_path), root_suffix=None, dry_run=False, writer=Writer())
    expected = (
        "from __future__ import annotations\n"
        "__all__: list = ['ADerived', 'ZBase', 'typed']\n"
        "class ZBase:\n"
        "    pass\n"
        "class ADerived(ZBase):\n"
        "    pass\n"
        "def typed(value: int, *, enabled: bool = True) -> str:\n"
        '    """\n'
        "    Convert.\n"
        '    """\n'
    )
    assert {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == {"stubgen_test_python.pyi": expected.encode("utf-8")}
    ast.parse(expected)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_package_pipeline(tmp_path, load_python_fixture, caplog):
    module = load_python_fixture("stubgen_test_package")
    run(make_parser(), Printer(True), [module.__name__], str(tmp_path), root_suffix=None, dry_run=False, writer=Writer())
    expected = {
        "stubgen_test_package/__init__.pyi": b"from __future__ import annotations\nfrom . import leaf\n__all__: list = ['leaf']\n",
        "stubgen_test_package/leaf.pyi": b"from __future__ import annotations\n__all__: list = ['double']\ndef double(value: int) -> int:\n    ...\n",
    }
    actual = {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert actual == expected
    for text in actual.values():
        ast.parse(text.decode("utf-8"))
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
```

- [ ] **Step 2: Run the package test before its fixture exists.** Expect
  `ModuleNotFoundError` for `stubgen_test_package`, not a native import failure.

- [ ] **Step 3: Add the package fixture.** `__init__.py`:

```python
from . import leaf

__all__ = ["leaf"]
```

`leaf.py`:

```python
__all__ = ["double"]


def double(value: int) -> int:
    return value * 2
```

- [ ] **Step 4: Run both tests and the cumulative suite on 3.10 and 3.13.**
  Confirm these tests need neither demo configuration nor optional packages.
  Run the pipeline file before the parser file, then in the reverse order, as
  separate pytest invocations; both orders must pass without import-state leaks.

- [ ] **Step 5: Show orchestration omission is detected, then restore by process exit.**

```sh
env -u VIRTUAL_ENV uv run --no-project --python 3.10 --with 'pytest>=8,<9' python - <<'PY'
from unittest.mock import patch
import pytest
from pybind11_stubgen.writer import Writer
with patch.object(Writer, 'write_module', return_value=None):
    code = pytest.main(['tests/unit/test_pipeline.py', '-q'])
assert code == pytest.ExitCode.TESTS_FAILED, code
PY
```

- [ ] **Step 6: Rerun unpatched, cumulative checks and hooks; commit** as
  `test: exercise pure Python generation pipeline without native bindings`.

## Task 7: Compiler-free runners, CI configuration, and acceptance

**Files:** Append a unit section to `tox.ini`; add one job and one dependency
entry to `.github/workflows/ci.yml`; update `tests/README.md`.
Read those three files in full before editing. Do not alter existing native
commands, dependencies, matrix rows, build workflow, or gemmi steps.

**Interfaces:** Consume `STUBGEN_TEST_INSTALLED=1` and the no-package test import
layout from Task 1. Every new runner executes exactly `tests/unit` and
`tests/test_snapshot_helpers.py`; installed runs use `python -I -m pytest`.

- [ ] **Step 1: Capture the pre-configuration failures.** A clean wheel/pytest
  environment can already run the tests manually, but requesting `py310-unit`
  before the explicit section exists either fails or inherits native setup.
  Use `tox list`/`tox config -e py310-unit` to inspect it; do not deliberately
  launch a native build with missing factors. Record the missing dedicated
  compiler-free configuration as setup-red, then verify actual runs after editing.

- [ ] **Step 2: Add this dedicated tox section, leaving the default list intact.**

```ini
[testenv:py{310,311,312,313}-unit]
description = Check compiler-free production contracts and snapshot helpers
package = skip
setenv =
    PYTHONUNBUFFERED = 1
    STUBGEN_TEST_INSTALLED = 1
allowlist_externals =
    uv
deps =
    pytest>=8,<9
commands_pre =
commands =
    uv pip install --python "{envpython}" .
    {envpython} -I -m pytest {toxinidir}/tests/unit {toxinidir}/tests/test_snapshot_helpers.py {posargs}
```

  The explicit empty `commands_pre` overrides the inherited demo installer.
  `deps` and `setenv` likewise replace the native defaults. Render `tox config`
  for all four unit environments and one native environment to inspect resolved
  values, but require actual execution, not config text tests, for acceptance.

- [ ] **Step 3: Add this CI job alongside, not inside, the native job.**

```yaml
  unit-tests:
    name: "Compiler-free tests • Python ${{ matrix.python }}"
    runs-on: ubuntu-latest
    needs: [build]
    strategy:
      fail-fast: false
      matrix:
        python: ["3.10", "3.11", "3.12", "3.13"]
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - uses: astral-sh/setup-uv@v7
      - uses: actions/download-artifact@v6
        with:
          name: dist
          path: dist
      - name: Install wheel and pytest only
        shell: bash
        run: |
          uv venv .venv
          uv pip install --python .venv/bin/python 'pytest>=8,<9' dist/*.whl
      - name: Test installed wheel without native fixtures
        env:
          STUBGEN_TEST_INSTALLED: "1"
        run: .venv/bin/python -I -m pytest tests/unit tests/test_snapshot_helpers.py
```

  Change only the publication job's `needs` list to
  `[check, build, unit-tests, tests, test-cli-options]`. Leave its condition,
  permissions, artifacts, and publishing steps untouched. No remote action is
  authorized. Do not add pytest annotation packages or `uv sync` to the new job.

- [ ] **Step 4: Document the new test layers and exact commands.** Add a
  `Compiler-free production tests` section before `Native checks` in
  `tests/README.md` with:

````markdown
## Compiler-free production tests

`tests/unit/` covers parser/signature and annotation behavior, class ordering,
printer output, writer paths/contents, and small pure-Python generation flows.
Its fixtures are independent of `demo`; no native installation or NumPy/SciPy
is needed. The following command tests source edits directly without syncing
the development dependency group:

```sh
uv run --no-project --isolated --with 'pytest>=8,<9' python -m pytest \
  tests/unit tests/test_snapshot_helpers.py
```

To test a non-editable installation on each supported matrix interpreter:

```sh
uv run --no-project --with tox --with tox-uv tox \
  -e py310-unit,py311-unit,py312-unit,py313-unit
```

The unit environments install with uv, run isolated Python, and verify the
actual pytest process imports the installed generator. The default tox list
still runs the existing 13 native configurations; unit environments are explicit.
CI adds a separate compiler-free wheel matrix while retaining native/gemmi jobs.
````

  Replace the existing `Add a regression` section with this routing advice;
  leave the preceding deliberate-update instructions unchanged:

```markdown
## Add a regression

For harness behavior, add a small synthetic test to `test_snapshot_helpers.py`.
For compiler-free generator behavior, prefer a focused test in `tests/unit/`
with explicit expected models or text. Neither route requires a compiler.

When the regression requires real binding behavior, add or adjust the native
demo fixture, run a relevant native environment, inspect its failure, then
explicitly update that environment's expectations. Review only the intended
changes and run affected shared profiles and the compatibility matrix before
merging.

During test-only phase two, report newly discovered production bugs separately.
Do not hide them with changed expectations, unexplained skips, or snapshot
updates; production fixes require a separate scope.
```

- [ ] **Step 5: Run all four unit tox environments serially.**

```sh
env -u VIRTUAL_ENV uv run --no-project --with tox --with tox-uv tox \
  -e py310-unit,py311-unit,py312-unit,py313-unit
```

  Require pytest success with the installed-origin fixture enabled. No native
  build/install step or formatter invocation may appear in their logs. Inspect
  these environments with isolated Python to assert `find_spec('demo')`,
  `find_spec('numpy')`, and `find_spec('scipy')` are all `None`. Record actual
  package origins and Python versions. These are environment acceptance probes,
  not tests that demand optional packages be absent in every developer environment.

- [ ] **Step 6: Prove source-mode purity in fresh pytest-only environments.**
  Use ignored verification paths, not the native `.tox` environments. For each
  Python 3.10–3.13, create a fresh uv venv, install only pytest, assert optional
  module absence and invoke Python from the worktree with ordinary `-m pytest`.
  This deliberately tests source, so do not set `STUBGEN_TEST_INSTALLED` here.

```sh
mkdir -p .superpowers/sdd/2026-09-25-test-harness-phase-two/verification
for version in 3.10 3.11 3.12 3.13; do
  envdir=".superpowers/sdd/2026-09-25-test-harness-phase-two/verification/source-$version"
  test ! -e "$envdir" || exit 1
  uv venv --python "$version" "$envdir" || exit 1
  uv pip install --python "$envdir/bin/python" 'pytest>=8,<9' || exit 1
  "$envdir/bin/python" -I -c 'from importlib.util import find_spec; assert all(find_spec(n) is None for n in ("demo", "numpy", "scipy", "pybind11_stubgen"))' || exit 1
  env -u STUBGEN_TEST_INSTALLED "$envdir/bin/python" -m pytest tests/unit tests/test_snapshot_helpers.py -q || exit 1
done
```

  These commands intentionally refuse to overwrite a previous environment;
  choose a new ignored run directory when repeating them. Do not turn this
  acceptance probe into a new packaged dependency manager.

- [ ] **Step 7: Reproduce CI-style wheel runs locally on all four versions.**
  Build the wheel once into an ignored directory; do not sync project dependencies.

```sh
test ! -e .superpowers/sdd/2026-09-25-test-harness-phase-two/verification/dist || exit 1
env -u VIRTUAL_ENV uv build --wheel --out-dir .superpowers/sdd/2026-09-25-test-harness-phase-two/verification/dist || exit 1
for version in 3.10 3.11 3.12 3.13; do
  envdir=".superpowers/sdd/2026-09-25-test-harness-phase-two/verification/wheel-$version"
  test ! -e "$envdir" || exit 1
  uv venv --python "$version" "$envdir" || exit 1
  uv pip install --python "$envdir/bin/python" 'pytest>=8,<9' .superpowers/sdd/2026-09-25-test-harness-phase-two/verification/dist/*.whl || exit 1
  "$envdir/bin/python" -I -c 'from importlib.util import find_spec; import sys, pybind11_stubgen; from pathlib import Path; p=Path(pybind11_stubgen.__file__).resolve(); assert p.is_relative_to(Path(sys.prefix).resolve()), p; assert all(find_spec(n) is None for n in ("demo", "numpy", "scipy")); print(sys.version, p)' || exit 1
  STUBGEN_TEST_INSTALLED=1 "$envdir/bin/python" -I -m pytest tests/unit tests/test_snapshot_helpers.py -q || exit 1
done
```

  Confirm an independent same-process guard rejects checkout shadowing:

```sh
STUBGEN_TEST_INSTALLED=1 .superpowers/sdd/2026-09-25-test-harness-phase-two/verification/wheel-3.10/bin/python -m pytest tests/unit/test_parser.py::test_python_signature -q
```

  Expect exit 1 with an origin assertion failure because `-I` is intentionally
  absent. Rerun that environment's isolated command to prove green. Do not claim
  the separate `-c` preflight alone establishes installed test coverage.

- [ ] **Step 8: Recheck all 13 native configurations with an immutability audit.**
  Use the retained phase-one `task-6-logs/verify_run.py` if present, or create the
  following equivalent ignored audit script as
  `.superpowers/sdd/2026-09-25-test-harness-phase-two/verify_native.py`:

```python
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
REPORT = ROOT / '.superpowers/sdd/2026-09-25-test-harness-phase-two'


def references():
    result = {}
    def visit(path):
        key = path.relative_to(ROOT).as_posix()
        if path.is_symlink():
            result[key] = ['link', os.readlink(path)]
        elif path.is_dir():
            result[key] = ['directory']
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            result[key] = ['file', hashlib.sha256(path.read_bytes()).hexdigest()]
    for name in ('tests/stubs', 'tests/errors'):
        visit(ROOT / name)
    return result


before = references()
index = subprocess.check_output(['git', 'ls-files', '--stage', '-z'])
command = ['env', '-u', 'VIRTUAL_ENV', 'uv', 'run', '--no-project', '--with', 'tox', '--with', 'tox-uv', 'tox']
with (REPORT / 'native.log').open('wb') as log:
    process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=1200)
audit = {
    'command': command,
    'returncode': process.returncode,
    'references_unchanged': references() == before,
    'index_unchanged': subprocess.check_output(['git', 'ls-files', '--stage', '-z']) == index,
}
(REPORT / 'native-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
print(json.dumps(audit, indent=2))
assert audit['references_unchanged'] and audit['index_unchanged']
sys.exit(process.returncode)
```

  Run that script from the worktree root. Inspect `native.log` to verify exactly
  the original 13 environments passed both native comparisons and all harness
  self-tests without deselection or snapshot updates. Stop on timeout/failure;
  retain logs and diagnose, never rerun with checks excluded to claim acceptance.
  A timeout is not a successful immutability audit.

- [ ] **Step 9: Verify preservation, lock, formatting, and scope.**

```sh
git diff --exit-code a306491 -- pybind11_stubgen tests/demo-lib tests/py-demo tests/install-demo-module.sh tests/stubs tests/errors tests/conftest.py tests/snapshot_helpers.py tests/test_snapshot_helpers.py tests/test_demo_stubs.py tests/test_demo_errors.py pyproject.toml uv.lock
env -u VIRTUAL_ENV uv lock --check
env -u VIRTUAL_ENV uv run pre-commit run --all-files
git diff --check
git diff a306491 -- tox.ini .github/workflows/ci.yml
git status --short
```

  Review the last configuration diff for unchanged default/native matrix,
  dependencies, gemmi, build, publication trigger and permissions. YAML parsing
  hooks establish syntax only; actual remote behavior remains unverified. If
  hooks reformat tests, repeat the compiler-free matrix before committing.

- [ ] **Step 10: Commit only configuration/documentation changes and request review.**
  Commit as `test: run compiler-free contracts across supported Python versions`.
  Report source/unit-tox/wheel/native results separately, installed origins,
  reference/index audits, known bug reproductions, hooks, commit range and
  unexecuted remote CI. Do not describe phase one or two as remotely accepted.

## Plan self-review and handoff

Spec mapping: parser + isolation/support → Task 1; annotations/invalid input →
Task 2; graph ordering and nested consumer → Task 3; renderer/options → Task 4;
writer/error propagation → Task 5; independent packages + pipeline → Task 6;
Python matrix, wheel origins, native preservation, CI, documentation and final
acceptance → Task 7. Every task is independently reviewable after its prerequisites.

The plan does not authorize broader fixture extraction, packaging cleanup,
production bug fixes, snapshot regeneration, build simplification, or remote
execution. Those require a separately approved scope.
