from pathlib import Path

import pytest

from pybind11_stubgen.printer import Printer
from pybind11_stubgen.structs import Docstring, Identifier, Module
from pybind11_stubgen.writer import Writer


def files(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize("extension", ["pyi", "py"])
def test_module_utf8_and_final_newline(tmp_path, extension):
    module = Module(Identifier("sample"), doc=Docstring("café"))
    Writer(extension).write_module(module, Printer(True), to=tmp_path)
    assert files(tmp_path) == {
        f"sample.{extension}": '"""\ncafé\n"""\n'.encode("utf-8")
    }


@pytest.mark.parametrize("extension", ["pyi", "py"])
def test_empty_package_gets_init_file(tmp_path, extension):
    Writer(extension).write_module(
        Module(Identifier("empty"), is_package=True), Printer(True), to=tmp_path
    )
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
    Writer().write_module(
        Module(Identifier("sample"), doc=Docstring("Renamed")),
        Printer(True),
        to=tmp_path,
        sub_dir=Path("renamed"),
    )
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
