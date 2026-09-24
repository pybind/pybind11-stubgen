import ast
import logging

from pybind11_stubgen import run
from pybind11_stubgen.printer import Printer
from pybind11_stubgen.writer import Writer
from unit_support import make_parser


def test_python_module_pipeline(tmp_path, load_python_fixture, caplog):
    module = load_python_fixture("stubgen_test_python")
    run(
        make_parser(),
        Printer(True),
        [module.__name__],
        str(tmp_path),
        root_suffix=None,
        dry_run=False,
        writer=Writer(),
    )
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
    assert {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    } == {"stubgen_test_python.pyi": expected.encode("utf-8")}
    ast.parse(expected)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_package_pipeline(tmp_path, load_python_fixture, caplog):
    module = load_python_fixture("stubgen_test_package")
    run(
        make_parser(),
        Printer(True),
        [module.__name__],
        str(tmp_path),
        root_suffix=None,
        dry_run=False,
        writer=Writer(),
    )
    expected = {
        "stubgen_test_package/__init__.pyi": b"from __future__ import annotations\nfrom . import leaf\n__all__: list = ['leaf']\n",
        "stubgen_test_package/leaf.pyi": b"from __future__ import annotations\n__all__: list = ['double']\ndef double(value: int) -> int:\n    ...\n",
    }
    actual = {
        p.relative_to(tmp_path).as_posix(): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert actual == expected
    for text in actual.values():
        ast.parse(text.decode("utf-8"))
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
