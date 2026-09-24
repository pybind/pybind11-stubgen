from __future__ import annotations

import difflib
import errno
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
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
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                paths = sorted(directory / entry.name for entry in entries)
        except OSError as error:
            raise HarnessError(f"Unable to scan directory: {directory}") from error
        for path in paths:
            if path.is_symlink():
                raise HarnessError(f"Unexpected symlink: {path}")
            if path.is_file():
                result[path.relative_to(root).as_posix()] = path.read_bytes()
            elif path.is_dir():
                pending.append(path)
            else:
                raise HarnessError(f"Unexpected filesystem entry: {path}")
    return result


def diff_tree(expected: Snapshot, actual: Snapshot) -> str:
    differences = []
    for name in sorted(expected.keys() | actual.keys()):
        if name in expected and name in actual and expected[name] == actual[name]:
            continue
        kind = (
            "Missing"
            if name not in actual
            else "Unexpected"
            if name not in expected
            else "Changed"
        )
        differences.append(f"{kind}: {name}\n")
        before = expected.get(name, b"").decode("utf-8", errors="backslashreplace")
        after = actual.get(name, b"").decode("utf-8", errors="backslashreplace")
        differences.extend(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"expected/{name}",
                tofile=f"actual/{name}",
            )
        )
    return "".join(differences)


class SnapshotMismatch(HarnessError):
    """Generated output differs from its reference."""


def check_snapshot(
    root: Path,
    profile: Path,
    actual: Snapshot,
    *,
    update: bool = False,
    only: frozenset[str] | None = None,
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
    changed = tuple(
        sorted(
            name
            for name in expected.keys() | actual.keys()
            if name not in expected
            or name not in actual
            or expected[name] != actual[name]
        )
    )
    for name in expected.keys() - actual.keys():
        (destination / relative_file(name)).unlink()
    if only is None:
        directories = [path for path in destination.rglob("*") if path.is_dir()]
        for directory in sorted(
            directories, key=lambda path: len(path.parts), reverse=True
        ):
            try:
                directory.rmdir()
            except OSError as error:
                # Nonempty directories contain retained reference files.
                if error.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                    raise
    for name, content in actual.items():
        target = destination / relative_file(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return changed


def run_command(
    argv: list[str],
    *,
    cwd: Path,
    log: Path,
    expected_status: int = 0,
) -> subprocess.CompletedProcess[bytes]:
    result = None
    stdout = stderr = b""
    problem = None
    try:
        result = subprocess.run(
            argv, cwd=cwd, capture_output=True, timeout=300, check=False
        )
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
    log.with_suffix(".json").write_text(
        json.dumps(
            {
                "command": argv,
                "cwd": str(cwd),
                "returncode": result.returncode if result is not None else None,
                "error": problem,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
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


def validate_error_run(
    result: subprocess.CompletedProcess[bytes], output: Path
) -> bytes:
    if result.returncode != 1:
        raise HarnessError(f"Expected fatal-error exit 1, got {result.returncode}")
    if b"Traceback (most recent call last)" in result.stderr:
        raise HarnessError("Unexpected Python traceback in fatal-error run")
    if b"Terminating due to previous errors" not in result.stderr:
        raise HarnessError("Missing fatal-diagnostic termination marker")
    if read_tree(output):
        raise HarnessError("Fatal-error run unexpectedly wrote output")
    return normalize_stderr(result.stderr)


def ruff_version(repo: Path) -> str:
    text = (repo / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^\s*-\s+repo:\s*", text)[1:]
    blocks = [
        block
        for block in blocks
        if block.splitlines()[0].strip().strip("\"'")
        == "https://github.com/astral-sh/ruff-pre-commit"
    ]
    if len(blocks) != 1:
        raise HarnessError("Cannot identify the Ruff pre-commit pin")
    match = re.search(r"""(?m)^\s*rev:\s*["']?v?(\d+\.\d+\.\d+)["']?\s*$""", blocks[0])
    if match is None:
        raise HarnessError("Cannot resolve the Ruff pre-commit version")
    return match.group(1)


def format_stubs(
    output: Path,
    repo: Path,
    workspace: Path,
    python_version: tuple[int, int],
) -> None:
    prefix = ["uvx", "--from", f"ruff=={ruff_version(repo)}", "ruff"]
    options = [
        "--config",
        str(repo / "pyproject.toml"),
        "--target-version",
        f"py{python_version[0]}{python_version[1]}",
        "--no-cache",
        str(output),
    ]
    # Preserve repository-root first-party import discovery with explicit config.
    run_command(prefix + ["format"] + options, cwd=repo, log=workspace / "ruff-format")
    run_command(
        prefix + ["check", "--select", "I,RUF022", "--fix"] + options,
        cwd=repo,
        log=workspace / "ruff-check",
    )


def _write_diagnostic(path: Path, content: str) -> None:
    # Replace existing links rather than following them; exclusive creation also
    # refuses a link introduced between unlinking and opening the file.
    path.unlink(missing_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)


@contextmanager
def diagnostics(
    workspace: Path,
    *,
    artifacts: Path | None,
    reference_roots: tuple[Path, ...],
    case_id: str,
    check_name: str,
    expected: Path,
) -> Iterator[None]:
    workspace = workspace.resolve()
    for root in reference_roots:
        root = root.resolve()
        if workspace.is_relative_to(root) or root.is_relative_to(workspace):
            raise HarnessError("Working workspace overlaps a reference tree")
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
            if any(
                candidate.is_relative_to(root.resolve()) for root in reference_roots
            ):
                raise HarnessError("Artifact destination is inside a reference tree")
        if artifact_parent.is_relative_to(workspace):
            raise HarnessError("Artifact destination is inside the working workspace")
    context = f"Case: {case_id}/{check_name}\nReference: {expected.resolve()}\nWorkspace: {workspace}\n"
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        _write_diagnostic(workspace / "context.txt", context)
    except OSError as error:
        raise HarnessError(f"{context}Diagnostic write failed: {error}") from error
    try:
        yield
    except Exception as error:
        summary = context + str(error)
        files = {"failure.txt": summary}
        if isinstance(error, SnapshotMismatch):
            files["diff.patch"] = str(error)
        for name, content in files.items():
            try:
                _write_diagnostic(workspace / name, content)
            except OSError as diagnostic_error:
                summary += f"\nDiagnostic write failed ({workspace / name}): {diagnostic_error}"
        if artifact_parent is not None:
            destination = artifact_parent
            try:
                artifact_parent.mkdir(parents=True, exist_ok=True)
                destination = Path(tempfile.mkdtemp(prefix="run-", dir=artifact_parent))
                for source in workspace.rglob("*"):
                    # Never dereference rejected output symlinks while retaining diagnostics.
                    if source.is_symlink() or not source.is_file():
                        continue
                    target = destination / source.relative_to(workspace)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
            except OSError as retention_error:
                summary += (
                    f"\nArtifact retention failed ({destination}): {retention_error}"
                )
            else:
                summary += f"\nArtifacts: {destination}"
        raise HarnessError(summary) from error


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
        return (
            Path(f"python-{major}.{minor}")
            / f"pybind11-{self.branch}"
            / self.numpy_format
        )

    @property
    def error_profile(self) -> Path:
        return Path(f"pybind11-{self.branch}")


def make_case(
    repo: Path,
    python_version: tuple[int, int],
    branch: str | None,
    numpy_format: str | None,
) -> DemoCase:
    if python_version < (3, 10):
        raise HarnessError("The test harness requires Python >=3.10")
    if branch not in BRANCHES or numpy_format not in NUMPY_FORMATS:
        raise HarnessError(
            "Native tests require --pybind11-branch and --numpy-format; use tox to build the matching demo"
        )
    case = DemoCase(repo.resolve(), python_version, branch, numpy_format)
    resolve_profile(case.stubs_root, case.stub_profile)
    resolve_profile(case.errors_root, case.error_profile)
    return case
