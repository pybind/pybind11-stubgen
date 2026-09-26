import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from native_support import check_versions, require_origin, runtime_pins, select_modes

A = "numpy-array-wrap-with-annotated"
T = "numpy-array-use-type-var"


def test_modes_preserve_order_and_cli_overrides():
    assert select_modes(None, f"{A} {T}") == (A, T)
    assert select_modes(T, f"{A} {T}") == (T,)
    assert select_modes(A, None) == (A,)


@pytest.mark.parametrize("value", [None, "", "unknown", f"{A} {A}"])
def test_invalid_defaults_are_errors_not_empty_parameters(value):
    with pytest.raises(ValueError):
        select_modes(None, value)


def test_invalid_explicit_mode():
    with pytest.raises(ValueError):
        select_modes("unknown", A)


def test_origin_checks_path_components_and_missing_origins(tmp_path):
    prefix = tmp_path / "env"
    origin = prefix / "lib" / "module.py"
    assert require_origin("module", str(origin), prefix) == origin
    for outside in (None, str(tmp_path / "env-other" / "module.py")):
        with pytest.raises(RuntimeError, match="module"):
            require_origin("module", outside, prefix)


def test_runtime_pins_and_drift():
    env = {"STUBGEN_NUMPY_VERSION": "2.2.6", "STUBGEN_SCIPY_VERSION": "1.15.3"}
    expected = {"numpy": "2.2.6", "scipy": "1.15.3"}
    assert runtime_pins(env) == expected
    assert runtime_pins({}) == {}
    check_versions(expected, expected)
    with pytest.raises(ValueError):
        runtime_pins({"STUBGEN_NUMPY_VERSION": "2.2.6"})
    for actual in ({}, {**expected, "numpy": "1.26.4"}):
        with pytest.raises(RuntimeError, match="numpy"):
            check_versions(expected, actual)


@pytest.mark.parametrize("explicit, expected_count", [(None, 2), (T, 1)])
def test_real_pytest_runs_remaining_mode_after_failure(
    tmp_path, explicit, expected_count
):
    tests_root = Path(__file__).resolve().parents[1]
    for name in ("conftest.py", "snapshot_helpers.py", "native_support.py"):
        shutil.copyfile(tests_root / name, tmp_path / name)
    (tmp_path / "test_modes.py").write_text(
        "import pytest\n"
        "@pytest.fixture\n"
        "def demo_case(request): return request.param\n"
        "def test_mode(demo_case):\n"
        f"    assert demo_case != {A!r}\n"
    )
    env = {k: v for k, v in os.environ.items() if not k.startswith("STUBGEN_")}
    env.pop("PYTEST_ADDOPTS", None)
    env["STUBGEN_NUMPY_FORMATS"] = f"{A} {T}"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    command = [
        sys.executable,
        "-I",
        "-m",
        "pytest",
        "test_modes.py",
        "-q",
        "--confcutdir",
        str(tmp_path),
        "--junitxml",
        "result.xml",
    ]
    if explicit:
        command += ["--numpy-format", explicit]
    result = subprocess.run(
        command, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == (1 if explicit is None else 0), (
        result.stdout + result.stderr
    )
    cases = ET.parse(tmp_path / "result.xml").findall(".//testcase")
    assert len(cases) == expected_count
    assert [c.attrib["name"] for c in cases] == (
        [f"test_mode[{A}]", f"test_mode[{T}]"]
        if explicit is None
        else [f"test_mode[{T}]"]
    )
    assert sum(c.find("failure") is not None for c in cases) == (explicit is None)
    assert not any(c.find("skipped") is not None for c in cases)
