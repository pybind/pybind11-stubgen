import importlib
import sys
from pathlib import Path

import pytest

from pybind11_stubgen.parser.mixins.error_handlers import LocalErrors
from unit_support import make_parser, q


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
