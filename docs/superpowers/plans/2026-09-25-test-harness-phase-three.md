# Shared Native Test Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the same 13 native compatibility cases through 11 independently built tox profiles locally and in CI, using a standard fixture backend and explicit dependencies without changing generator behavior or snapshots.

**Architecture:** Tox owns the native environment list, dependency choices, and default NumPy modes. Pytest parameterizes modes within an installed environment; a small stdlib helper builds and installs one fixture wheel using tox-provisioned tools. A separate stdlib adapter translates tox's expanded default environment names into CI matrix JSON; it does not manage builds or environments.

**Tech Stack:** Python 3.10–3.13, pytest 8, tox 4 with tox-uv, uv, scikit-build-core 1.0.3, Ninja 1.13.2, CMake, pybind11, cmeel/Eigen, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-25-test-harness-phase-three-design.md` (approved, including the NumPy/SciPy reconciliation).

## Global Constraints

- Continue in `.worktrees/test-harness-phase-one` on `test-harness-phase-one`; preserve runtime/source invariants against `807e7e44a1536699faf0070978303f58caa45648`.
- Every production file under `pybind11_stubgen/` remains unchanged.
- Native C++ fixture source/header contents and existing Python files under `tests/py-demo/demo/` remain unchanged.
- Reference bytes and symlink aliases under `tests/stubs/` and `tests/errors/` remain unchanged.
- Preserve snapshot comparison, normalization, update guards, process contracts, existing 300-second snapshot subprocess timeouts, and diagnostic retention.
- Preserve all 13 logical compatibility cases and both native checks for each case. The default native list becomes exactly 11 profiles; the four `py310-unit` through `py313-unit` environments remain explicit.
- Preserve generator build backend/package discovery, the root development dependency group and lockfile, gemmi jobs, workflow triggers, and publication conditions and permissions.
- Preserve compiler-free independence from native/optional dependencies and formatter downloads; new support tests require only pytest and the standard library beyond the generator.
- pybind11 pins: `2.9.2`, `2.11.2`, `2.12.1`, `2.13.6`, `3.0.4` for series `v2.9`, `v2.11`, `v2.12`, `v2.13`, `v3.0` respectively.
- CMake evaluation pins: `3.31.10`, `3.28.3`, `3.28.3`, `4.2.3`, `4.2.3` for those same series respectively.
- Retain `cmeel==0.59.0` and `cmeel-eigen==3.4.0.2`; new backend/tool pins are `scikit-build-core==1.0.3` and `ninja==1.13.2`.
- NumPy/SciPy pins: Python 3.10 uses `2.2.6`/`1.15.3`; Python 3.11 uses `2.4.6`/`1.17.1`; Python 3.12–3.13 use `2.5.3`/`1.17.1`.
- These runtime pins preserve the observed baseline. The old fixture installer replaces NumPy despite tox declaring `numpy~=1.20`; do not reproduce that dependency drift.
- No broad dependency upgrades, snapshot regeneration/reorganization, production fixes, new platform matrix, or persistent cross-environment native wheel cache.
- No push, PR, remote workflow execution, or publication. Remote acceptance remains explicitly unverified.
- Do not silently change an evaluation pin or weaken an assertion to accommodate a failure. Investigate, report, and obtain a scope decision when necessary.

## File map and boundaries

| File | Responsibility |
| --- | --- |
| `tests/native_support.py` (new) | Pure mode selection, origin validation, and runtime-version checks; no imports of native packages. |
| `tests/conftest.py` | Shared installed-generator guard, native fixture provenance/reuse evidence, mode parameterization. |
| `tests/unit/conftest.py` | Keep parser/fixture isolation; remove only the installed guard moved to the parent. |
| `tests/unit/test_native_support.py` (new) | Pure contracts plus a real subprocess pytest check of grouped-mode execution. |
| `tests/build_native.py` (new) | One explicitly targeted fixture wheel build/install, dependency checks, owned run directories, retained logs/payload evidence. |
| `tests/unit/test_build_native.py` (new) | Command boundaries, filesystem isolation, payload and failure contracts without a compiler. |
| `tests/py-demo/pyproject.toml` | Standard fixture backend and existing package metadata. |
| `tests/py-demo/bindings/CMakeLists.txt` | Explicit Python/pybind11 discovery and component-scoped extension installation. |
| `tests/py-demo/setup.py`, `tests/install-demo-module.sh` | Remove after their replacements are integrated and validated. |
| `tox.ini` | Single native profile/dependency/mode authority, local wheel packaging, installed pytest execution. |
| `tests/native_matrix.py` (new) | Validate expanded tox names and emit compact CI matrix JSON. |
| `tests/unit/test_native_matrix.py` (new) | Independent case inventory, adapter validation, real CLI failures. |
| `.github/workflows/ci.yml` | Derive native matrix, invoke tox with the downloaded wheel, retain early and late failure diagnostics. |
| `tests/README.md` | Commands, renamed profiles, dependency policy, serial updates, and verification boundaries. |

No new `__init__.py` files in test/support directories. Do not refactor `tests/snapshot_helpers.py` or rewrite the native test bodies: parameterize their existing `demo_case` fixture.

## Common verification and evidence

Use an ignored workspace belonging to this plan only:

```sh
E="$(pwd)/.superpowers/sdd/2026-09-25-test-harness-phase-three"
git check-ignore -q "$E"
mkdir -p "$E"
```

Set `E` in each shell invocation that uses it; tool calls do not share shell variables. After building a generator wheel, save its absolute path in `$E/generator-wheel.path` and reload `WHEEL` from that file in later commands. Keep logs, disposable source copies, command/status records, and per-task reports there. Do not read or reuse another plan's scratch helpers. Capture before/after reference and index states for every native verification batch. Intentional commits change the index between batches; comparisons are within each batch, not against the pre-implementation index forever.

Fast checks, repeated on both endpoint interpreters during each task:

```sh
for version in 3.10 3.13; do
  env -u VIRTUAL_ENV uv run --no-project --isolated --python "$version" \
    --with 'pytest>=8,<9' python -m pytest tests/unit tests/test_snapshot_helpers.py -q
done
```

Use `--isolated`: `--no-project` alone can reuse a worktree environment. Native tools are bootstrap dependencies of the orchestrator, not dependencies of the compiler-free suite:

```sh
env -u VIRTUAL_ENV uv run --no-project --isolated --with tox --with tox-uv tox --version
```

Planning inspected tox 4.64.2/tox-uv 1.36.0. The production adapter uses the longstanding `tox list -d --no-desc` interface, not private tox APIs or its newer JSON configuration serializer. `tox config --format json` below is a verification aid; use the inspected tox version for those checks if an older local tool lacks it.

At each task's end, run applicable pre-commit hooks, `git diff --check`, inspect scope, self-review, and commit only the task's files. Include focused/cumulative results, expected negative-control failures, and limits in its report. A setup/import failure before implementation is not sufficient sensitivity evidence: exercise a broken behavioral path too.

### Native batch audit helper (ignored evidence, not shipped support)

Create `$E/audit_native.py` before the first baseline run. It audits any command after `--`; it is not an alternate native runner or matrix source.

```python
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument("--label", required=True)
p.add_argument("command", nargs=argparse.REMAINDER)
a = p.parse_args()
command = a.command[1:] if a.command[:1] == ["--"] else a.command
if not command or not a.label.replace("-", "").isalnum():
    p.error("provide a simple label and a command after --")
root = Path.cwd()
out = root / ".superpowers/sdd/2026-09-25-test-harness-phase-three"
out.mkdir(parents=True, exist_ok=True)

def state():
    entries = {}
    def visit(path):
        key = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries[key] = ["link", os.readlink(path)]
        elif path.is_dir():
            entries[key] = ["directory"]
            for child in sorted(path.iterdir()):
                visit(child)
        else:
            entries[key] = ["file", hashlib.sha256(path.read_bytes()).hexdigest()]
    for name in ("tests/stubs", "tests/errors"):
        visit(root / name)
    entries["INDEX"] = subprocess.check_output(
        ["git", "ls-files", "--stage", "-z"]
    ).decode()
    return entries

before = state()
env = dict(os.environ)
env.pop("VIRTUAL_ENV", None)
env["UV_LINK_MODE"] = "copy"
start = time.monotonic()
status = None
error = None
try:
    with (out / (a.label + ".log")).open("xb") as log:
        status = subprocess.run(
            command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600
        ).returncode
except Exception as exc:
    error = repr(exc)
after = state()
report = {
    "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "command": command, "returncode": status, "error": error,
    "seconds": time.monotonic() - start, "unchanged": before == after,
    "before": before, "after": after,
}
(out / (a.label + ".json")).write_text(json.dumps(report, indent=2) + "\n")
assert error is None and status == 0 and before == after, report["error"] or a.label
```

Use unique labels; existing logs must not be overwritten. Read the actual test summaries and case inventories as well as the audit result.

---

### Task 1: Grouped-mode pytest contracts and shared installed provenance

**Files:**
- Create: `tests/native_support.py`, `tests/unit/test_native_support.py`.
- Modify: `tests/conftest.py`, `tests/unit/conftest.py`.

**Interfaces:**
- Consumes: `snapshot_helpers.NUMPY_FORMATS`, `make_case(repo, python_version, branch, numpy_format)`; existing native tests request `demo_case`.
- Produces: `select_modes(explicit: str | None, defaults: str | None) -> tuple[str, ...]`; `require_origin(name: str, origin: str | None, prefix: Path) -> Path`; `check_versions(expected: Mapping[str, str], actual: Mapping[str, str]) -> None`; `runtime_pins(environ: Mapping[str, str]) -> dict[str, str]`.
- Environment contract: `STUBGEN_NUMPY_FORMATS` is whitespace-separated default modes; `STUBGEN_NUMPY_VERSION` and `STUBGEN_SCIPY_VERSION` are either both present or both absent. CLI `--numpy-format` overrides defaults. `STUBGEN_TEST_INSTALLED=1` enables the parent installed-generator guard.
- Produces native JUnit properties for extension path/hash, interpreter, and runtime versions; no new writes to caller-supplied artifact directories.

- [ ] **Step 1: Capture the unchanged baseline before editing test support.**

Verify a clean worktree and the spec's preservation anchor. Run the fast selection on 3.10/3.13 and the existing 13 native profiles serially:

```sh
python "$E/audit_native.py" --label baseline -- \
  uv run --no-project --isolated --with tox --with tox-uv tox
```

Expected: 13 native environments, 99 tests each, both native comparisons in every environment, unchanged references/index. Record actual NumPy/SciPy and CMake versions with each environment's `importlib.metadata.version`; compare them to the spec's tables. Investigate baseline failures rather than starting the migration over them.

- [ ] **Step 2: Write the pure contract and actual pytest-execution tests first.**

Use this test core in `tests/unit/test_native_support.py`:

```python
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
def test_real_pytest_runs_remaining_mode_after_failure(tmp_path, explicit, expected_count):
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
    command = [sys.executable, "-I", "-m", "pytest", "test_modes.py", "-q",
               "--confcutdir", str(tmp_path), "--junitxml", "result.xml"]
    if explicit:
        command += ["--numpy-format", explicit]
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True,
                            text=True, timeout=30)
    assert result.returncode == (1 if explicit is None else 0), result.stdout + result.stderr
    cases = ET.parse(tmp_path / "result.xml").findall(".//testcase")
    assert len(cases) == expected_count
    assert [c.attrib["name"] for c in cases] == (
        [f"test_mode[{A}]", f"test_mode[{T}]"] if explicit is None else [f"test_mode[{T}]"]
    )
    assert sum(c.find("failure") is not None for c in cases) == (explicit is None)
    assert not any(c.find("skipped") is not None for c in cases)
```

- [ ] **Step 3: Run the new file and observe missing-support failure, then implement the pure helper.**

```sh
env -u VIRTUAL_ENV uv run --no-project --isolated --python 3.10 \
  --with 'pytest>=8,<9' python -m pytest tests/unit/test_native_support.py -q
```

Create `tests/native_support.py` with these contracts (stdlib plus the existing stdlib-only snapshot helper):

```python
from collections.abc import Mapping
from pathlib import Path

from snapshot_helpers import NUMPY_FORMATS


def select_modes(explicit: str | None, defaults: str | None) -> tuple[str, ...]:
    modes = (explicit,) if explicit is not None else tuple((defaults or "").split())
    if not modes or any(mode not in NUMPY_FORMATS for mode in modes):
        raise ValueError("Native tests require --numpy-format or valid STUBGEN_NUMPY_FORMATS")
    if len(set(modes)) != len(modes):
        raise ValueError("Duplicate NumPy modes")
    return modes


def require_origin(name: str, origin: str | None, prefix: Path) -> Path:
    prefix = prefix.resolve()
    if origin is None or not Path(origin).resolve().is_relative_to(prefix):
        raise RuntimeError(f"{name} must be installed under {prefix}; found {origin}")
    return Path(origin).resolve()


def check_versions(expected: Mapping[str, str], actual: Mapping[str, str]) -> None:
    for name, version in expected.items():
        if actual.get(name) != version:
            raise RuntimeError(f"Dependency drift: {name}: expected {version}, found {actual.get(name)}")


def runtime_pins(environ: Mapping[str, str]) -> dict[str, str]:
    result = {
        name: environ[key]
        for name, key in (("numpy", "STUBGEN_NUMPY_VERSION"), ("scipy", "STUBGEN_SCIPY_VERSION"))
        if key in environ
    }
    if len(result) == 1 or any(not version for version in result.values()):
        raise ValueError("Set both NumPy and SciPy pins, or neither for a direct rerun")
    return result
```

- [ ] **Step 4: Integrate the helpers into the existing pytest fixtures.**

Move the installed guard from `tests/unit/conftest.py` into the root conftest; remove its now-unused `os` import from the unit conftest, leaving all parser/import-isolation behavior untouched. Add these imports to the parent and retain its existing imports:

```python
import hashlib
import importlib
import importlib.metadata
import os

from native_support import check_versions, require_origin, runtime_pins, select_modes
```

Keep the existing options, update/artifact/report fixtures. Replace only `demo_case` and add the following hooks/fixtures:

```python
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
    record_testsuite_property("native_python", f"{sys.version_info.major}.{sys.version_info.minor}")
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
        Path(__file__).resolve().parents[1], sys.version_info[:2],
        pytestconfig.getoption("pybind11_branch"), request.param,
    )
```

The runtime pin environment is intentionally optional for an explicit direct rerun and old-profile transition; tox will always provide both pins after Task 3. The native module checks do not require every pybind11-created submodule to have `__file__`; validate the package and actual extension, not virtual C++ submodules.

- [ ] **Step 5: Verify sensitivity and compatibility, then commit.**

Run the focused file and cumulative fast selection on 3.10/3.13. The synthetic two-mode test must produce one failure and one pass internally while its outer regression test passes. Run this process-local negative control with isolated uv supplying pytest, then rerun the unpatched focused file:

```python
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path("tests").resolve()))
import native_support
import pytest

original = native_support.select_modes
with patch.object(native_support, "select_modes", side_effect=lambda e, d: original(e, d)[:1]):
    code = pytest.main(["tests/unit/test_native_support.py::test_modes_preserve_order_and_cli_overrides", "-q"])
assert code == pytest.ExitCode.TESTS_FAILED, code
```

Run at least `py313-pb30-naa` and `py313-pb29-naa` through the unchanged legacy installer using the batch audit. They still receive the old single-mode CLI option. Do not rename environments or alter dependencies in this task.

```sh
git add tests/native_support.py tests/conftest.py tests/unit/conftest.py tests/unit/test_native_support.py
git commit -m "test: parameterize native modes and share installed-origin guards"
```

---

### Task 2: Isolated fixture-wheel build helper and its failure contracts

**Files:**
- Create: `tests/build_native.py`, `tests/unit/test_build_native.py`.

**Interfaces:**
- Consumes: `native_support.check_versions`, `require_origin` from Task 1.
- Produces: `expected_versions(environ) -> dict[str, str]`; `new_run_dir(prefix: Path, repo: Path) -> Path`; `build_command(python: str, source: Path, run_dir: Path, pins: dict[str, str], pybind_dir: Path, eigen_dir: Path) -> list[str]`; `install_command(python: str, wheel: Path) -> list[str]`; `run_logged(command: list[str], *, cwd: Path, log: Path, env: dict[str, str], timeout: float = 600) -> None`; `audit_wheel(wheel: Path, package_source: Path) -> None`; `main() -> int`.
- CLI: `{envpython} tests/build_native.py` builds the adjacent fixture using that interpreter's installed tools. It never installs dependency packages itself.
- Required version environment variables: `STUBGEN_` + uppercased distribution name with `-` replaced by `_` + `_VERSION`, for `numpy`, `scipy`, `pybind11`, `cmake`, `ninja`, `scikit-build-core`, `cmeel`, `cmeel-eigen`.
- Persistent per-invocation evidence: `<sys.prefix>/tmp/native/run-*/evidence.json`, `build.log`, `install.log`, `wheel/*.whl`, `cmake/`. There is no cleanup operation and no shared source-tree build directory.

- [ ] **Step 1: Add real failure/path/payload tests before the helper exists.**

Create `tests/unit/test_build_native.py` with these tests; imports come from `build_native` and `importlib.machinery.EXTENSION_SUFFIXES`:

```python
import json
import os
import sys
import zipfile
from importlib.machinery import EXTENSION_SUFFIXES

import pytest

from build_native import (
    audit_wheel, build_command, expected_versions, install_command,
    new_run_dir, run_logged,
)

PINS = {"numpy": "2.2.6", "scipy": "1.15.3", "pybind11": "2.9.2",
        "cmake": "3.31.10", "ninja": "1.13.2", "scikit-build-core": "1.0.3",
        "cmeel": "0.59.0", "cmeel-eigen": "3.4.0.2"}


def test_explicit_versions_are_required():
    env = {"STUBGEN_" + k.upper().replace("-", "_") + "_VERSION": v for k, v in PINS.items()}
    assert expected_versions(env) == PINS
    del env["STUBGEN_NUMPY_VERSION"]
    with pytest.raises(RuntimeError, match="STUBGEN_NUMPY_VERSION"):
        expected_versions(env)


def test_run_directories_are_owned_unique_and_not_source(tmp_path):
    repo = tmp_path / "repo"
    prefix = tmp_path / "env"
    first = new_run_dir(prefix, repo)
    second = new_run_dir(prefix, repo)
    other = new_run_dir(tmp_path / "env-other", repo)
    assert first != second != other
    assert first.is_relative_to(prefix / "tmp/native")
    assert other.is_relative_to(tmp_path / "env-other/tmp/native")
    with pytest.raises(RuntimeError):
        new_run_dir(repo, repo)
    with pytest.raises(RuntimeError):
        new_run_dir(repo / "tests/py-demo", repo)
    linked = tmp_path / "linked-env"
    linked.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (linked / "tmp").symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError):
        new_run_dir(linked, repo)
    assert list(outside.iterdir()) == []


def test_commands_target_interpreter_tools_and_wheel_without_dependency_resolution(tmp_path):
    source, run = tmp_path / "fixture", tmp_path / "run"
    pb, eigen = tmp_path / "pb", tmp_path / "eigen"
    command = build_command("/env/bin/python", source, run, PINS, pb, eigen)
    assert command[:8] == ["uv", "build", "--wheel", "--no-build-isolation", "--no-cache", "--python", "/env/bin/python", "--out-dir"]
    assert f"cmake.define.pybind11_DIR={pb}" in command
    assert f"cmake.define.Eigen3_DIR={eigen}" in command
    assert "cmake.define.STUBGEN_PYBIND11_VERSION=2.9.2" in command
    assert "cmake.version===3.31.10" in command
    assert "ninja.version===1.13.2" in command
    assert f"build-dir={run / 'cmake'}" in command
    assert command[-1] == str(source)
    wheel = run / "wheel/demo.whl"
    assert install_command("/env/bin/python", wheel) == [
        "uv", "pip", "install", "--python", "/env/bin/python", "--no-deps",
        "--reinstall-package", "py-demo", "--no-cache", str(wheel),
    ]


@pytest.mark.parametrize("status", [0, 7])
def test_real_process_status_and_output_are_retained(tmp_path, status):
    command = [sys.executable, "-c", f"print('process-output'); raise SystemExit({status})"]
    log = tmp_path / "process.log"
    if status:
        with pytest.raises(RuntimeError, match="exit 7"):
            run_logged(command, cwd=tmp_path, log=log, env=dict(os.environ))
    else:
        run_logged(command, cwd=tmp_path, log=log, env=dict(os.environ))
    lines = log.read_text().splitlines()
    assert json.loads(lines[0]) == command
    assert lines[-1] == "process-output"


def test_timeout_and_log_creation_failure_are_errors(tmp_path):
    with pytest.raises(RuntimeError, match="timed out"):
        run_logged([sys.executable, "-c", "import time; time.sleep(2)"],
                   cwd=tmp_path, log=tmp_path / "timeout.log", env=dict(os.environ), timeout=0.05)
    assert (tmp_path / "timeout.log").is_file()
    blocked = tmp_path / "blocked.log"
    blocked.mkdir()
    sentinel = tmp_path / "ran"
    with pytest.raises(OSError):
        run_logged([sys.executable, "-c", f"from pathlib import Path; Path({str(sentinel)!r}).touch()"],
                   cwd=tmp_path, log=blocked, env=dict(os.environ))
    assert not sentinel.exists()


@pytest.mark.parametrize("extra", [None, "lib/libdemo.a", "include/demo/Foo.h", "build/lib/stale.py", "demo/unrelated.txt"])
def test_wheel_payload_is_exactly_package_extension_and_metadata(tmp_path, extra):
    package = tmp_path / "demo"
    package.mkdir()
    (package / "__init__.py").write_bytes(b"VALUE = 1\n")
    wheel = tmp_path / "fixture.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("demo/__init__.py", b"VALUE = 1\n")
        archive.writestr("demo/_bindings" + EXTENSION_SUFFIXES[0], b"test payload, not imported")
        archive.writestr("py_demo-0.0.0.dist-info/METADATA", b"Name: py-demo\n")
        if extra:
            archive.writestr(extra, b"unwanted")
    if extra:
        with pytest.raises(RuntimeError, match="payload"):
            audit_wheel(wheel, package)
    else:
        audit_wheel(wheel, package)
    (package / "__init__.py").write_bytes(b"VALUE = 2\n")
    with pytest.raises(RuntimeError):
        audit_wheel(wheel, package)
```

- [ ] **Step 2: Observe missing-helper failure, then implement the helper's core.**

Use the common isolated pytest command on this focused file. Create `tests/build_native.py` with stdlib imports only at import time (`hashlib`, `importlib.metadata`, `importlib.machinery`, `json`, `os`, `pathlib.Path`, `subprocess`, `sys`, `tempfile`, `zipfile`, and `native_support`). Its core is:

```python
import hashlib
import importlib.machinery
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from native_support import check_versions, require_origin

PACKAGES = ("numpy", "scipy", "pybind11", "cmake", "ninja", "scikit-build-core", "cmeel", "cmeel-eigen")


def expected_versions(environ):
    pins = {}
    for name in PACKAGES:
        key = "STUBGEN_" + name.upper().replace("-", "_") + "_VERSION"
        if not environ.get(key):
            raise RuntimeError(f"{key} must be set by tox")
        pins[name] = environ[key]
    return pins


def new_run_dir(prefix: Path, repo: Path) -> Path:
    prefix, repo = prefix.resolve(), repo.resolve()
    if repo.is_relative_to(prefix) or prefix.is_relative_to(repo / "tests"):
        raise RuntimeError("Native build prefix overlaps source roots")
    parent = prefix / "tmp/native"
    require_origin("native build directory", str(parent), prefix)
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=parent))


def build_command(python, source, run_dir, pins, pybind_dir, eigen_dir):
    command = ["uv", "build", "--wheel", "--no-build-isolation", "--no-cache",
               "--python", python, "--out-dir", str(run_dir / "wheel")]
    settings = {
        "build-dir": str(run_dir / "cmake"),
        "cmake.version": "==" + pins["cmake"],
        "ninja.version": "==" + pins["ninja"],
        "ninja.make-fallback": "false",
        "cmake.define.Python_EXECUTABLE": python,
        "cmake.define.pybind11_DIR": str(pybind_dir),
        "cmake.define.Eigen3_DIR": str(eigen_dir),
        "cmake.define.STUBGEN_PYBIND11_VERSION": pins["pybind11"],
    }
    for key, value in settings.items():
        command += ["--config-setting", f"{key}={value}"]
    return command + [str(source)]


def install_command(python, wheel):
    return ["uv", "pip", "install", "--python", python, "--no-deps",
            "--reinstall-package", "py-demo", "--no-cache", str(wheel)]


def run_logged(command, *, cwd, log, env, timeout=600):
    print(f"Running {command!r}; log: {log}", flush=True)
    try:
        with log.open("xb") as stream:
            stream.write((json.dumps(command) + "\n").encode())
            stream.flush()
            result = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Command timed out after {timeout}s; log: {log}; {command!r}") from exc
    if result.returncode:
        tail = "\n".join(log.read_text(errors="replace").splitlines()[-30:])
        raise RuntimeError(f"Command exit {result.returncode}; log: {log}; {command!r}\n{tail}")


def audit_wheel(wheel, package_source):
    expected = {"demo/" + p.relative_to(package_source).as_posix(): p.read_bytes()
                for p in package_source.rglob("*.py")}
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            not n.startswith(("demo/", "py_demo-0.0.0.dist-info/"))
            or n.endswith((".a", ".lib", ".h", ".hpp", ".pyc")) for n in names
        ):
            raise RuntimeError("Unexpected fixture wheel payload")
        actual = {n: archive.read(n) for n in names if n.endswith(".py")}
        extension_names = {"demo/_bindings" + suffix for suffix in importlib.machinery.EXTENSION_SUFFIXES}
        extensions = [n for n in names if n in extension_names]
        payload = {n for n in names if not n.startswith("py_demo-0.0.0.dist-info/")}
        if actual != expected or len(extensions) != 1 or payload != set(expected) | set(extensions):
            raise RuntimeError("Fixture wheel payload differs from source package/extension contract")
```

Use the following `main` flow, with `if __name__ == "__main__": raise SystemExit(main())`. It must not execute at import time:

```python
def main():
    repo = Path(__file__).resolve().parents[1]
    source = repo / "tests/py-demo"
    run_dir = None
    evidence = {"python": sys.executable, "prefix": sys.prefix, "phase": "prepare"}
    try:
        run_dir = new_run_dir(Path(sys.prefix), repo)
        print(f"Native fixture evidence: {run_dir}", flush=True)
        pins = expected_versions(os.environ)
        before = {name: importlib.metadata.version(name) for name in PACKAGES}
        evidence.update(pins=pins, before=before)
        check_versions(pins, before)
        for name in PACKAGES:
            location = importlib.metadata.distribution(name).locate_file("")
            require_origin(name, str(location), Path(sys.prefix))
        pybind_dir = Path(importlib.metadata.distribution("pybind11").locate_file("pybind11/share/cmake/pybind11"))
        eigen_dir = Path(importlib.metadata.distribution("cmeel-eigen").locate_file("cmeel.prefix/share/eigen3/cmake"))
        for name, path, config in (("pybind11", pybind_dir, "pybind11Config.cmake"),
                                   ("Eigen", eigen_dir, "Eigen3Config.cmake")):
            require_origin(name, str(path), Path(sys.prefix))
            if not (path / config).is_file():
                raise RuntimeError(f"Missing {name} CMake configuration: {path}")
        evidence.update(pins=pins, before=before, pybind_dir=str(pybind_dir), eigen_dir=str(eigen_dir))
        env = dict(os.environ)
        for key in list(env):
            if key.startswith("SKBUILD_") or key in ("CMAKE_ARGS", "CMAKE_PREFIX_PATH", "CMAKE_TOOLCHAIN_FILE"):
                env.pop(key)
        env["CMAKE_BUILD_PARALLEL_LEVEL"] = "2"
        evidence["phase"] = "build"
        (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        run_logged(build_command(sys.executable, source, run_dir, pins, pybind_dir, eigen_dir),
                   cwd=repo, log=run_dir / "build.log", env=env)
        wheels = list((run_dir / "wheel").glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"Expected one new fixture wheel, found {wheels}")
        wheel = wheels[0]
        evidence["phase"] = "wheel payload"
        audit_wheel(wheel, source / "demo")
        evidence.update(wheel=str(wheel), wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest())
        evidence["phase"] = "install"
        run_logged(install_command(sys.executable, wheel), cwd=repo,
                   log=run_dir / "install.log", env=env)
        after = {name: importlib.metadata.version(name) for name in PACKAGES}
        check_versions(pins, after)
        evidence.update(after=after, phase="complete")
        (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        return 0
    except (OSError, RuntimeError, ValueError, importlib.metadata.PackageNotFoundError, zipfile.BadZipFile) as exc:
        print(f"Native fixture {evidence['phase']} failed: {exc}", file=sys.stderr)
        if run_dir is not None:
            evidence["error"] = str(exc)
            try:
                (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
            except OSError as report_error:
                print(f"Could not save evidence: {report_error}", file=sys.stderr)
        return 1
```

This fresh-per-invocation design deliberately trades incremental reuse across tox runs for simpler freshness guarantees. It still performs exactly one fixture build per profile invocation and shares it across modes. Six-hundred-second native build/install limits are separate from, and do not alter, the existing snapshot subprocess limits.

- [ ] **Step 3: Verify behavioral failures, then commit the independently testable helper.**

Run focused/cumulative tests on 3.10/3.13. Confirm the real nonzero process, timeout, blocked log, unsafe path, drift, and unwanted payload checks fail for their intended reasons, not missing tools. Run this control with isolated uv supplying pytest, then rerun unpatched green. Do not invoke the helper against the old setuptools fixture yet: backend integration belongs to Task 3.

```python
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path("tests").resolve()))
import build_native
import pytest

original = build_native.install_command
with patch.object(build_native, "install_command", side_effect=lambda p, w: [a for a in original(p, w) if a != "--no-deps"]):
    code = pytest.main(["tests/unit/test_build_native.py::test_commands_target_interpreter_tools_and_wheel_without_dependency_resolution", "-q"])
assert code == pytest.ExitCode.TESTS_FAILED, code
```

```sh
git add tests/build_native.py tests/unit/test_build_native.py
git commit -m "test: add isolated fixture wheel builder with retained diagnostics"
```

---

### Task 3: Standard fixture backend, pinned dependencies, and 11 native tox profiles

**Files:**
- Modify: `tests/py-demo/pyproject.toml`, `tests/py-demo/bindings/CMakeLists.txt`, `tox.ini`.
- Delete: `tests/py-demo/setup.py`, `tests/install-demo-module.sh`.

**Interfaces:**
- Consumes Task 1 mode/provenance/runtime environment contracts and Task 2 build CLI.
- Produces the 11 native profile names from the spec, managed local generator wheels, `--installpkg` support, per-profile JUnit at `{envtmpdir}/native.xml`, and fixture evidence beneath `{envtmpdir}/native/`.
- Keeps the explicit compiler-free unit environment section's commands/dependencies/setenv overrides unchanged.

- [ ] **Step 1: Capture the missing-new-profile failure before changing configuration.**

```sh
env -u VIRTUAL_ENV uv run --no-project --isolated --with tox --with tox-uv \
  tox list -d --no-desc > "$E/task-3-before.txt"
```

Run this assertion separately and retain the expected `AssertionError`:

```python
from pathlib import Path
p = Path(".superpowers/sdd/2026-09-25-test-harness-phase-three/task-3-before.txt")
expected = ["py310-pb30", "py311-pb30", "py312-pb30", "py313-pb30",
            "py310-pb213", "py311-pb213", "py312-pb213", "py313-pb213",
            "py313-pb29", "py313-pb211", "py313-pb212"]
assert p.read_text().splitlines() == expected
```

The old list has 13 names with mode suffixes; this is the intended mismatch. Do not use an unknown CLI option or a failed native build as configuration red evidence.

- [ ] **Step 2: Replace fixture metadata and add component-scoped installation.**

Replace `tests/py-demo/pyproject.toml` with:

```toml
[build-system]
requires = ["scikit-build-core>=1.0,<2"]
build-backend = "scikit_build_core.build"

[project]
name = "py-demo"
version = "0.0.0"
description = "Demo package to test stub generation"
readme = "README.rst"
requires-python = ">=3.10"
authors = [{name = "Sergei Izmailov", email = "sergei.a.izmailov@gmail.com"}]
dependencies = ["numpy"]

[project.urls]
Repository = "https://github.com/sizmailov/pybind11-project-example"

[tool.scikit-build]
cmake.source-dir = "bindings"
wheel.packages = ["demo"]
install.components = ["python"]
```

In `tests/py-demo/bindings/CMakeLists.txt`, retain C++17, source glob, includes, library linkage, and the existing `add_subdirectory` relationship. Add explicit Eigen discovery before that subdirectory so its resolved version is available in the parent scope:

```cmake
find_package(Eigen3 3.4.0 EXACT CONFIG REQUIRED)
```

Replace its pybind11 discovery with:

```cmake
if(NOT DEFINED STUBGEN_PYBIND11_VERSION)
    message(FATAL_ERROR "Build the fixture through tox to select pybind11 explicitly")
endif()
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 ${STUBGEN_PYBIND11_VERSION} EXACT CONFIG REQUIRED)
message(STATUS "Fixture Python: ${Python_EXECUTABLE}")
message(STATUS "Fixture pybind11: ${pybind11_VERSION} at ${pybind11_DIR}")
message(STATUS "Fixture Eigen3: ${Eigen3_VERSION} at ${Eigen3_DIR}")
```

Append:

```cmake
install(TARGETS _bindings
    LIBRARY DESTINATION demo COMPONENT python
    RUNTIME DESTINATION demo COMPONENT python
)
```

Both artifact clauses need `COMPONENT python`. The backend installs only this component, excluding the demo library's existing default-component exports/headers without changing its C++ source or removing its standalone CMake capabilities.

Delete the fixture `setup.py` and old shell installer with the replacement local build route. The remaining CI caller is migrated in Task 4: this is an explicit transitional boundary, not a claim that the intermediate commit is CI-ready. Do not publish this partially integrated branch.

- [ ] **Step 3: Replace the native tox configuration, preserving unit overrides.**

Use this native configuration before the existing `[testenv:py{310,311,312,313}-unit]` section:

```ini
[tox]
requires = tox>=4
uv_mode = true
skip_missing_interpreters = false
env_list =
    py{310,311,312,313}-pb30
    py{310,311,312,313}-pb213
    py313-pb29
    py313-pb211
    py313-pb212

[testenv]
description = Check installed demo stubs and errors across configured NumPy modes
package = wheel
wheel_build_env = .pkg
setenv =
    PYTHONUNBUFFERED = 1
    STUBGEN_TEST_INSTALLED = 1
    STUBGEN_NUMPY_FORMATS = numpy-array-wrap-with-annotated
    py313-pb{213,30}: STUBGEN_NUMPY_FORMATS = numpy-array-wrap-with-annotated numpy-array-use-type-var
    pb29: PYBIND11_BRANCH = v2.9
    pb211: PYBIND11_BRANCH = v2.11
    pb212: PYBIND11_BRANCH = v2.12
    pb213: PYBIND11_BRANCH = v2.13
    pb30: PYBIND11_BRANCH = v3.0
    pb29: STUBGEN_PYBIND11_VERSION = 2.9.2
    pb211: STUBGEN_PYBIND11_VERSION = 2.11.2
    pb212: STUBGEN_PYBIND11_VERSION = 2.12.1
    pb213: STUBGEN_PYBIND11_VERSION = 2.13.6
    pb30: STUBGEN_PYBIND11_VERSION = 3.0.4
    pb29: STUBGEN_CMAKE_VERSION = 3.31.10
    pb{211,212}: STUBGEN_CMAKE_VERSION = 3.28.3
    pb{213,30}: STUBGEN_CMAKE_VERSION = 4.2.3
    py310: STUBGEN_NUMPY_VERSION = 2.2.6
    py311: STUBGEN_NUMPY_VERSION = 2.4.6
    py{312,313}: STUBGEN_NUMPY_VERSION = 2.5.3
    py310: STUBGEN_SCIPY_VERSION = 1.15.3
    py{311,312,313}: STUBGEN_SCIPY_VERSION = 1.17.1
    STUBGEN_CMEEL_VERSION = 0.59.0
    STUBGEN_CMEEL_EIGEN_VERSION = 3.4.0.2
    STUBGEN_SCIKIT_BUILD_CORE_VERSION = 1.0.3
    STUBGEN_NINJA_VERSION = 1.13.2
allowlist_externals = uv
deps =
    pytest>=8,<9
    typing_extensions>=4,<5
    cmeel=={env:STUBGEN_CMEEL_VERSION}
    cmeel-eigen=={env:STUBGEN_CMEEL_EIGEN_VERSION}
    numpy=={env:STUBGEN_NUMPY_VERSION}
    scipy=={env:STUBGEN_SCIPY_VERSION}
    pybind11=={env:STUBGEN_PYBIND11_VERSION}
    cmake=={env:STUBGEN_CMAKE_VERSION}
    scikit-build-core=={env:STUBGEN_SCIKIT_BUILD_CORE_VERSION}
    ninja=={env:STUBGEN_NINJA_VERSION}
commands_pre =
    {envpython} {toxinidir}/tests/build_native.py
commands =
    {envpython} -I -m pytest {toxinidir}/tests/test_snapshot_helpers.py {toxinidir}/tests/test_demo_stubs.py {toxinidir}/tests/test_demo_errors.py --pybind11-branch {env:PYBIND11_BRANCH} --artifacts-dir {envtmpdir}/pytest-artifacts --junitxml {envtmpdir}/native.xml --maxfail=0 {posargs}
```

Remove the old global `skipsdist` setting: native tox now uses its wheel-package mechanism. The unit section still explicitly uses `package = skip` and its original uv installation command. Do not accidentally introduce native build dependencies or precommands there.

Native profile names deliberately encode the interpreter that tox infers. Do not override `base_python` independently: CI derives its interpreter from this naming contract. The resolved configuration check below enforces agreement.

- [ ] **Step 4: Inspect resolution, then evaluate the entire real native matrix.**

Use `tox config` to verify all 11 environments' resolved `deps`, `set_env`, `base_python`, package mode, and commands, plus one unit environment's complete override. Confirm NumPy modes and exact pin tables independently, not by comparing a function with itself.

First build `py313-pb29` and `py313-pb30` serially to exercise the oldest and newest families. If either fails, investigate and stop rather than silently selecting another backend/tool version. Then run all profiles with fresh tox environments using the audit:

```sh
python "$E/audit_native.py" --label local-fresh -- \
  uv run --no-project --isolated --with tox --with tox-uv tox -r
```

Expected: 11 profile successes; nine profiles have 99 tests and the two dual-mode profiles have 101 tests, since only the existing 97 harness self-tests are selected natively. Both native test functions appear for every configured mode. New support tests run through the separate compiler-free selection. Record fixture wheel paths and `evidence.json`, inspect their payloads, CMake dependency locations, and unchanged before/after runtime pins.

Run the existing four unit tox environments and cumulative source checks. Exercise `tox -e py313-pb30 -- --numpy-format numpy-array-use-type-var -k demo_stubs` as an explicitly filtered debugging check, separately from unfiltered acceptance.

- [ ] **Step 5: Review source/reference preservation and commit the integrated local runner.**

Confirm no old installer callers remain in tox. CI still needs migration in Task 4 and is not claimed operational at this intermediate commit. No native C++/Python fixtures or references should differ.

```sh
git add tox.ini tests/py-demo/pyproject.toml tests/py-demo/bindings/CMakeLists.txt tests/py-demo/setup.py tests/install-demo-module.sh
git commit -m "test: build pinned native fixtures once per tox profile"
```

---

### Task 4: Derived CI matrix and the supplied-wheel execution path

**Files:**
- Create: `tests/native_matrix.py`, `tests/unit/test_native_matrix.py`.
- Modify: `.github/workflows/ci.yml`.

**Interfaces:**
- Consumes the expanded default native names from `tox list -d --no-desc`; consumes Task 3's `--installpkg` route, naming contract, and artifact locations.
- Produces `matrix_from_names(names: list[str]) -> dict[str, list[dict[str, str]]]`, returning `{"include": [{"env": "py313-pb30", "python": "3.13"}]}` for one input.
- CLI: `python tests/native_matrix.py DEFAULT_NAMES_FILE` emits one compact JSON line to stdout; invalid input returns nonzero and reports the error on stderr.
- CI build-job output `native-matrix` feeds `tests.strategy.matrix`; publication continues to depend on the existing `tests` job ID.

- [ ] **Step 1: Write the independent inventory and invalid-input tests.**

```python
import json
from pathlib import Path
import subprocess
import sys

import pytest

from native_matrix import matrix_from_names

EXPECTED_NAMES = [
    "py310-pb30", "py311-pb30", "py312-pb30", "py313-pb30",
    "py310-pb213", "py311-pb213", "py312-pb213", "py313-pb213",
    "py313-pb29", "py313-pb211", "py313-pb212",
]


def test_explicit_profile_inventory_and_interpreters():
    matrix = matrix_from_names(EXPECTED_NAMES)
    assert matrix == {"include": [
        {"env": "py310-pb30", "python": "3.10"},
        {"env": "py311-pb30", "python": "3.11"},
        {"env": "py312-pb30", "python": "3.12"},
        {"env": "py313-pb30", "python": "3.13"},
        {"env": "py310-pb213", "python": "3.10"},
        {"env": "py311-pb213", "python": "3.11"},
        {"env": "py312-pb213", "python": "3.12"},
        {"env": "py313-pb213", "python": "3.13"},
        {"env": "py313-pb29", "python": "3.13"},
        {"env": "py313-pb211", "python": "3.13"},
        {"env": "py313-pb212", "python": "3.13"},
    ]}


@pytest.mark.parametrize("names", [[], ["py313-pb30"] * 2, ["py313-unit"],
    ["py39-pb30"], ["py313-pb99"], ["py313-pb30-naa"], ["py313-pb300"],
    ["py313-pb209"], [""], [" py313-pb30"]])
def test_rejects_missing_duplicate_or_unsupported_profiles(names):
    with pytest.raises(ValueError):
        matrix_from_names(names)


def test_cli_json_and_nonzero_failure(tmp_path):
    script = Path(__file__).resolve().parents[1] / "native_matrix.py"
    names = tmp_path / "names.txt"
    names.write_text("py313-pb30\n")
    result = subprocess.run([sys.executable, str(script), str(names)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"include": [{"env": "py313-pb30", "python": "3.13"}]}
    names.write_text("py313-pb30\npy313-pb30\n")
    result = subprocess.run([sys.executable, str(script), str(names)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert result.stdout == ""
    assert "Duplicate" in result.stderr
```

- [ ] **Step 2: Observe missing-adapter failure, then implement the small translator.**

```python
import argparse
import json
from pathlib import Path
import re
import sys

from snapshot_helpers import BRANCHES


def matrix_from_names(names):
    if not names:
        raise ValueError("No default native environments")
    if len(names) != len(set(names)):
        raise ValueError("Duplicate native environments")
    rows = []
    for name in names:
        match = re.fullmatch(r"py(3)(1[0-3])-pb([23])(0|[1-9]\d?)", name)
        if match is None or f"v{match[3]}.{int(match[4])}" not in BRANCHES:
            raise ValueError(f"Unsupported native environment: {name!r}")
        rows.append({"env": name, "python": f"{match[1]}.{match[2]}"})
    return {"include": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("names_file", type=Path)
    args = parser.parse_args()
    try:
        matrix = matrix_from_names(args.names_file.read_text().splitlines())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

The regex validates the approved naming schema/interpreter range; `BRANCHES` is the existing reference-series vocabulary. Neither defines the execution list or duplicates dependency pins. Do not parse raw tox brace syntax or add a tox plugin dependency to the adapter/tests.

- [ ] **Step 3: Validate the actual tox-derived inventory before wiring CI.**

```sh
env -u VIRTUAL_ENV uv run --no-project --isolated --with tox --with tox-uv \
  tox list -d --no-desc > "$E/default-native.txt"
python tests/native_matrix.py "$E/default-native.txt" > "$E/native-matrix.json"
env -u VIRTUAL_ENV uv run --no-project --isolated --with 'tox==4.64.2' --with 'tox-uv==1.36.0' \
  tox config --format json -k env_name base_python set_env -o "$E/resolved-native.json"
```

Use the following independent check. Tox's resolved configuration can include its packaging environment; only the explicit expected native names are part of the matrix.

```python
import json
from pathlib import Path
E = Path(".superpowers/sdd/2026-09-25-test-harness-phase-three")
expected = ["py310-pb30", "py311-pb30", "py312-pb30", "py313-pb30",
            "py310-pb213", "py311-pb213", "py312-pb213", "py313-pb213",
            "py313-pb29", "py313-pb211", "py313-pb212"]
rows = json.loads((E / "native-matrix.json").read_text())["include"]
resolved = json.loads((E / "resolved-native.json").read_text())["env"]
assert [r["env"] for r in rows] == expected
cases = []
for row in rows:
    item = resolved[row["env"]]
    assert item["base_python"] == [row["env"].split("-")[0]]
    env = item["set_env"]
    modes = env["STUBGEN_NUMPY_FORMATS"].split()
    wanted = ["numpy-array-wrap-with-annotated"]
    if row["env"] in ("py313-pb30", "py313-pb213"):
        wanted += ["numpy-array-use-type-var"]
    assert modes == wanted
    cases.extend((row["python"], env["PYBIND11_BRANCH"], mode) for mode in modes)
assert len(cases) == len(set(cases)) == 13
```

Also run list/translation with a fresh `--workdir` and `UV_PYTHON_DOWNLOADS=never`. It must not create fixture environments, compile code, or require discovering every matrix interpreter. The list command, unlike full `tox config`, does not materialize packaging/run environments.

- [ ] **Step 4: Replace only native CI orchestration and expose the derived matrix.**

Add this output to the existing `build` job:

```yaml
    outputs:
      native-matrix: ${{ steps.native-matrix.outputs.matrix }}
```

After its existing uv setup, add:

```yaml
      - name: Derive native test matrix from tox
        id: native-matrix
        shell: bash
        run: |
          set -euo pipefail
          uv run --no-project --isolated --with tox --with tox-uv \
            tox list -d --no-desc > "$RUNNER_TEMP/native-envs.txt"
          matrix=$(python tests/native_matrix.py "$RUNNER_TEMP/native-envs.txt")
          printf 'matrix=%s\n' "$matrix" >> "$GITHUB_OUTPUT"
```

Replace the existing `tests` job, not the unit/gemmi/check/build-publication logic, with:

```yaml
  tests:
    name: "Native tests • ${{ matrix.env }}"
    runs-on: ubuntu-latest
    needs: [build]
    strategy:
      fail-fast: false
      matrix: ${{ fromJSON(needs.build.outputs.native-matrix) }}
    steps:
      - uses: actions/checkout@v5
      - uses: actions/download-artifact@v6
        with:
          name: dist
          path: dist
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - uses: astral-sh/setup-uv@v7
      - name: Test supplied wheel through shared tox profile
        shell: bash
        env:
          TOX_PROFILE: ${{ matrix.env }}
        run: |
          set -euo pipefail
          shopt -s nullglob
          wheels=(dist/*.whl)
          test "${#wheels[@]}" -eq 1
          uv run --no-project --isolated --with tox --with tox-uv \
            tox -e "$TOX_PROFILE" --installpkg "${wheels[0]}"
      - name: Archive native build and test diagnostics
        uses: actions/upload-artifact@v6
        if: failure()
        with:
          name: "${{ matrix.env }}-diagnostics"
          include-hidden-files: true
          path: |
            .tox/${{ matrix.env }}/log/
            .tox/${{ matrix.env }}/tmp/native/**/evidence.json
            .tox/${{ matrix.env }}/tmp/native/**/*.log
            .tox/${{ matrix.env }}/tmp/native/**/CMakeCache.txt
            .tox/${{ matrix.env }}/tmp/native/**/CMakeConfigureLog.yaml
            .tox/${{ matrix.env }}/tmp/pytest-artifacts/
            .tox/${{ matrix.env }}/tmp/native.xml
          retention-days: 30
          if-no-files-found: ignore
```

`include-hidden-files` is needed for `.tox` artifacts. Restrict paths to logs/evidence, not whole environments or fixture wheels. The old native-only annotation installation step is removed with the duplicate setup route; pytest/JUnit diagnostics remain available. No changes to gemmi's annotation step, release credentials, or publication conditions.

- [ ] **Step 5: Exercise the supplied-wheel route locally and commit.**

Build the generator wheel from a clean tracked-source archive (including Task 3's committed tree). Use fresh directory names for later repetitions:

```sh
E="$(pwd)/.superpowers/sdd/2026-09-25-test-harness-phase-three"
mkdir "$E/clean-source" "$E/dist"
git archive --format=tar HEAD -o "$E/clean-source.tar"
tar -xf "$E/clean-source.tar" -C "$E/clean-source"
(cd "$E/clean-source" && env -u VIRTUAL_ENV uv build --wheel --out-dir "$E/dist")
WHEEL=$(python - "$E/dist" <<'PY'
from pathlib import Path
import sys
wheel, = Path(sys.argv[1]).glob('*.whl')
print(wheel.resolve())
PY
)
printf '%s\n' "$WHEEL" > "$E/generator-wheel.path"
```

Record its SHA-256 and verify its production files match the current tracked production tree. Do not change generator package discovery or clean unrelated worktree build output.

Run the CI command locally across all 11 profiles, with the batch audit and an absolute wheel path:

```sh
python "$E/audit_native.py" --label supplied-wheel -- \
  uv run --no-project --isolated --with tox --with tox-uv \
  tox --installpkg "$WHEEL"
```

Inspect tox package-install records: they must name the supplied wheel and must not build/reinstall the generator from `.`. Distinguish expected fixture-wheel builds from a forbidden replacement generator build. Confirm installed origin within pytest. Save this artifact-identity probe as `$E/check_supplied_wheel.py`, then run it with each of the 11 native interpreters using `-I`, passing the absolute `$WHEEL` path:

```python
import hashlib
from importlib.metadata import distribution
import json
from pathlib import Path
import sys
import zipfile

import pybind11_stubgen

wheel = Path(sys.argv[1])
digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
origin = Path(pybind11_stubgen.__file__).resolve()
assert origin.is_relative_to(Path(sys.prefix).resolve()), origin
installed = origin.parent.parent
with zipfile.ZipFile(wheel) as archive:
    assert not any(n.startswith('build/') for n in archive.namelist())
    names = {n for n in archive.namelist() if n.startswith('pybind11_stubgen/') and n.endswith('.py')}
    actual = {p.relative_to(installed).as_posix() for p in origin.parent.rglob('*.py')}
    assert names == actual
    for name in names:
        assert archive.read(name) == (installed / name).read_bytes(), name
info = json.loads(distribution('pybind11-stubgen').read_text('direct_url.json'))
archive_info = info['archive_info']
assert (archive_info.get('hashes', {}).get('sha256') == digest
        or archive_info.get('hash') == 'sha256=' + digest), info
print(json.dumps({'origin': str(origin), 'wheel_sha256': digest, 'direct_url': info}))
```

If the installer records an unexpected provenance schema, investigate rather than removing the artifact identity check; origin and equal source files alone are insufficient. Run focused and cumulative tests on 3.10/3.13. Run this mutation with isolated uv supplying pytest, then restore an unpatched green run. Run YAML/all applicable hooks.

```python
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path("tests").resolve()))
import native_matrix
import pytest

original = native_matrix.matrix_from_names

def wrong_interpreter(names):
    result = original(names)
    for row in result["include"]:
        row["python"] = "3.13"
    return result

with patch.object(native_matrix, "matrix_from_names", side_effect=wrong_interpreter):
    code = pytest.main(["tests/unit/test_native_matrix.py::test_explicit_profile_inventory_and_interpreters", "-q"])
assert code == pytest.ExitCode.TESTS_FAILED, code
```

```sh
git add tests/native_matrix.py tests/unit/test_native_matrix.py .github/workflows/ci.yml
git commit -m "test: derive native CI jobs from tox and consume the built wheel"
```

---

### Task 5: User documentation and full acceptance audit

**Files:**
- Modify: `tests/README.md`.
- Evidence only: this plan's ignored workspace, including disposable source copies and final report.

**Interfaces:**
- Consumes all preceding CLI/environment interfaces, wheel evidence, JUnit case properties, and audit helper.
- Produces documented workflows and a final local acceptance report; no new runtime/helper API.

- [ ] **Step 1: Update documentation alongside verified commands.**

Replace the old native prerequisites/commands/suffix explanation with this content, retaining the existing snapshot update safeguards and compiler-free instructions:

```markdown
Native checks require Python 3.10–3.13 for the full matrix, uv, tox with tox-uv,
and a C++17 compiler. Tox installs pinned pybind11 distributions, CMake,
scikit-build-core, Ninja, cmeel/Eigen, NumPy, and SciPy. It no longer clones
pybind11 or builds/installs demo-lib separately. Normalization still uses the
existing pinned Ruff tool.

The default matrix has 11 native build profiles covering the same 13 cases.
For Python 3.13 with pybind11 2.13 or 3.0, both NumPy rendering modes share one
installed fixture. Other profiles use annotated arrays. The old `-naa` and
`-nutv` tox suffixes are replaced by a mode selection within the grouped profile.

    tox -e py313-pb30
    tox -e py313-pb30 -- -k demo_errors
    tox -e py313-pb30 -- --numpy-format numpy-array-use-type-var
    tox
    tox -e py313-pb30 --installpkg dist/pybind11_stubgen-3.0.0-py3-none-any.whl

Tox's selected pybind11/CMake and runtime dependency versions are authoritative
for native checks both locally and in CI. NumPy/SciPy are pinned to the observed
phase-two runtime versions; fixture installation cannot replace them. The root
development dependency group is not the native test environment.

Local native tox installs a generator wheel. CI supplies its existing build
artifact through the same runner. Installed origins are checked inside pytest.
After a matching tox run, a single check can be repeated without rebuilding:

    STUBGEN_TEST_INSTALLED=1 .tox/py313-pb30/bin/python -I -m pytest \
      tests/test_demo_stubs.py --pybind11-branch v3.0 \
      --numpy-format numpy-array-use-type-var

That direct rerun checks installed origins and snapshots but does not reconstruct
tox's dependency-pin environment. Rerun tox after generator/fixture changes or
to validate the configured pins and rebuild the fixture.

Each profile owns its build directories and diagnostics. Checks can use bounded
parallel tox execution after the isolation acceptance test; they do not require
pytest workers. Reference updates remain explicit and serial:

    tox -e py313-pb30 -- --numpy-format numpy-array-wrap-with-annotated --update-snapshots
    git diff -- tests/stubs tests/errors

Do not update shared references concurrently. Existing aliases and per-test,
nontransactional update semantics are unchanged. A broken build or generator
command is not eligible to become a new expectation.

Build/install logs and fixture provenance are under
`.tox/<profile>/tmp/native/run-*/`; tox command logs are under
`.tox/<profile>/log/`. Pytest diagnostics remain in the environment's
`tmp/pytest-artifacts/`, with distinct case/check/run directories. The native
JUnit report is `tmp/native.xml`. CI's failure upload includes these scoped
logs and reports, not entire virtual environments.
```

Explain that the supplied-wheel example assumes the current generator wheel has already been built in `dist/`; use the actual filename when the project version changes. Update the earlier README sentence that says the default list still contains 13 environments. Keep the ordinary-Python positional-only bug and dirty-tree generator packaging issue outside this migration; replace the phase-two-only closing policy with the continuing test-infrastructure rule against hiding production bugs through expectation changes.

- [ ] **Step 2: Run the four-version compiler-free acceptance independently of native environments.**

Run all four explicit unit tox environments and fresh source/wheel checks using pytest-only environments. A concrete fresh-environment loop is:

```sh
unset VIRTUAL_ENV STUBGEN_TEST_INSTALLED STUBGEN_NUMPY_VERSION STUBGEN_SCIPY_VERSION STUBGEN_NUMPY_FORMATS
for version in 3.10 3.11 3.12 3.13; do
  uv venv --python "$version" "$E/source-$version"
  uv pip install --python "$E/source-$version/bin/python" 'pytest>=8,<9'
  "$E/source-$version/bin/python" -c 'from importlib.util import find_spec; assert all(find_spec(n) is None for n in ("demo", "numpy", "scipy", "cmake", "scikit_build_core"))'
  "$E/source-$version/bin/python" -c 'from pathlib import Path; import pybind11_stubgen; assert Path(pybind11_stubgen.__file__).resolve() == Path("pybind11_stubgen/__init__.py").resolve()'
  "$E/source-$version/bin/python" -m pytest tests/unit tests/test_snapshot_helpers.py -q
  uv venv --python "$version" "$E/wheel-$version"
  uv pip install --python "$E/wheel-$version/bin/python" 'pytest>=8,<9' "$WHEEL"
  "$E/wheel-$version/bin/python" -I -c 'from importlib.util import find_spec; assert all(find_spec(n) is None for n in ("demo", "numpy", "scipy", "cmake", "scikit_build_core"))'
  STUBGEN_TEST_INSTALLED=1 "$E/wheel-$version/bin/python" -I -m pytest tests/unit tests/test_snapshot_helpers.py -q
done
uv run --no-project --isolated --with tox --with tox-uv tox \
  -e py310-unit,py311-unit,py312-unit,py313-unit
```

Build `$WHEEL` from the final tracked implementation first, not from a stale task snapshot. Reuse Task 4's archive/build procedure with new `final-source`/`final-dist` directories and update `generator-wheel.path`. Test the installed guard's red/green behavior on a narrow selection: from the checkout, run the fresh wheel environment's Python without `-I`, with `STUBGEN_TEST_INSTALLED=1`, on `tests/unit/test_pipeline.py::test_python_module_pipeline`; require a setup error naming the checkout origin. Restore `-I` and require a passing test, then run the full unpatched selection.

- [ ] **Step 3: Re-run native acceptance and inspect exact cases, reuse, and pins.**

Use unique audit labels for an unfiltered local-wheel run and a supplied-wheel run on the final tree. Read all 11 JUnit files and compare to the independently expected native inventory. A checker core is:

```python
from pathlib import Path
import xml.etree.ElementTree as ET

profiles = ["py310-pb30", "py311-pb30", "py312-pb30", "py313-pb30",
            "py310-pb213", "py311-pb213", "py312-pb213", "py313-pb213",
            "py313-pb29", "py313-pb211", "py313-pb212"]
A, T = "numpy-array-wrap-with-annotated", "numpy-array-use-type-var"
seen = []
for profile in profiles:
    tree = ET.parse(Path(".tox") / profile / "tmp/native.xml")
    cases = tree.findall(".//testcase")
    assert not any(c.find(tag) is not None for c in cases for tag in ("failure", "error", "skipped"))
    native = [c.attrib["name"] for c in cases if c.attrib["name"].startswith("test_demo_")]
    modes = [A, T] if profile in ("py313-pb30", "py313-pb213") else [A]
    expected = [f"{test}[{mode}]" for test in ("test_demo_stubs", "test_demo_errors") for mode in modes]
    assert sorted(native) == sorted(expected), (profile, native)
    properties = {p.attrib["name"]: p.attrib["value"] for p in tree.findall(".//property")}
    assert Path(properties["native_extension"]).resolve().is_relative_to((Path(".tox") / profile).resolve())
    assert len(properties["native_extension_sha256"]) == 64
    seen.extend((profile, mode) for mode in modes)
assert len(seen) == len(set(seen)) == 13
```

Sorting here compares case inventories only; never sort diagnostic stderr or expected output. Check the JUnit runtime properties against the explicit version table. For each dual-mode profile, correlate its single fixture build command/evidence record with both pytest mode IDs and the unchanged extension digest. Check `evidence.json` before/after versions, CMake's selected version/paths, and the audited fixture payload.

Use `--result-json` on tox verification runs when useful to retain the package installation command list. Verify installed generator files against `$WHEEL` with `zipfile`/hashes inside each environment; do not infer artifact identity solely from a site-packages path.

- [ ] **Step 4: Demonstrate bounded parallel isolation and sibling-source freshness.**

Run two different profiles concurrently (two tox workers, two compiler jobs per build), using the supplied generator wheel and the audit:

```sh
python "$E/audit_native.py" --label parallel -- \
  uv run --no-project --isolated --with tox --with tox-uv \
  tox -p 2 -e py310-pb213,py313-pb30 --installpkg "$WHEEL"
```

Verify both complete case inventories and disjoint build/evidence paths. Never add `--update-snapshots` to parallel verification.

For freshness, extract another clean tracked archive into a new directory beneath `$E`. Run `py313-pb30` there using `$WHEEL`; save its build evidence. Append this line to that disposable copy's `tests/demo-lib/include/demo/Foo.h`:

```cpp
#error PHASE_THREE_SIBLING_REBUILD_CONTROL
```

Run the same tox command again. Require nonzero build failure containing that marker, a new retained build log, and no subsequent pytest command using the previously installed extension. Restore the original header bytes in that disposable copy and require a green rerun. Never modify the tracked fixture in the main worktree for this probe. This is behavioral proof against stale frontend wheel caching and stale CMake inputs, not merely a command-argument assertion.

- [ ] **Step 5: Verify failure and preservation boundaries, then commit documentation.**

Run the Task 1 grouped-mode failure regression, Task 2 process/log/timeout/payload tests, and drift/origin negative controls on the final code. For an actual native pytest drift control, run these commands separately, recording the first as an expected failure rather than letting shell fail-fast conceal the restored run:

```sh
STUBGEN_TEST_INSTALLED=1 STUBGEN_NUMPY_VERSION=0.0.0 STUBGEN_SCIPY_VERSION=1.17.1 \
  .tox/py313-pb30/bin/python -I -m pytest tests/test_demo_stubs.py \
  --pybind11-branch v3.0 --numpy-format numpy-array-wrap-with-annotated -q
STUBGEN_TEST_INSTALLED=1 STUBGEN_NUMPY_VERSION=2.5.3 STUBGEN_SCIPY_VERSION=1.17.1 \
  .tox/py313-pb30/bin/python -I -m pytest tests/test_demo_stubs.py \
  --pybind11-branch v3.0 --numpy-format numpy-array-wrap-with-annotated -q
```

Require a setup error naming NumPy for the first and a green test for the second. No native rebuild is needed for this isolated control.

Audit protected paths against `807e7e4`:

```sh
git diff --exit-code 807e7e4 -- pybind11_stubgen tests/py-demo/demo \
  tests/demo-lib tests/py-demo/bindings/src \
  tests/stubs tests/errors tests/snapshot_helpers.py tests/test_snapshot_helpers.py \
  tests/test_demo_stubs.py tests/test_demo_errors.py pyproject.toml uv.lock
uv lock --check
uv run pre-commit run --all-files
git diff --check
```

Review the remaining CMake/fixture metadata/tox/CI changes manually against the spec. Confirm gemmi, release triggers/permissions/conditions, root package discovery, and all snapshot aliases are unchanged. No old installer calls or old native environment examples should remain in active runner/docs files (historical design/plan documents may retain them).

Write a final report containing exact commits, command exit statuses, case inventories, observed versions/build locations, wheel hashes/origins, reference/index audit results, negative-control failures and restored greens, plus the explicitly deferred remote acceptance. Retain logs for both early build failures and ordinary pytest failures. Do not claim actual GitHub upload behavior from YAML validation.

```sh
git add tests/README.md
git commit -m "docs: document grouped native tests and verified dependency policy"
```

## Spec coverage and final review gate

| Spec contract | Implementation/verification task |
| --- | --- |
| 11 profiles / 13 cases; single-mode override; continue after ordinary failure | Tasks 1, 3, 4, 5 |
| Same-process generator origin and installed demo/extension provenance | Tasks 1, 5 |
| Explicit pybind11/CMake/Eigen/backend/runtime selections, no dependency replacement | Tasks 2, 3, 5 |
| Standard fixture wheel, no redundant standalone demo build, correct payload | Tasks 2, 3, 5 |
| Per-environment build paths, actual shared fixture, source freshness, parallel safety | Tasks 1, 2, 3, 5 |
| Authoritative tox matrix; externally supplied generator wheel; retained early/late logs | Tasks 3, 4, 5 |
| Compiler-free independence and sensitive orchestration tests | Tasks 1, 2, 4, 5 |
| Immutable references/index during checks, production/demo source preservation | Baseline and Tasks 3–5 |
| Existing unit/gemmi/release/root packaging boundaries | Tasks 3–5 and final cumulative review |
| Local-only acceptance, separate bugs, documented limits | Every task report and Task 5 |

Request a final cumulative review against the approved spec after all five task gates. Re-run affected acceptance after any fixes; do not assume earlier green runs cover later edits. Keep the existing branch/worktree and perform no integration or remote actions without a new user decision.
