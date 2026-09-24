# Phase-One Pytest Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace mutating shell snapshot checks with independently tested pytest checks and explicit reference updates, without changing native builds or compatibility coverage.

**Architecture:** A standard-library-only helper module handles snapshot paths, byte comparisons, guarded updates, subprocess diagnostics, normalization, and artifact retention. Thin pytest fixtures select an existing profile, and two integration tests invoke the installed generator outside the checkout. Tox and CI retain their environments and build steps, changing only how checks run.

**Tech Stack:** Python >=3.10, pytest >=8,<9, pathlib, subprocess, difflib, existing uv/tox tooling, existing Ruff pre-commit pin, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-24-test-harness-phase-one-design.md` (approved in chat).

## Global Constraints

- "No production stub-generation behavior is changed."
- "Keep `tests/install-demo-module.sh`, the demo sources, and their build configuration unchanged."
- "Preserve all 13 existing integration configurations."
- "Comparison never consults Git or `HEAD`."
- "Compare normalized bytes; decode text for readable diffs."
- "Never stage or commit anything." This applies to the test harness; implementation commits below are developer actions.
- "Apply a 300-second timeout to the generator and each formatting subprocess."
- "Run updates serially."
- "CI runs in check mode only."
- "A test with failed generation or normalization must not update its own references."
- Preserve directory aliases and the current Ruff/address normalization policy; do not deduplicate snapshots.
- Require explicit native-test configuration and an installed demo; never silently skip native checks or build at collection time.
- Use `sys.executable -I -m pybind11_stubgen` from temporary directories. Never use `uv run` inside subprocess helpers or CI after wheel installation.
- Keep the `gemmi` job, existing matrix/CMake choices, and native dependency versions unchanged.
- Harness self-tests require pytest and the standard library only, not the demo, Git, Ruff, or a compiler.
- Until Task 6 rewires tox, **do not run the old tox commands or shell checkers against real reference trees**: they mutate and stage snapshots.
- Code blocks below are implementation instructions, not changes already made or tests already run.

---

## Execution preparation and file map

At execution time, use `superpowers:using-git-worktrees` to establish an isolated workspace. Read the spec, this plan, and any repository instructions there. Record initial Git status and do not overwrite existing developer changes. Do not run the legacy test suite as a baseline; use the compiler-free commands below until its callers are replaced.

| File | Boundary |
| --- | --- |
| `tests/snapshot_helpers.py` | Small functions for filesystem snapshots, subprocesses, normalization, artifacts, and profile metadata. No production-module imports or pytest dependency. |
| `tests/test_snapshot_helpers.py` | Synthetic regression tests for each helper and the integration-test orchestration. |
| `tests/conftest.py` | Four CLI options and lazy fixtures; no native imports, subprocesses, or builds during collection. |
| `tests/test_demo_stubs.py` | Successful generator contract, Ruff normalization, then compare/update. |
| `tests/test_demo_errors.py` | Fatal-error contract, address normalization, then compare/update one stderr file. |
| `pyproject.toml`, `uv.lock` | pytest dependency and test discovery settings. |
| `tox.ini` | Existing environment matrix/build plus pytest invocation and argument forwarding. |
| `.github/workflows/ci.yml` | Existing wheel/native setup plus pytest and artifact upload. |
| `README.md`, `tests/README.md` | Short contributor entry point and complete testing guide. |
| Two legacy `tests/check-demo-*.sh` scripts | Remove only after callers migrate. |

Do not create `tests/__init__.py`. Use pytest's default import mode so sibling test modules can import `snapshot_helpers`. The generator subprocess is isolated from these test-module imports.

Tasks 1–4 grow the shared helper in small, reviewed increments; merge each new import into its import block rather than duplicating imports. Keep subprocesses confined to `run_command`; filesystem comparisons must never invoke Git.

## Task 1: Establish compiler-free, read-only snapshot comparisons

**Files:**
- Create: `tests/snapshot_helpers.py`, `tests/test_snapshot_helpers.py`.
- Modify: `pyproject.toml` (`dependency-groups.dev`, new pytest configuration), `uv.lock`.

**Interfaces:**
- Consumes: Python standard library, pytest.
- Produces: `HarnessError(AssertionError)`, `Snapshot = dict[str, bytes]`.
- Produces: `relative_file(name: str) -> Path`, `resolve_profile(root: Path, profile: Path) -> Path`.
- Produces: `read_tree(root: Path) -> Snapshot`, `diff_tree(expected: Snapshot, actual: Snapshot) -> str`.
- Test utility: `write_files(root: Path, files: dict[str, bytes]) -> None`.

- [ ] **Step 1: Add pytest and explicit test discovery.** Add `"pytest>=8,<9"` to the existing dev group; preserve all existing dependencies. Append:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
```

Run `uv lock` without `--upgrade`; review the lock diff for unrelated dependency changes. Use this project-independent command for all compiler-free red/green cycles below:

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py -q
```

- [ ] **Step 2: Write the comparison/path tests before the helper exists.** Create `tests/test_snapshot_helpers.py`:

```python
from pathlib import Path

import pytest

import snapshot_helpers as h


def write_files(root: Path, files: dict[str, bytes]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def test_diff_detects_changed_missing_and_unexpected_files():
    expected = {"nested/a file.pyi": b"old\n", "gone.pyi": b"x\n"}
    actual = {"nested/a file.pyi": b"new\n", "extra.pyi": b"y\n"}
    assert h.diff_tree(expected, expected) == ""
    difference = h.diff_tree(expected, actual)
    assert "Changed: nested/a file.pyi" in difference
    assert "Missing: gone.pyi" in difference
    assert "Unexpected: extra.pyi" in difference
    assert "-old" in difference and "+new" in difference
    assert h.diff_tree({"x": b"x\r\n"}, {"x": b"x\n"})


def test_read_tree_preserves_bytes_and_rejects_links(tmp_path):
    write_files(tmp_path, {"sub/a.pyi": b"\xff\r\n"})
    assert h.read_tree(tmp_path) == {"sub/a.pyi": b"\xff\r\n"}
    assert h.read_tree(tmp_path / "absent") == {}
    (tmp_path / "linked.pyi").symlink_to("sub/a.pyi")
    with pytest.raises(h.HarnessError, match="symlink"):
        h.read_tree(tmp_path)


def test_profile_aliases_resolve_but_escapes_and_missing_profiles_fail(tmp_path):
    refs = tmp_path / "refs"
    write_files(refs / "real", {"x.pyi": b"x"})
    (refs / "alias").symlink_to("real", target_is_directory=True)
    (refs / "chain").symlink_to("alias", target_is_directory=True)
    assert h.resolve_profile(refs, Path("chain")) == refs / "real"
    outside = tmp_path / "outside"
    outside.mkdir()
    (refs / "escape").symlink_to(outside, target_is_directory=True)
    for name in ("escape", "missing", "../outside"):
        with pytest.raises(h.HarnessError):
            h.resolve_profile(refs, Path(name))


@pytest.mark.parametrize("name", ["", ".", "..", "../x", "/x", "a/../x", "a\\x"])
def test_relative_file_rejects_unsafe_names(name):
    with pytest.raises(h.HarnessError):
        h.relative_file(name)
```

- [ ] **Step 3: Run the compiler-free command.** Expected red result: collection fails because `snapshot_helpers` does not exist. Confirm the failure reason before proceeding.

- [ ] **Step 4: Implement the read-only helper.** Create `tests/snapshot_helpers.py`:

```python
from __future__ import annotations

import difflib
from pathlib import Path, PurePosixPath

Snapshot = dict[str, bytes]


class HarnessError(AssertionError):
    """An actionable test-harness or comparison failure."""


def relative_file(name: str) -> Path:
    path = PurePosixPath(name)
    if (
        not name
        or not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or "\\" in name
        or path.as_posix() != name
    ):
        raise HarnessError(f"Unsafe snapshot name: {name!r}")
    return Path(*path.parts)


def resolve_profile(root: Path, profile: Path) -> Path:
    relative_file(profile.as_posix())
    try:
        base = root.resolve(strict=True)
        destination = (base / profile).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise HarnessError(f"Unavailable snapshot profile: {root / profile}") from error
    if not destination.is_relative_to(base) or destination == base:
        raise HarnessError(f"Snapshot profile escapes root: {root / profile}")
    if not destination.is_dir():
        raise HarnessError(f"Snapshot profile is not a directory: {destination}")
    return destination


def read_tree(root: Path) -> Snapshot:
    if root.is_symlink():
        raise HarnessError(f"Unexpected symlink: {root}")
    if not root.exists():
        return {}
    if not root.is_dir():
        raise HarnessError(f"Expected directory: {root}")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise HarnessError(f"Unexpected symlink: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
        elif not path.is_dir():
            raise HarnessError(f"Unexpected filesystem entry: {path}")
    return result


def diff_tree(expected: Snapshot, actual: Snapshot) -> str:
    differences = []
    for name in sorted(expected.keys() | actual.keys()):
        if name in expected and name in actual and expected[name] == actual[name]:
            continue
        kind = "Missing" if name not in actual else "Unexpected" if name not in expected else "Changed"
        differences.append(f"{kind}: {name}\n")
        before = expected.get(name, b"").decode("utf-8", errors="backslashreplace")
        after = actual.get(name, b"").decode("utf-8", errors="backslashreplace")
        differences.extend(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"expected/{name}", tofile=f"actual/{name}",
        ))
    return "".join(differences)
```

- [ ] **Step 5: Rerun the compiler-free command.** Expected: all Task 1 tests pass, without native imports or filesystem writes beyond synthetic temporary fixtures.
- [ ] **Step 6: Commit the independently tested comparison layer.**

```sh
git add pyproject.toml uv.lock tests/snapshot_helpers.py tests/test_snapshot_helpers.py
git commit -m "test: add read-only snapshot comparison helpers"
```

## Task 2: Add narrowly scoped updates and mutation regressions

**Files:** Modify `tests/snapshot_helpers.py`, `tests/test_snapshot_helpers.py`.

**Interfaces:**
- Consumes: `Snapshot`, `HarnessError`, `relative_file`, `resolve_profile`, `read_tree`, `diff_tree` from Task 1.
- Produces: `SnapshotMismatch(HarnessError)`.
- Produces: `check_snapshot(root: Path, profile: Path, actual: Snapshot, *, update: bool = False, only: frozenset[str] | None = None) -> tuple[str, ...]`.
- Return value: changed relative filenames when updating, or an empty tuple when already equal. A check-mode mismatch raises `SnapshotMismatch` with the diff.
- `only` restricts error snapshots to their stderr filename; it must not delete other files in that profile.

**Self-test command for this task (from the repository root):**

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py -q
```

- [ ] **Step 1: Add update and mutation tests.** Append:

```python
@pytest.mark.parametrize("update", [False, True])
def test_check_update_preserve_aliases_unrelated_files_and_index(tmp_path, update):
    refs = tmp_path / "refs"
    write_files(refs / "real", {"a.pyi": b"developer edit", "old.pyi": b"old"})
    write_files(refs / "unrelated", {"keep.pyi": b"keep"})
    (refs / "alias").symlink_to("real", target_is_directory=True)
    write_files(tmp_path / ".git", {"index": b"pre-existing staged state"})
    before = h.read_tree(refs / "real")
    actual = {"a.pyi": b"new", "nested/new.pyi": b"added"}
    if update:
        changed = h.check_snapshot(refs, Path("alias"), actual, update=True)
        assert set(changed) == {"a.pyi", "old.pyi", "nested/new.pyi"}
        assert h.read_tree(refs / "real") == actual
    else:
        assert h.check_snapshot(refs, Path("alias"), before) == ()
        with pytest.raises(h.SnapshotMismatch):
            h.check_snapshot(refs, Path("alias"), actual)
        assert h.read_tree(refs / "real") == before
    assert (refs / "alias").is_symlink()
    assert h.read_tree(refs / "unrelated") == {"keep.pyi": b"keep"}
    assert (tmp_path / ".git/index").read_bytes() == b"pre-existing staged state"


def test_stderr_update_is_scoped_to_one_file(tmp_path):
    write_files(tmp_path / "case", {"stderr.txt": b"old", "unrelated.txt": b"keep"})
    h.check_snapshot(tmp_path, Path("case"), {"stderr.txt": b"new"},
                     update=True, only=frozenset({"stderr.txt"}))
    assert h.read_tree(tmp_path / "case") == {
        "stderr.txt": b"new", "unrelated.txt": b"keep",
    }


@pytest.mark.parametrize("actual", [
    {"../escape": b"bad"}, {"x": b"file", "x/child": b"collision"},
    {"x": "not bytes"},
])
def test_update_validates_all_content_before_writing(tmp_path, actual):
    write_files(tmp_path / "case", {"keep.pyi": b"original"})
    with pytest.raises(h.HarnessError):
        h.check_snapshot(tmp_path, Path("case"), actual, update=True)
    assert h.read_tree(tmp_path / "case") == {"keep.pyi": b"original"}


def test_update_rejects_nested_reference_symlinks(tmp_path):
    write_files(tmp_path / "case", {"keep.pyi": b"original"})
    (tmp_path / "case/link.pyi").symlink_to("keep.pyi")
    with pytest.raises(h.HarnessError, match="symlink"):
        h.check_snapshot(tmp_path, Path("case"), {"keep.pyi": b"new"}, update=True)
    assert (tmp_path / "case/keep.pyi").read_bytes() == b"original"


def test_update_handles_file_directory_shape_changes(tmp_path):
    write_files(tmp_path / "case", {"old/child": b"old", "flat": b"old"})
    actual = {"old": b"now a file", "flat/child": b"now nested"}
    h.check_snapshot(tmp_path, Path("case"), actual, update=True)
    assert h.read_tree(tmp_path / "case") == actual


def test_scoped_update_rejects_extra_actual_files_before_writing(tmp_path):
    write_files(tmp_path / "case", {"stderr.txt": b"original", "unrelated": b"keep"})
    with pytest.raises(h.HarnessError, match="scope"):
        h.check_snapshot(tmp_path, Path("case"), {"stderr.txt": b"new", "extra": b"bad"},
                         update=True, only=frozenset({"stderr.txt"}))
    assert h.read_tree(tmp_path / "case") == {"stderr.txt": b"original", "unrelated": b"keep"}
```

The synthetic `.git/index` sentinel keeps self-tests independent of Git. Task 6 separately checks the real repository index and references around native runs.

- [ ] **Step 2: Run the compiler-free command.** Expected red result: the new tests fail on missing `check_snapshot`/`SnapshotMismatch`; Task 1 tests stay green.
- [ ] **Step 3: Implement validation, comparison, and update in that order.** Append:

```python
class SnapshotMismatch(HarnessError):
    """Generated output differs from its reference."""


def check_snapshot(
    root: Path, profile: Path, actual: Snapshot, *,
    update: bool = False, only: frozenset[str] | None = None,
) -> tuple[str, ...]:
    for name, content in actual.items():
        path = relative_file(name)
        if not isinstance(content, bytes):
            raise HarnessError(f"Snapshot content must be bytes: {name}")
        if any(parent.as_posix() in actual for parent in path.parents):
            raise HarnessError(f"Conflicting snapshot paths: {name}")
    if only is not None:
        for name in only:
            relative_file(name)
        if actual.keys() - only:
            raise HarnessError("Actual output exceeds the selected snapshot scope")
    destination = resolve_profile(root, profile)
    expected = read_tree(destination)
    if only is not None:
        for name in only:
            target = destination / relative_file(name)
            if target.exists() and not target.is_file():
                raise HarnessError(f"Scoped reference is not a file: {target}")
        expected = {name: content for name, content in expected.items() if name in only}
    difference = diff_tree(expected, actual)
    if not difference:
        return ()
    if not update:
        raise SnapshotMismatch(difference)
    changed = tuple(sorted(
        name for name in expected.keys() | actual.keys()
        if name not in expected or name not in actual or expected[name] != actual[name]
    ))
    for name in expected.keys() - actual.keys():
        (destination / relative_file(name)).unlink()
    if only is None:
        directories = [path for path in destination.rglob("*") if path.is_dir()]
        for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                # Nonempty directories contain retained reference files.
                continue
    for name, content in actual.items():
        target = destination / relative_file(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return changed
```

Do not add Git calls, whole-repository cleanup, alias replacement, or an automatic fallback profile. I/O failures propagate; this is not a transaction across tests or the matrix.

- [ ] **Step 4: Rerun all harness self-tests.** Expected: green. Inspect the helper to confirm all content/path validation occurs before unlink/write operations.
- [ ] **Step 5: Commit.**

```sh
git add tests/snapshot_helpers.py tests/test_snapshot_helpers.py
git commit -m "test: add explicit scoped snapshot updates"
```

## Task 3: Add strict subprocess contracts and existing normalization

**Files:** Modify `tests/snapshot_helpers.py`, `tests/test_snapshot_helpers.py`.

**Interfaces:**
- Consumes: `HarnessError`, `read_tree`.
- Produces: `run_command(argv: list[str], *, cwd: Path, log: Path, expected_status: int = 0) -> subprocess.CompletedProcess[bytes]`.
- Produces: `normalize_stderr(stderr: bytes) -> bytes`, `validate_error_run(result: subprocess.CompletedProcess[bytes], output: Path) -> bytes`.
- Produces: `ruff_version(repo: Path) -> str`, `format_stubs(output: Path, repo: Path, workspace: Path, python_version: tuple[int, int]) -> None`.
- Every process writes `<log>.json`, `<log>.stdout`, `<log>.stderr` before reporting a failure. No process runs through a shell.

**Self-test command for this task (from the repository root):**

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py -q
```

- [ ] **Step 1: Add process and fatal-error tests.** Merge these imports into the self-test file: `import json`, `import subprocess`, `import sys`. Append:

```python
@pytest.mark.parametrize("status", [0, 1, 2, 127])
def test_run_command_requires_exact_status_and_retains_logs(tmp_path, status):
    command = [sys.executable, "-c", f"import sys; print('diagnostic', file=sys.stderr); sys.exit({status})"]
    if status == 1:
        result = h.run_command(command, cwd=tmp_path, log=tmp_path / "process", expected_status=1)
        assert result.returncode == 1
    else:
        with pytest.raises(h.HarnessError, match="expected 1"):
            h.run_command(command, cwd=tmp_path, log=tmp_path / "process", expected_status=1)
    assert b"diagnostic" in (tmp_path / "process.stderr").read_bytes()
    assert json.loads((tmp_path / "process.json").read_text())["returncode"] == status


def test_missing_command_and_timeout_are_diagnostic(tmp_path, monkeypatch):
    with pytest.raises(h.HarnessError):
        h.run_command([str(tmp_path / "missing-command")], cwd=tmp_path, log=tmp_path / "missing")
    assert (tmp_path / "missing.json").is_file()

    def timeout(argv, **kwargs):
        assert kwargs["timeout"] == 300
        raise subprocess.TimeoutExpired(argv, 300, output=b"partial", stderr=b"stuck")

    monkeypatch.setattr(h.subprocess, "run", timeout)
    with pytest.raises(h.HarnessError, match="300"):
        h.run_command(["fake"], cwd=tmp_path, log=tmp_path / "timeout")
    assert (tmp_path / "timeout.stdout").read_bytes() == b"partial"
    assert (tmp_path / "timeout.stderr").read_bytes() == b"stuck"


@pytest.mark.parametrize("status,stderr,files", [
    (0, b"Terminating due to previous errors", {}),
    (2, b"Terminating due to previous errors", {}),
    (1, b"Traceback (most recent call last):\nTerminating due to previous errors", {}),
    (1, b"unrelated failure", {}),
    (1, b"Terminating due to previous errors", {"unexpected.pyi": b"x"}),
])
def test_invalid_fatal_error_runs_are_rejected(tmp_path, status, stderr, files):
    write_files(tmp_path / "output", files)
    result = subprocess.CompletedProcess(["stubgen"], status, b"", stderr)
    with pytest.raises(h.HarnessError):
        h.validate_error_run(result, tmp_path / "output")


def test_error_normalization_is_narrow(tmp_path):
    stderr = b"object at 0xAB12\nTerminating due to previous errors\n"
    result = subprocess.CompletedProcess(["stubgen"], 1, b"", stderr)
    assert h.validate_error_run(result, tmp_path / "absent") == (
        b"object at 0x1234abcd5678\nTerminating due to previous errors\n"
    )
    assert h.normalize_stderr(b"ordinary text 123 abc 0xZZ") == b"ordinary text 123 abc 0xZZ"
```

- [ ] **Step 2: Run the compiler-free command and confirm missing APIs cause the new failures.**
- [ ] **Step 3: Implement process logging and contracts.** Add imports `json`, `re`, and `subprocess` to the helper and append:

```python
def run_command(
    argv: list[str], *, cwd: Path, log: Path, expected_status: int = 0,
) -> subprocess.CompletedProcess[bytes]:
    result = None
    stdout = stderr = b""
    problem = None
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=300, check=False)
        stdout, stderr = result.stdout, result.stderr
        if result.returncode != expected_status:
            problem = f"exit {result.returncode}, expected {expected_status}"
    except subprocess.TimeoutExpired as error:
        stdout, stderr = error.stdout or b"", error.stderr or b""
        problem = "timed out after 300 seconds"
    except OSError as error:
        problem = str(error)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.with_suffix(".stdout").write_bytes(stdout)
    log.with_suffix(".stderr").write_bytes(stderr)
    log.with_suffix(".json").write_text(json.dumps({
        "command": argv, "cwd": str(cwd),
        "returncode": result.returncode if result is not None else None,
        "error": problem,
    }, indent=2) + "\n", encoding="utf-8")
    if problem is not None:
        raise HarnessError(
            f"{argv!r}: {problem}\nLogs: {log}\n"
            f"stdout:\n{stdout.decode('utf-8', errors='replace')}\n"
            f"stderr:\n{stderr.decode('utf-8', errors='replace')}"
        )
    assert result is not None
    return result


def normalize_stderr(stderr: bytes) -> bytes:
    return re.sub(rb"0x[0-9A-Fa-f]+", b"0x1234abcd5678", stderr)


def validate_error_run(result: subprocess.CompletedProcess[bytes], output: Path) -> bytes:
    if result.returncode != 1:
        raise HarnessError(f"Expected fatal-error exit 1, got {result.returncode}")
    if b"Traceback (most recent call last)" in result.stderr:
        raise HarnessError("Unexpected Python traceback in fatal-error run")
    if b"Terminating due to previous errors" not in result.stderr:
        raise HarnessError("Missing fatal-diagnostic termination marker")
    if read_tree(output):
        raise HarnessError("Fatal-error run unexpectedly wrote output")
    return normalize_stderr(result.stderr)
```

- [ ] **Step 4: Run the self-test command.** Expected: all process and fatal-error tests pass.
- [ ] **Step 5: Add the Ruff boundary tests before implementing normalization.** Append:

```python
def test_ruff_pin_configuration_target_order_and_cache_policy(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    write_files(repo, {
        ".pre-commit-config.yaml": (
            b"repos:\n  - repo: unrelated\n    rev: v99.0.0\n"
            b"  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.15.20\n"
        ),
        "pyproject.toml": b"[tool.ruff]\nline-length = 88\n",
    })
    commands = []

    def record(argv, **kwargs):
        commands.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(h, "run_command", record)
    h.format_stubs(tmp_path / "output", repo, tmp_path, (3, 12))
    assert len(commands) == 2
    assert commands[0][0][:5] == ["uvx", "--from", "ruff==0.15.20", "ruff", "format"]
    assert commands[1][0][4:8] == ["check", "--select", "I,RUF022", "--fix"]
    for argv, kwargs in commands:
        assert argv[argv.index("--config") + 1] == str(repo / "pyproject.toml")
        assert argv[argv.index("--target-version") + 1] == "py312"
        assert "--no-cache" in argv
        assert kwargs["cwd"] == tmp_path


def test_invalid_ruff_pin_and_formatter_failure_are_not_ignored(tmp_path, monkeypatch):
    write_files(tmp_path, {".pre-commit-config.yaml": b"repos: []\n"})
    with pytest.raises(h.HarnessError, match="Ruff"):
        h.ruff_version(tmp_path)
    write_files(tmp_path, {".pre-commit-config.yaml": (
        b"repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.15.20\n"
    )})

    def fail(argv, **kwargs):
        raise h.HarnessError("formatter failed")

    monkeypatch.setattr(h, "run_command", fail)
    with pytest.raises(h.HarnessError, match="formatter failed"):
        h.format_stubs(tmp_path / "output", tmp_path, tmp_path, (3, 10))
```

- [ ] **Step 6: Run the self-test command.** Expected: the new tests fail because `ruff_version` and `format_stubs` do not exist yet.
- [ ] **Step 7: Implement the Ruff adapter.** This narrowly parses the existing pin; do not introduce PyYAML or a generic configuration framework:

```python
def ruff_version(repo: Path) -> str:
    text = (repo / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^\s*-\s+repo:\s*", text)[1:]
    blocks = [block for block in blocks if block.splitlines()[0].strip().strip("\"'")
              == "https://github.com/astral-sh/ruff-pre-commit"]
    if len(blocks) != 1:
        raise HarnessError("Cannot identify the Ruff pre-commit pin")
    match = re.search(r'''(?m)^\s*rev:\s*["']?v?(\d+\.\d+\.\d+)["']?\s*$''', blocks[0])
    if match is None:
        raise HarnessError("Cannot resolve the Ruff pre-commit version")
    return match.group(1)


def format_stubs(
    output: Path, repo: Path, workspace: Path, python_version: tuple[int, int],
) -> None:
    prefix = ["uvx", "--from", f"ruff=={ruff_version(repo)}", "ruff"]
    options = ["--config", str(repo / "pyproject.toml"), "--target-version",
               f"py{python_version[0]}{python_version[1]}", "--no-cache", str(output)]
    run_command(prefix + ["format"] + options, cwd=workspace, log=workspace / "ruff-format")
    run_command(prefix + ["check", "--select", "I,RUF022", "--fix"] + options,
                cwd=workspace, log=workspace / "ruff-check")
```

`--no-cache` keeps Ruff cache files out of the compared output; uv's tool cache remains outside that tree. Tests mock Ruff execution, so self-tests still need pytest alone.

- [ ] **Step 8: Run the self-test command.** Expected: all process, error-contract, and normalization tests pass without executing Ruff.
- [ ] **Step 9: Commit.**

```sh
git add tests/snapshot_helpers.py tests/test_snapshot_helpers.py
git commit -m "test: validate generator processes and preserve normalization"
```

## Task 4: Retain useful failure artifacts without touching references

**Files:** Modify `tests/snapshot_helpers.py`, `tests/test_snapshot_helpers.py`.

**Interfaces:**
- Consumes: `HarnessError`, `SnapshotMismatch`, `relative_file`.
- Produces context manager: `diagnostics(workspace: Path, *, artifacts: Path | None, reference_roots: tuple[Path, ...], case_id: str, check_name: str, expected: Path) -> Iterator[None]`.
- Validates destinations before yielding; records context locally. On a failure, retains regular files in a unique run directory under `<artifacts>/<case_id>/<check_name>/` and raises `HarnessError` with locations and original diagnostics.

**Self-test command for this task (from the repository root):**

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py -q
```

- [ ] **Step 1: Add artifact safety and retention tests.** Append:

```python
@pytest.mark.parametrize("through_alias", [False, True])
def test_artifacts_cannot_target_reference_trees(tmp_path, through_alias):
    refs = tmp_path / "refs"
    write_files(refs / "case", {"x.pyi": b"keep"})
    destination = refs / "artifacts"
    if through_alias:
        alias = tmp_path / "alias"
        alias.symlink_to(refs, target_is_directory=True)
        destination = alias / "artifacts"
    with pytest.raises(h.HarnessError, match="reference"):
        with h.diagnostics(tmp_path / "work", artifacts=destination,
                           reference_roots=(refs,), case_id="case", check_name="stubs",
                           expected=refs / "case"):
            raise AssertionError("body must not run")
    assert h.read_tree(refs) == {"case/x.pyi": b"keep"}


def test_failure_artifacts_include_output_diff_and_context(tmp_path):
    workspace = tmp_path / "work"
    refs = tmp_path / "refs"
    write_files(refs / "case", {"x.pyi": b"expected"})
    with pytest.raises(h.HarnessError, match="Artifacts:"):
        with h.diagnostics(workspace, artifacts=tmp_path / "artifacts",
                           reference_roots=(refs,), case_id="case", check_name="stubs",
                           expected=refs / "case"):
            write_files(workspace / "output", {"x.pyi": b"actual"})
            raise h.SnapshotMismatch("Changed: x.pyi\n")
    runs = list((tmp_path / "artifacts/case/stubs").iterdir())
    assert len(runs) == 1
    assert (runs[0] / "output/x.pyi").read_bytes() == b"actual"
    assert "Changed: x.pyi" in (runs[0] / "diff.patch").read_text()
    assert str(refs / "case") in (runs[0] / "context.txt").read_text()
    assert h.read_tree(refs) == {"case/x.pyi": b"expected"}


def test_artifacts_cannot_recurse_into_workspace(tmp_path):
    with pytest.raises(h.HarnessError, match="workspace"):
        with h.diagnostics(tmp_path, artifacts=tmp_path / "artifacts",
                           reference_roots=(tmp_path / "refs",), case_id="case",
                           check_name="stubs", expected=tmp_path / "refs/case"):
            raise AssertionError("body must not run")
```

- [ ] **Step 2: Run the self-tests and confirm the missing `diagnostics` API causes failures.**
- [ ] **Step 3: Implement diagnostics.** Add `from contextlib import contextmanager`, `from collections.abc import Iterator`, `import shutil`, and `import tempfile` to the helper. Append:

```python
@contextmanager
def diagnostics(
    workspace: Path, *, artifacts: Path | None, reference_roots: tuple[Path, ...],
    case_id: str, check_name: str, expected: Path,
) -> Iterator[None]:
    workspace = workspace.resolve()
    artifact_parent = None
    for component in (case_id, check_name):
        if len(relative_file(component).parts) != 1:
            raise HarnessError(f"Invalid artifact identifier: {component}")
    if artifacts is not None:
        base = artifacts.resolve()
        artifact_parent = (base / case_id / check_name).resolve()
        if not artifact_parent.is_relative_to(base):
            raise HarnessError("Artifact identifiers escape their destination")
        for candidate in (base, artifact_parent):
            if any(candidate.is_relative_to(root.resolve()) for root in reference_roots):
                raise HarnessError("Artifact destination is inside a reference tree")
        if artifact_parent.is_relative_to(workspace):
            raise HarnessError("Artifact destination is inside the working workspace")
    workspace.mkdir(parents=True, exist_ok=True)
    context = f"Case: {case_id}/{check_name}\nReference: {expected.resolve()}\nWorkspace: {workspace}\n"
    (workspace / "context.txt").write_text(context, encoding="utf-8")
    try:
        yield
    except Exception as error:
        summary = context + str(error)
        (workspace / "failure.txt").write_text(summary, encoding="utf-8")
        if isinstance(error, SnapshotMismatch):
            (workspace / "diff.patch").write_text(str(error), encoding="utf-8")
        if artifact_parent is not None:
            artifact_parent.mkdir(parents=True, exist_ok=True)
            destination = Path(tempfile.mkdtemp(prefix="run-", dir=artifact_parent))
            for source in workspace.rglob("*"):
                # Never dereference rejected output symlinks while retaining diagnostics.
                if source.is_symlink() or not source.is_file():
                    continue
                target = destination / source.relative_to(workspace)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            summary += f"\nArtifacts: {destination}"
        raise HarnessError(summary) from error
```

- [ ] **Step 4: Run all self-tests.** Expected: green; artifact failures cannot create directories inside reference roots, including through aliases.
- [ ] **Step 5: Commit.**

```sh
git add tests/snapshot_helpers.py tests/test_snapshot_helpers.py
git commit -m "test: retain isolated snapshot failure diagnostics"
```

## Task 5: Connect lazy pytest fixtures and both native test contracts

**Files:**
- Create: `tests/conftest.py`, `tests/test_demo_stubs.py`, `tests/test_demo_errors.py`.
- Modify: `tests/snapshot_helpers.py`, `tests/test_snapshot_helpers.py`.

**Interfaces:**
- Consumes all helper interfaces from Tasks 1–4.
- Produces frozen `DemoCase(repo: Path, python_version: tuple[int, int], branch: str, numpy_format: str)` with properties `id`, `stubs_root`, `errors_root`, `stub_profile`, `error_profile`.
- Produces `make_case(repo: Path, python_version: tuple[int, int], branch: str | None, numpy_format: str | None) -> DemoCase`.
- pytest fixtures: `demo_case -> DemoCase`, `update_snapshots -> bool`, `artifacts_dir -> Path | None`, `report_update -> Callable[[str], None]`.
- Native test functions take those four fixtures plus `tmp_path`; they are also callable from synthetic orchestration tests without a compiler.

**Self-test command for this task (from the repository root):**

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py -q
```

- [ ] **Step 1: Add profile-selection tests first.** Append:

```python
@pytest.mark.parametrize("branch,mode", [(None, None), ("v9.9", "numpy-array-use-type-var"),
                                         ("v3.0", "invalid-format")])
def test_case_requires_explicit_recognized_configuration(tmp_path, branch, mode):
    with pytest.raises(h.HarnessError):
        h.make_case(tmp_path, (3, 13), branch, mode)


def test_case_requires_existing_profiles_and_uses_runtime_python(tmp_path):
    mode = "numpy-array-wrap-with-annotated"
    with pytest.raises(h.HarnessError):
        h.make_case(tmp_path, (3, 13), "v3.0", mode)
    write_files(tmp_path / "tests/stubs/python-3.13/pybind11-v3.0" / mode, {})
    write_files(tmp_path / "tests/errors/pybind11-v3.0", {})
    case = h.make_case(tmp_path, (3, 13), "v3.0", mode)
    assert case.stub_profile == Path("python-3.13/pybind11-v3.0") / mode
    assert case.error_profile == Path("pybind11-v3.0")
    assert "python-3.13" in case.id
```

- [ ] **Step 2: Run the self-test command.** Expected: the new profile tests fail because `make_case` does not exist yet.
- [ ] **Step 3: Implement the metadata.** Add `from dataclasses import dataclass` to the helper and append:

```python
BRANCHES = ("v2.9", "v2.11", "v2.12", "v2.13", "v3.0")
NUMPY_FORMATS = ("numpy-array-wrap-with-annotated", "numpy-array-use-type-var")


@dataclass(frozen=True)
class DemoCase:
    repo: Path
    python_version: tuple[int, int]
    branch: str
    numpy_format: str

    @property
    def id(self) -> str:
        major, minor = self.python_version
        return f"python-{major}.{minor}-pybind11-{self.branch}-{self.numpy_format}"

    @property
    def stubs_root(self) -> Path:
        return self.repo / "tests/stubs"

    @property
    def errors_root(self) -> Path:
        return self.repo / "tests/errors"

    @property
    def stub_profile(self) -> Path:
        major, minor = self.python_version
        return Path(f"python-{major}.{minor}") / f"pybind11-{self.branch}" / self.numpy_format

    @property
    def error_profile(self) -> Path:
        return Path(f"pybind11-{self.branch}")


def make_case(
    repo: Path, python_version: tuple[int, int], branch: str | None, numpy_format: str | None,
) -> DemoCase:
    if python_version < (3, 10):
        raise HarnessError("The test harness requires Python >=3.10")
    if branch not in BRANCHES or numpy_format not in NUMPY_FORMATS:
        raise HarnessError("Native tests require --pybind11-branch and --numpy-format; use tox to build the matching demo")
    case = DemoCase(repo.resolve(), python_version, branch, numpy_format)
    resolve_profile(case.stubs_root, case.stub_profile)
    resolve_profile(case.errors_root, case.error_profile)
    return case
```

- [ ] **Step 4: Run the self-test command.** Expected: all profile-selection tests pass.
- [ ] **Step 5: Add orchestration safety tests before creating the native test modules.** Append:

```python
@pytest.mark.parametrize("failure_stage", ["generator", "formatter"])
def test_success_update_never_accepts_failed_generation_or_formatting(tmp_path, monkeypatch, failure_stage):
    import test_demo_stubs as integration

    repo = tmp_path / "repo"
    case = h.DemoCase(repo, (3, 13), "v3.0", "numpy-array-wrap-with-annotated")
    reference = case.stubs_root / case.stub_profile
    write_files(reference, {"demo/__init__.pyi": b"original"})
    messages = []

    def generate(argv, **kwargs):
        assert argv[:4] == [sys.executable, "-I", "-m", "pybind11_stubgen"]
        assert kwargs["expected_status"] == 0
        if failure_stage == "generator":
            raise h.HarnessError("generator failed")
        write_files(kwargs["cwd"] / "output", {"demo/__init__.pyi": b"new"})
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    def format_failure(*args):
        raise h.HarnessError("formatter failed")

    monkeypatch.setattr(integration, "run_command", generate)
    monkeypatch.setattr(integration, "format_stubs", format_failure)
    with pytest.raises(h.HarnessError, match=f"{failure_stage} failed"):
        integration.test_demo_stubs(case, tmp_path / "work", True, None, messages.append)
    assert h.read_tree(reference) == {"demo/__init__.pyi": b"original"}
    assert messages == []


def test_error_update_rejects_traceback_even_with_exit_one(tmp_path, monkeypatch):
    import test_demo_errors as integration

    case = h.DemoCase(tmp_path / "repo", (3, 13), "v3.0", "numpy-array-use-type-var")
    reference = case.errors_root / case.error_profile
    write_files(reference, {"demo.errors.stderr.txt": b"original"})

    def traceback_result(argv, **kwargs):
        assert argv[:4] == [sys.executable, "-I", "-m", "pybind11_stubgen"]
        assert kwargs["expected_status"] == 1
        return subprocess.CompletedProcess(argv, 1, b"", b"Traceback (most recent call last):\n")

    monkeypatch.setattr(integration, "run_command", traceback_result)
    with pytest.raises(h.HarnessError, match="traceback"):
        integration.test_demo_errors(case, tmp_path / "work", True, None, print)
    assert h.read_tree(reference) == {"demo.errors.stderr.txt": b"original"}


@pytest.mark.parametrize("kind", ["stubs", "errors"])
@pytest.mark.parametrize("update", [False, True])
def test_integration_check_and_update_paths_with_synthetic_output(tmp_path, monkeypatch, kind, update):
    import test_demo_errors
    import test_demo_stubs

    case = h.DemoCase(tmp_path / "repo", (3, 13), "v3.0", "numpy-array-wrap-with-annotated")
    integration = test_demo_stubs if kind == "stubs" else test_demo_errors
    run_test = integration.test_demo_stubs if kind == "stubs" else integration.test_demo_errors
    reference = case.stubs_root / case.stub_profile if kind == "stubs" else case.errors_root / case.error_profile
    filename = "demo/__init__.pyi" if kind == "stubs" else "demo.errors.stderr.txt"
    new_content = b"new stubs\n" if kind == "stubs" else b"object 0x1234abcd5678\nTerminating due to previous errors\n"
    write_files(reference, {filename: b"original"})
    messages = []

    def generate(argv, **kwargs):
        if kind == "stubs":
            write_files(kwargs["cwd"] / "output", {filename: new_content})
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        return subprocess.CompletedProcess(argv, 1, b"", b"object 0xABCD\nTerminating due to previous errors\n")

    monkeypatch.setattr(integration, "run_command", generate)
    if kind == "stubs":
        monkeypatch.setattr(integration, "format_stubs", lambda *args: None)
    if update:
        run_test(case, tmp_path / "work", True, None, messages.append)
        assert h.read_tree(reference) == {filename: new_content}
        assert messages and str(reference.resolve()) in messages[0]
    else:
        with pytest.raises(h.HarnessError, match="Changed:"):
            run_test(case, tmp_path / "work", False, None, messages.append)
        assert h.read_tree(reference) == {filename: b"original"}
        assert messages == []


@pytest.mark.parametrize("empty_at", ["generator", "formatter"])
def test_empty_output_cannot_erase_references(tmp_path, monkeypatch, empty_at):
    import test_demo_stubs as integration

    case = h.DemoCase(tmp_path / "repo", (3, 13), "v3.0", "numpy-array-wrap-with-annotated")
    reference = case.stubs_root / case.stub_profile
    write_files(reference, {"demo/__init__.pyi": b"original"})

    def generate(argv, **kwargs):
        if empty_at == "formatter":
            write_files(kwargs["cwd"] / "output", {"demo/__init__.pyi": b"new"})
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    def erase_output(output, repo, workspace, python_version):
        (output / "demo/__init__.pyi").unlink()

    monkeypatch.setattr(integration, "run_command", generate)
    monkeypatch.setattr(integration, "format_stubs", erase_output)
    with pytest.raises(h.HarnessError, match="demo/__init__.pyi"):
        integration.test_demo_stubs(case, tmp_path / "work", True, None, print)
    assert h.read_tree(reference) == {"demo/__init__.pyi": b"original"}
```

- [ ] **Step 6: Run the self-test command.** Expected: new orchestration tests fail because the native-test modules do not exist yet.
- [ ] **Step 7: Create the lazy fixtures in `tests/conftest.py`.**

```python
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
    return make_case(Path(__file__).resolve().parents[1], sys.version_info[:2],
                     pytestconfig.getoption("pybind11_branch"),
                     pytestconfig.getoption("numpy_format"))


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
```

The terminal reporter is intentional: updates must display destinations and changed paths even when a passing test's stdout would normally be captured.

- [ ] **Step 8: Create `tests/test_demo_stubs.py` with the existing generator flags and validated ordering.**

```python
import sys

from snapshot_helpers import (
    HarnessError, check_snapshot, diagnostics, format_stubs, read_tree, run_command,
)


def test_demo_stubs(demo_case, tmp_path, update_snapshots, artifacts_dir, report_update):
    case = demo_case
    expected = case.stubs_root / case.stub_profile
    output = tmp_path / "output"
    with diagnostics(tmp_path, artifacts=artifacts_dir,
                     reference_roots=(case.stubs_root, case.errors_root),
                     case_id=case.id, check_name="stubs", expected=expected):
        run_command([
            sys.executable, "-I", "-m", "pybind11_stubgen", "demo",
            "--output-dir", str(output), f"--{case.numpy_format}",
            r"--ignore-invalid-expressions=\(anonymous namespace\)::(Enum|Unbound)|<demo\._bindings\.flawed_bindings\..*",
            "--enum-class-locations=ConsoleForegroundColor:demo._bindings.enum",
            "--print-value-comments", r"--print-safe-value-reprs=Foo\(\d+\)", "--exit-code",
        ], cwd=tmp_path, log=tmp_path / "stubgen", expected_status=0)
        if "demo/__init__.pyi" not in read_tree(output):
            raise HarnessError("Successful demo generation did not produce demo/__init__.pyi")
        format_stubs(output, case.repo, tmp_path, case.python_version)
        actual = read_tree(output)
        if "demo/__init__.pyi" not in actual:
            raise HarnessError("Normalized output lost demo/__init__.pyi")
        changed = check_snapshot(case.stubs_root, case.stub_profile, actual,
                                 update=update_snapshots)
        if update_snapshots:
            report_update(f"{case.id}: {expected} -> {expected.resolve()}; changed: {changed}")
```

Validate the tree before and after normalization: reject unexpected links before handing files to Ruff, and prevent update mode from deleting all references after a spurious successful command or formatter that left no demo output.

- [ ] **Step 9: Create `tests/test_demo_errors.py`.**

```python
import sys

from snapshot_helpers import check_snapshot, diagnostics, run_command, validate_error_run


def test_demo_errors(demo_case, tmp_path, update_snapshots, artifacts_dir, report_update):
    case = demo_case
    expected = case.errors_root / case.error_profile
    output = tmp_path / "output"
    filename = "demo.errors.stderr.txt"
    with diagnostics(tmp_path, artifacts=artifacts_dir,
                     reference_roots=(case.stubs_root, case.errors_root),
                     case_id=case.id, check_name="errors", expected=expected / filename):
        result = run_command([
            sys.executable, "-I", "-m", "pybind11_stubgen", "demo",
            "--output-dir", str(output), "--exit-code",
        ], cwd=tmp_path, log=tmp_path / "stubgen", expected_status=1)
        stderr = validate_error_run(result, output)
        (tmp_path / "normalized.stderr").write_bytes(stderr)
        changed = check_snapshot(case.errors_root, case.error_profile, {filename: stderr},
                                 update=update_snapshots, only=frozenset({filename}))
        if update_snapshots:
            report_update(f"{case.id}: {expected} -> {expected.resolve()}; changed: {changed}")
```

- [ ] **Step 10: Run the self-test command.** Expected: all harness tests pass without an installed demo.
- [ ] **Step 11: Verify collection without native configuration.**

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests --collect-only -q
```

Expected: collection succeeds without native imports or build commands.

- [ ] **Step 12: Verify that missing configuration fails explicitly.**

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_demo_stubs.py -q
```

Expected: failure with the missing-configuration message, not a skip or attempted build. This failure is deliberate; do not treat it as a native baseline run. Actual installed-demo validation happens after Task 6 replaces the unsafe tox entry point.

- [ ] **Step 13: Commit.**

```sh
git add tests/snapshot_helpers.py tests/test_snapshot_helpers.py tests/conftest.py tests/test_demo_stubs.py tests/test_demo_errors.py
git commit -m "test: add pytest demo generation and error checks"
```

## Task 6: Switch callers, document workflows, and verify compatibility

**Files:**
- Modify: `tox.ini`, `.github/workflows/ci.yml`, `README.md`, `tests/README.md`, `tests/test_snapshot_helpers.py`.
- Delete: `tests/check-demo-stubs-generation.sh`, `tests/check-demo-errors-generation.sh`.
- Verify but do not rewrite: `tests/install-demo-module.sh`, native fixture sources, reference trees, existing CI matrix and `gemmi` job.

**Interfaces:**
- Consumes the four pytest options and three test files from Task 5.
- Produces safe default tox/CI checks, `tox -e py313-pb30-naa -- --update-snapshots` forwarding, and failed-run artifacts under `tmp/pytest-artifacts/` in CI.
- No new production interface, native build step, or matrix configuration.

**Self-test command for this task (from the repository root):**

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py -q
```

- [ ] **Step 1: Add a regression for the entry-point switch.** Append to the self-tests:

```python
def test_entry_points_use_pytest_without_legacy_mutating_checks():
    repo = Path(__file__).resolve().parents[1]
    tox = (repo / "tox.ini").read_text()
    ci = (repo / ".github/workflows/ci.yml").read_text()
    assert "-m pytest" in tox and "{posargs}" in tox
    assert "pytest>=8,<9" in tox
    assert "PYTHON_TAG_FILE" not in tox
    native_job = ci.split("  tests:\n", 1)[1].split("  test-cli-options:\n", 1)[0]
    assert "-m pytest" in native_job
    assert "tmp/pytest-artifacts/" in native_job
    assert "--update-snapshots" not in native_job
    for script in ("check-demo-stubs-generation.sh", "check-demo-errors-generation.sh"):
        assert script not in tox and script not in ci
```

- [ ] **Step 2: Run self-tests.** Expected red result: only the entry-point test fails because tox/CI still invoke the old scripts.
- [ ] **Step 3: Rewire tox without changing its environment list, branch mappings, CMake pins, or build command.** Add `pytest>=8,<9` to `deps`. Change the description, remove `STUBS_OUT`, `PYTHON_TAG_FILE`, and the Python-tag `commands_pre` line. Keep the existing demo installation `commands_pre` line. Set:

```ini
description = Check generated demo stubs and errors

commands =
    {envpython} -m pip install .
    {envpython} -m pytest {toxinidir}/tests/test_snapshot_helpers.py {toxinidir}/tests/test_demo_stubs.py {toxinidir}/tests/test_demo_errors.py --pybind11-branch {env:PYBIND11_BRANCH} --numpy-format {env:NUMPY_FORMAT} --artifacts-dir {envtmpdir}/pytest-artifacts {posargs}
```

The `description` belongs in `[testenv]`, not inside `commands`. Retain the existing uv/tox setup policy; changing native dependency or CMake selection belongs to phase 3.

- [ ] **Step 4: Replace CI's two checking steps and patch-upload step with these steps.** Preserve all earlier wheel/demo installation steps and the surrounding matrix:

```yaml
      - name: Check installed wheel and demo snapshots
        shell: bash
        run: |
          source .venv/bin/activate
          python -I -c 'import sys; from pathlib import Path; import pybind11_stubgen; p = Path(pybind11_stubgen.__file__).resolve(); assert p.is_relative_to(Path(sys.prefix).resolve()), p; print(p)'
          python -m pytest tests/test_snapshot_helpers.py tests/test_demo_stubs.py tests/test_demo_errors.py \
            --pybind11-branch "${{ matrix.config.pybind11-branch }}" \
            --numpy-format "${{ matrix.config.numpy-format }}" \
            --artifacts-dir tmp/pytest-artifacts/ --maxfail=0

      - name: Archive test diagnostics
        uses: actions/upload-artifact@v6
        if: failure()
        with:
          name: "python-${{ matrix.config.python }}-pybind-${{ matrix.config.pybind11-branch }}-${{ matrix.config.numpy-format }}-diagnostics"
          path: tmp/pytest-artifacts/
          retention-days: 30
          if-no-files-found: ignore
```

The wheel-origin assertion protects against accidentally importing an editable checkout. Do not run `uv run` or another project sync in this job after the wheel is installed. The single pytest invocation attempts both native checks even when one fails.

- [ ] **Step 5: Remove the legacy checker files now that their callers are gone.** Use scoped removal; do not touch the installer:

```sh
git rm tests/check-demo-stubs-generation.sh tests/check-demo-errors-generation.sh
```

- [ ] **Step 6: Replace `tests/README.md` with this workflow guide.**

````markdown
# Testing

The native demo models a C++ library (`demo-lib`), its bindings
(`py-demo/bindings`), and a mixed Python/native package (`py-demo`).

Checks generate output in temporary directories and compare it with `stubs/`
and `errors/`. They never modify references or stage files. Updating references
is a separate, explicit operation.

## Prerequisites

Use Python 3.10 or newer. Native tests additionally need Git, a C++17 compiler,
uv, and tox with tox-uv. Tox installs the existing CMake/Eigen/Python dependencies.
Initial builds clone pybind11; normalization may download the pinned Ruff tool.

```sh
uv python install 3.10 3.11 3.12 3.13
uv tool install tox --with tox-uv
```

## Harness self-tests, without a compiler

With pytest installed:

```sh
python -m pytest tests/test_snapshot_helpers.py
```

Or let uv supply only pytest, without syncing the project's native dependencies:

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py
```

## Native checks

```sh
tox -e py313-pb30-naa                 # One environment: Python 3.13, pybind11 3.0, annotated arrays.
tox -e py313-pb30-naa -- -k demo_errors  # One check in that environment.
tox                                  # Full configured matrix, serially.
```

Environment suffix `naa` means `numpy-array-wrap-with-annotated`; `nutv` means
`numpy-array-use-type-var`. Keep runs serial: the existing native build and some
reference directories are shared. Do not use `tox -p` or pytest workers yet.

After tox has installed the project and matching demo, a check can be rerun
without rebuilding:

```sh
.tox/py313-pb30-naa/bin/python -m pytest tests/test_demo_stubs.py \
  --pybind11-branch v3.0 --numpy-format numpy-array-wrap-with-annotated
```

That command tests the installed generator, not uninstalled source edits. Rerun
tox after changing generator or native fixture code. Missing configuration or a
missing demo is an error, not a skipped test.

## Update references deliberately

```sh
tox -e py313-pb30-naa -- --update-snapshots
git diff -- tests/stubs tests/errors
```

Use `-k demo_stubs` or `-k demo_errors` with the update option to select one kind
of expectation. Generation, exit-status, no-output, and formatting assertions
still apply in update mode. A broken command cannot become a new expectation.

Updates report their canonical destination and changed paths. Some directories
are aliases (for example, Python 3.13 uses the Python 3.12 reference directory).
An update to shared expectations affects every profile using that directory;
review and recheck those profiles. Aliases are preserved, and unrelated profiles
are not rewritten. Nothing is automatically staged or committed.

Updates are per test, not transactional across a run. If a later check fails,
earlier successful checks may already have updated their references. Always
review the diff; do not accept unexplained changes from a bulk regeneration.

## Failures and artifacts

Failures show the configuration, resolved reference location, file-set changes,
content diffs, and process diagnostics. Each check uses a fresh temporary output
directory. Optional `--artifacts-dir PATH` retains failure output outside the
reference trees. Tox uses its environment temporary directory; CI uploads
`tmp/pytest-artifacts/` with separate configuration/check/run subdirectories.

## Add a regression

For harness behavior, add a small synthetic test to `test_snapshot_helpers.py`;
no compiler is required. For generated-output behavior, add or adjust the demo
fixture, run a relevant native environment, inspect its failure, then explicitly
update that environment's expectations. Review only the intended changes and
run affected shared profiles and the compatibility matrix before merging.
````

- [ ] **Step 7: Replace only the root README's Contributing section with a short link and hook instructions.**

````markdown
Contributing
------------

See [the testing guide](tests/README.md) for prerequisites, running checks,
updating reference snapshots, and adding regression fixtures. Normal test runs
do not update or stage reference files.

To enable repository hooks locally:

```sh
uv sync
uv run pre-commit install
```
````

Keep the rest of the README unchanged.

- [ ] **Step 8: Verify the compiler-free layer on the supported floor and a current matrix interpreter.** These are verification runs, not snapshot updates:

```sh
uv run --no-project --python 3.10 --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py -q
uv run --no-project --python 3.13 --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py -q
uv lock --check
```

Expected: both self-test runs and the lock check pass. Run the repository hooks on the changed files in the development environment:

```sh
uv run pre-commit run --files pyproject.toml uv.lock tox.ini .github/workflows/ci.yml README.md tests/README.md tests/snapshot_helpers.py tests/test_snapshot_helpers.py tests/conftest.py tests/test_demo_stubs.py tests/test_demo_errors.py
```

If hooks reformat code, rerun both compiler-free commands before committing. This project-syncing hook command is local development only, not part of the installed-wheel CI test step.

- [ ] **Step 9: Verify preservation of the native matrix/build and the `gemmi` job.** Run this read-only comparison against the investigation baseline:

```sh
python - <<'PY'
from pathlib import Path
import subprocess

base = '99eb2dc'
old = subprocess.check_output(['git', 'show', f'{base}:.github/workflows/ci.yml'], text=True)
new = Path('.github/workflows/ci.yml').read_text()
def matrix(text):
    return text.split('  tests:\n', 1)[1].split('    steps:\n', 1)[0]
assert matrix(old) == matrix(new), 'Native matrix or scheduling changed'
assert old.split('  test-cli-options:\n', 1)[1] == new.split('  test-cli-options:\n', 1)[1], 'Smoke/publish jobs changed'
for path in ['tests/install-demo-module.sh', 'tests/demo-lib', 'tests/py-demo']:
    subprocess.run(['git', 'diff', '--exit-code', base, '--', path], check=True)
print('Matrix, native fixtures/build, and gemmi/publish jobs preserved')
PY
```

Also review `git diff 99eb2dc -- tox.ini` to confirm the environment list and native dependency pins are unchanged. Do not create a third copy of the matrix in test code.

- [ ] **Step 10: Run one representative native environment and prove check-mode immutability, even on failure.** Only now is the tox entry point safe to use:

```sh
python - <<'PY'
from pathlib import Path
import hashlib
import os
import subprocess

def state():
    references = {}
    for root in (Path('tests/stubs'), Path('tests/errors')):
        for path in sorted(root.rglob('*')):
            name = str(path)
            if path.is_symlink():
                references[name] = ('symlink', os.readlink(path))
            elif path.is_file():
                references[name] = ('file', hashlib.sha256(path.read_bytes()).hexdigest())
            elif path.is_dir():
                references[name] = ('directory',)
    index = subprocess.check_output(['git', 'ls-files', '--stage', '-z'])
    return references, index

before = state()
result = subprocess.run(['tox', '-e', 'py313-pb30-naa'], check=False)
assert state() == before, 'Check-mode run changed references or staging state'
raise SystemExit(result.returncode)
PY
```

Expected: two native checks and the self-tests pass; reference bytes, alias targets, and index entries remain unchanged. If a baseline snapshot/build issue is exposed, preserve diagnostics and investigate it separately; never run a blanket update to obtain green results.

- [ ] **Step 11: Exercise the remaining representative differences, then the full matrix.**

```sh
tox -e py310-pb30-naa,py313-pb213-naa,py313-pb30-nutv
tox
```

The full CI matrix must exercise all 13 profiles before merge. Local missing interpreters, unavailable network/toolchains, and pre-existing build failures must be reported as limits, not represented as passing coverage. Confirm a deliberate synthetic mismatch from the self-tests produces useful artifacts and does not change references; do not corrupt checked-in snapshots to trigger CI failures.

- [ ] **Step 12: Review the final diff and commit the caller/documentation switch.**

```sh
git diff --check
git diff -- tests/stubs tests/errors
git add tox.ini .github/workflows/ci.yml README.md tests/README.md tests/test_snapshot_helpers.py
git commit -m "test: switch tox and CI to non-mutating pytest checks"
```

The script deletions were staged by the scoped `git rm`. No reference changes belong in this mechanical commit. If reference corrections are proven necessary, explain and review them separately as required by the spec.

## Spec-to-task review map

| Specification requirement | Implementation/verification task |
| --- | --- |
| Python >=3.10; pytest-only self-tests; explicit discovery | Tasks 1 and 6 |
| Complete byte/file-set comparisons; working-tree expectations, not Git | Tasks 1–2 |
| Scoped updates; stale files; aliases; escaping paths; developer changes | Task 2, integration guards in Task 5, real index check in Task 6 |
| Exact exit codes; tracebacks; absent executable; no output on errors; 300-second timeouts | Tasks 3 and 5 |
| Existing Ruff pin/config/target/order and narrow address normalization | Task 3 |
| Safe, useful failure artifacts and CI retention | Tasks 4 and 6 |
| Explicit profile options; lazy fixtures; isolated installed-module subprocesses | Task 5 |
| Update reporting, shared aliases, and per-test transaction boundary | Tasks 2 and 5; Task 6 documentation |
| Existing native build, 13 configurations, wheel coverage, and unchanged gemmi job | Task 6 |
| Contributor workflows and removal of duplicate shell checkers | Task 6 |
| Phases 2–4 remain a roadmap, not incidental implementation | Completion boundary below |

## Completion evidence and later phases

Before reporting implementation complete, record:

- Python 3.10 and 3.13 compiler-free results.
- Native configurations actually run and any limitations; CI results for all 13 configurations.
- Installed-wheel origin verification and unchanged `gemmi` job.
- Passing and intentionally failing synthetic check/update safety cases.
- Check-mode reference/index immutability evidence and usable failure artifacts.
- Clean formatting/lock checks, scoped commits, and absence of unexplained reference churn.

Do not start phases 2–4 as incidental refactoring. Their roadmap remains in the
approved spec: compiler-free production tests; shared orchestration/simpler
native builds; then snapshot deduplication. Each requires a separate scoped plan.
