import sys
from pathlib import Path

import pytest

from snapshot_helpers import BRANCHES, NUMPY_FORMATS, make_case


def pytest_addoption(parser):
    group = parser.getgroup("demo snapshots")
    group.addoption("--pybind11-branch", choices=BRANCHES)
    group.addoption("--numpy-format", choices=NUMPY_FORMATS)
    group.addoption("--update-snapshots", action="store_true", default=False)
    group.addoption("--artifacts-dir", type=Path)


@pytest.fixture
def demo_case(pytestconfig):
    return make_case(
        Path(__file__).resolve().parents[1],
        sys.version_info[:2],
        pytestconfig.getoption("pybind11_branch"),
        pytestconfig.getoption("numpy_format"),
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
