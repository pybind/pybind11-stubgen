import hashlib
import importlib
import importlib.metadata
import os
import sys
from pathlib import Path

import pytest

from native_support import check_versions, require_origin, runtime_pins, select_modes
from snapshot_helpers import BRANCHES, NUMPY_FORMATS, make_case


def pytest_addoption(parser):
    group = parser.getgroup("demo snapshots")
    group.addoption("--pybind11-branch", choices=BRANCHES)
    group.addoption("--numpy-format", choices=NUMPY_FORMATS)
    group.addoption("--update-snapshots", action="store_true", default=False)
    group.addoption("--artifacts-dir", type=Path)


def pytest_generate_tests(metafunc):
    if "demo_case" not in metafunc.fixturenames:
        return
    try:
        modes = select_modes(
            metafunc.config.getoption("numpy_format"),
            os.environ.get("STUBGEN_NUMPY_FORMATS"),
        )
    except ValueError as exc:
        raise pytest.UsageError(str(exc)) from exc
    metafunc.parametrize("demo_case", modes, indirect=True, ids=modes)


@pytest.fixture(scope="session", autouse=True)
def enforce_installed_origin():
    if os.environ.get("STUBGEN_TEST_INSTALLED") != "1":
        return
    importlib.import_module("pybind11_stubgen")
    for name, module in list(sys.modules.items()):
        if name == "pybind11_stubgen" or name.startswith("pybind11_stubgen."):
            require_origin(name, getattr(module, "__file__", None), Path(sys.prefix))


@pytest.fixture(scope="session")
def installed_native(record_testsuite_property):
    prefix = Path(sys.prefix)
    demo = importlib.import_module("demo")
    extension = importlib.import_module("demo._bindings")
    require_origin("demo", demo.__file__, prefix)
    path = require_origin("demo._bindings", extension.__file__, prefix)
    expected = runtime_pins(os.environ)
    before = {name: importlib.metadata.version(name) for name in ("numpy", "scipy")}
    check_versions(expected, before)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    record_testsuite_property("native_extension", str(path))
    record_testsuite_property("native_extension_sha256", digest)
    record_testsuite_property(
        "native_python", f"{sys.version_info.major}.{sys.version_info.minor}"
    )
    for name, version in before.items():
        record_testsuite_property(name, version)
    yield
    after = {name: importlib.metadata.version(name) for name in before}
    check_versions(before, after)
    check_versions(expected, after)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path


@pytest.fixture
def demo_case(request, pytestconfig, installed_native):
    return make_case(
        Path(__file__).resolve().parents[1],
        sys.version_info[:2],
        pytestconfig.getoption("pybind11_branch"),
        request.param,
    )


@pytest.fixture
def update_snapshots(pytestconfig):
    return pytestconfig.getoption("update_snapshots")


@pytest.fixture
def artifacts_dir(pytestconfig):
    return pytestconfig.getoption("artifacts_dir")


@pytest.fixture
def report_update(pytestconfig):
    def report(message):
        terminal = pytestconfig.pluginmanager.get_plugin("terminalreporter")
        if terminal is None:
            print(message)
        else:
            terminal.write_line(message)

    return report
