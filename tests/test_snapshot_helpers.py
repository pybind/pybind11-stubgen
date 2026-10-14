import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import snapshot_helpers as h
from snapshot_catalog import load_catalog
from snapshot_test_support import tree_state, write_catalog


def seed_catalog(case):
    write_catalog(
        case.repo,
        {
            case.id: {
                "stubs": {"demo/__init__.pyi": "seed/init.pyi"},
                "errors": {"demo.errors.stderr.txt": "seed/stderr.txt"},
            },
            "unrelated": {
                "stubs": {"demo/__init__.pyi": "seed/init.pyi"},
                "errors": {"demo.errors.stderr.txt": "seed/stderr.txt"},
            },
        },
        {
            "stubs": {"seed/init.pyi": b"original"},
            "errors": {"seed/stderr.txt": b"original"},
        },
    )
    (case.repo / ".git").mkdir()
    (case.repo / ".git/index").write_bytes(b"index sentinel")


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


@pytest.mark.parametrize("unreadable", [".", "sub"])
def test_read_tree_reports_scan_errors(tmp_path, monkeypatch, unreadable):
    write_files(tmp_path, {"sub/a.pyi": b"must not disappear\n"})
    blocked = tmp_path / unreadable
    scandir = os.scandir

    def failing_scandir(path):
        if Path(path) == blocked:
            raise PermissionError("synthetic scan failure")
        return scandir(path)

    monkeypatch.setattr(os, "scandir", failing_scandir)
    with pytest.raises(h.HarnessError) as failure:
        h.read_tree(tmp_path)
    assert str(blocked) in str(failure.value)
    assert isinstance(failure.value.__cause__, PermissionError)


@pytest.mark.parametrize("name", ["", ".", "..", "../x", "/x", "a/../x", "a\\x"])
def test_relative_file_rejects_unsafe_names(name):
    with pytest.raises(h.HarnessError):
        h.relative_file(name)


@pytest.mark.parametrize("status", [0, 1, 2, 127])
def test_run_command_requires_exact_status_and_retains_logs(tmp_path, status):
    command = [
        sys.executable,
        "-c",
        f"import sys; print('diagnostic', file=sys.stderr); sys.exit({status})",
    ]
    if status == 1:
        result = h.run_command(
            command, cwd=tmp_path, log=tmp_path / "process", expected_status=1
        )
        assert result.returncode == 1
    else:
        with pytest.raises(h.HarnessError, match="expected 1"):
            h.run_command(
                command, cwd=tmp_path, log=tmp_path / "process", expected_status=1
            )
    assert b"diagnostic" in (tmp_path / "process.stderr").read_bytes()
    assert json.loads((tmp_path / "process.json").read_text())["returncode"] == status


def test_missing_command_and_timeout_are_diagnostic(tmp_path, monkeypatch):
    with pytest.raises(h.HarnessError):
        h.run_command(
            [str(tmp_path / "missing-command")], cwd=tmp_path, log=tmp_path / "missing"
        )
    assert (tmp_path / "missing.json").is_file()

    def timeout(argv, **kwargs):
        assert kwargs["timeout"] == 300
        raise subprocess.TimeoutExpired(argv, 300, output=b"partial", stderr=b"stuck")

    monkeypatch.setattr(h.subprocess, "run", timeout)
    with pytest.raises(h.HarnessError, match="300"):
        h.run_command(["fake"], cwd=tmp_path, log=tmp_path / "timeout")
    assert (tmp_path / "timeout.stdout").read_bytes() == b"partial"
    assert (tmp_path / "timeout.stderr").read_bytes() == b"stuck"


@pytest.mark.parametrize("suffix", [".stdout", ".stderr", ".json"])
@pytest.mark.parametrize("status", [0, 2])
def test_run_command_log_failure_preserves_context_and_other_logs(
    tmp_path, suffix, status
):
    log = tmp_path / "process"
    blocked = log.with_suffix(suffix)
    blocked.mkdir()
    command = [
        sys.executable,
        "-c",
        "import sys; print('captured output'); "
        f"print('captured error', file=sys.stderr); sys.exit({status})",
    ]
    with pytest.raises(h.HarnessError) as failure:
        h.run_command(command, cwd=tmp_path, log=log)
    summary = str(failure.value)
    assert repr(command) in summary
    assert f"exit {status}, expected 0" in summary
    assert "stdout:\ncaptured output\n" in summary
    assert "stderr:\ncaptured error\n" in summary
    assert "Log persistence failed" in summary
    assert str(blocked) in summary and "[Errno" in summary
    if suffix != ".stdout":
        assert log.with_suffix(".stdout").read_bytes() == b"captured output\n"
    if suffix != ".stderr":
        assert log.with_suffix(".stderr").read_bytes() == b"captured error\n"
    if suffix != ".json":
        metadata = json.loads(log.with_suffix(".json").read_text())
        assert metadata == {
            "command": command,
            "cwd": str(tmp_path),
            "returncode": status,
            "error": None if status == 0 else "exit 2, expected 0",
        }


@pytest.mark.parametrize("suffix", [".stdout", ".stderr", ".json"])
def test_run_command_log_failure_preserves_timeout(tmp_path, monkeypatch, suffix):
    log = tmp_path / "timeout"
    blocked = log.with_suffix(suffix)
    blocked.mkdir()

    def timeout(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 300, output=b"partial", stderr=b"stuck")

    monkeypatch.setattr(h.subprocess, "run", timeout)
    with pytest.raises(h.HarnessError) as failure:
        h.run_command(["fake"], cwd=tmp_path, log=log)
    summary = str(failure.value)
    assert "['fake']: timed out after 300 seconds" in summary
    assert "stdout:\npartial" in summary and "stderr:\nstuck" in summary
    assert "Log persistence failed" in summary and str(blocked) in summary
    if suffix != ".json":
        metadata = json.loads(log.with_suffix(".json").read_text())
        assert metadata["returncode"] is None
        assert metadata["error"] == "timed out after 300 seconds"


@pytest.mark.parametrize("missing_command", [False, True])
def test_run_command_log_directory_failure_preserves_process_context(
    tmp_path, missing_command
):
    blocked = tmp_path / "not-a-directory"
    blocked.write_bytes(b"keep")
    command = (
        [str(tmp_path / "missing-command")]
        if missing_command
        else [sys.executable, "-c", "import sys; print('captured'); sys.exit(2)"]
    )
    with pytest.raises(h.HarnessError) as failure:
        h.run_command(command, cwd=tmp_path, log=blocked / "process")
    summary = str(failure.value)
    assert repr(command) in summary
    if missing_command:
        assert "No such file or directory" in summary
    else:
        assert "exit 2, expected 0" in summary
        assert "stdout:\ncaptured\n" in summary
    assert "Log persistence failed" in summary and str(blocked) in summary
    assert blocked.read_bytes() == b"keep"


def test_run_command_log_failure_survives_outer_diagnostics(tmp_path):
    workspace = tmp_path / "work"
    expected = tmp_path / "refs/case"
    command = [
        sys.executable,
        "-c",
        "import sys; print('captured output'); "
        "print('captured error', file=sys.stderr); sys.exit(2)",
    ]
    with pytest.raises(h.HarnessError) as failure:
        with h.diagnostics(
            workspace,
            artifacts=tmp_path / "artifacts",
            reference_roots=(tmp_path / "refs",),
            case_id="case",
            check_name="stubs",
            expected=expected,
        ):
            (workspace / "process.stderr").mkdir()
            h.run_command(command, cwd=workspace, log=workspace / "process")
    summary = str(failure.value)
    assert "case/stubs" in summary and str(expected) in summary
    assert "Artifacts:" in summary
    runs = list((tmp_path / "artifacts/case/stubs").iterdir())
    assert len(runs) == 1
    retained = (runs[0] / "failure.txt").read_text()
    assert retained == (workspace / "failure.txt").read_text()
    for text in (summary, retained):
        assert repr(command) in text
        assert "exit 2, expected 0" in text
        assert "stdout:\ncaptured output\n" in text
        assert "stderr:\ncaptured error\n" in text
        assert "Log persistence failed" in text
        assert str(workspace / "process.stderr") in text
    assert (runs[0] / "process.stdout").read_bytes() == b"captured output\n"
    assert json.loads((runs[0] / "process.json").read_text())["returncode"] == 2


@pytest.mark.parametrize(
    "status,stderr,files",
    [
        (0, b"Terminating due to previous errors", {}),
        (2, b"Terminating due to previous errors", {}),
        (
            1,
            b"Traceback (most recent call last):\nTerminating due to previous errors",
            {},
        ),
        (1, b"unrelated failure", {}),
        (1, b"Terminating due to previous errors", {"unexpected.pyi": b"x"}),
    ],
)
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
    assert (
        h.normalize_stderr(b"ordinary text 123 abc 0xZZ")
        == b"ordinary text 123 abc 0xZZ"
    )


def test_ruff_pin_configuration_target_order_and_cache_policy(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    write_files(
        repo,
        {
            ".pre-commit-config.yaml": (
                b"repos:\n  - repo: unrelated\n    rev: v99.0.0\n"
                b"  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.15.20\n"
            ),
            "pyproject.toml": b"[tool.ruff]\nline-length = 88\n",
        },
    )
    commands = []

    def record(argv, **kwargs):
        commands.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(h, "run_command", record)
    h.format_stubs(tmp_path / "output", repo, tmp_path, (3, 12))
    assert len(commands) == 2
    assert commands[0][0][:5] == ["uvx", "--from", "ruff==0.15.20", "ruff", "format"]
    assert commands[1][0][4:8] == ["check", "--select", "I,RUF022", "--fix"]
    for (argv, kwargs), log_name in zip(commands, ("ruff-format", "ruff-check")):
        assert argv[argv.index("--config") + 1] == str(repo / "pyproject.toml")
        assert argv[argv.index("--target-version") + 1] == "py312"
        assert "--no-cache" in argv
        assert argv[-1] == str(tmp_path / "output")
        # Ruff's cwd controls first-party discovery even with explicit config.
        assert kwargs["cwd"] == repo
        assert kwargs["log"] == tmp_path / log_name


def test_invalid_ruff_pin_and_formatter_failure_are_not_ignored(tmp_path, monkeypatch):
    write_files(tmp_path, {".pre-commit-config.yaml": b"repos: []\n"})
    with pytest.raises(h.HarnessError, match="Ruff"):
        h.ruff_version(tmp_path)
    write_files(
        tmp_path,
        {
            ".pre-commit-config.yaml": (
                b"repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.15.20\n"
            )
        },
    )

    def fail(argv, **kwargs):
        raise h.HarnessError("formatter failed")

    monkeypatch.setattr(h, "run_command", fail)
    with pytest.raises(h.HarnessError, match="formatter failed"):
        h.format_stubs(tmp_path / "output", tmp_path, tmp_path, (3, 10))


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
        with h.diagnostics(
            tmp_path / "work",
            artifacts=destination,
            reference_roots=(refs,),
            case_id="case",
            check_name="stubs",
            expected=refs / "case",
        ):
            raise AssertionError("body must not run")
    assert h.read_tree(refs) == {"case/x.pyi": b"keep"}


def test_failure_artifacts_include_output_diff_and_context(tmp_path):
    workspace = tmp_path / "work"
    refs = tmp_path / "refs"
    write_files(refs / "case", {"x.pyi": b"expected"})
    with pytest.raises(h.HarnessError, match="Artifacts:"):
        with h.diagnostics(
            workspace,
            artifacts=tmp_path / "artifacts",
            reference_roots=(refs,),
            case_id="case",
            check_name="stubs",
            expected=refs / "case",
        ):
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
        with h.diagnostics(
            tmp_path,
            artifacts=tmp_path / "artifacts",
            reference_roots=(tmp_path / "refs",),
            case_id="case",
            check_name="stubs",
            expected=tmp_path / "refs/case",
        ):
            raise AssertionError("body must not run")


@pytest.mark.parametrize("component", ["case_id", "check_name"])
@pytest.mark.parametrize("value", ["", "..", "../escape", "/absolute", "nested/name"])
def test_diagnostics_rejects_invalid_identifiers_before_writing(
    tmp_path, component, value
):
    identifiers = {"case_id": "case", "check_name": "stubs", component: value}
    with pytest.raises(h.HarnessError):
        with h.diagnostics(
            tmp_path / "work",
            artifacts=tmp_path / "artifacts",
            reference_roots=(tmp_path / "refs",),
            expected=tmp_path / "refs/case",
            **identifiers,
        ):
            pytest.fail("body must not run")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("artifacts_enabled", [False, True])
def test_success_records_context_without_retaining_artifacts(
    tmp_path, artifacts_enabled
):
    workspace = tmp_path / "work"
    artifacts = tmp_path / "artifacts"
    expected = tmp_path / "refs/case"
    with h.diagnostics(
        workspace,
        artifacts=artifacts if artifacts_enabled else None,
        reference_roots=(tmp_path / "refs",),
        case_id="case",
        check_name="stubs",
        expected=expected,
    ):
        assert (workspace / "context.txt").read_text() == (
            f"Case: case/stubs\nReference: {expected}\nWorkspace: {workspace}\n"
        )
    assert not artifacts.exists()
    assert not (workspace / "failure.txt").exists()


def test_failure_without_artifacts_preserves_original_diagnostics(tmp_path):
    error = RuntimeError("generation failed")
    workspace = tmp_path / "work"
    expected = tmp_path / "refs/case"
    with pytest.raises(h.HarnessError) as failure:
        with h.diagnostics(
            workspace,
            artifacts=None,
            reference_roots=(tmp_path / "refs",),
            case_id="case",
            check_name="stubs",
            expected=expected,
        ):
            raise error
    summary = str(failure.value)
    assert failure.value.__cause__ is error
    assert "generation failed" in summary
    assert str(workspace) in summary and str(expected) in summary
    assert "Artifacts:" not in summary
    assert (workspace / "failure.txt").read_text() == summary
    assert not (workspace / "diff.patch").exists()


def test_failure_artifacts_are_unique_and_skip_symlinks_and_special_files(tmp_path):
    refs = tmp_path / "refs"
    write_files(refs / "case", {"x.pyi": b"keep"})
    for index in range(2):
        workspace = tmp_path / f"work-{index}"
        with pytest.raises(h.HarnessError, match="rejected output"):
            with h.diagnostics(
                workspace,
                artifacts=tmp_path / "artifacts",
                reference_roots=(refs,),
                case_id="case",
                check_name="stubs",
                expected=refs / "case",
            ):
                write_files(workspace / "output", {"x.pyi": str(index).encode()})
                (workspace / "linked.pyi").symlink_to(refs / "case/x.pyi")
                (workspace / "linked-dir").symlink_to(refs, target_is_directory=True)
                (workspace / "broken").symlink_to(tmp_path / "absent")
                os.mkfifo(workspace / "fifo")
                raise h.HarnessError("rejected output")
    runs = list((tmp_path / "artifacts/case/stubs").iterdir())
    assert len(runs) == 2
    assert {(run / "output/x.pyi").read_bytes() for run in runs} == {b"0", b"1"}
    for run in runs:
        assert set(h.read_tree(run)) == {"output/x.pyi", "context.txt", "failure.txt"}
    assert h.read_tree(refs) == {"case/x.pyi": b"keep"}


@pytest.mark.parametrize("relation", ["inside", "same", "ancestor"])
@pytest.mark.parametrize("through_alias", [False, True])
def test_diagnostics_rejects_reference_overlapping_workspaces(
    tmp_path, relation, through_alias
):
    refs = tmp_path / "refs"
    write_files(refs / "case", {"x.pyi": b"keep"})
    workspace = {"inside": refs / "work", "same": refs, "ancestor": tmp_path}[relation]
    if through_alias:
        alias = tmp_path / "alias"
        alias.symlink_to(workspace, target_is_directory=True)
        workspace = alias
    body_ran = False
    with pytest.raises(h.HarnessError) as failure:
        with h.diagnostics(
            workspace,
            artifacts=None,
            reference_roots=(refs,),
            case_id="case",
            check_name="stubs",
            expected=refs / "case",
        ):
            body_ran = True
            raise h.SnapshotMismatch("Changed: x.pyi\n")
    assert h.read_tree(refs) == {"case/x.pyi": b"keep"}
    assert not body_ran
    assert "reference" in str(failure.value)


@pytest.mark.parametrize("name", ["context.txt", "failure.txt", "diff.patch"])
def test_diagnostic_writes_do_not_follow_reference_symlinks(tmp_path, name):
    refs = tmp_path / "refs"
    write_files(refs / "case", {"x.pyi": b"keep"})
    workspace = tmp_path / "work"
    workspace.mkdir()
    if name == "context.txt":
        (workspace / name).symlink_to(refs / "case/x.pyi")
    error = h.SnapshotMismatch("Changed: x.pyi\n")
    with pytest.raises(h.HarnessError) as failure:
        with h.diagnostics(
            workspace,
            artifacts=tmp_path / "artifacts",
            reference_roots=(refs,),
            case_id="case",
            check_name="stubs",
            expected=refs / "case",
        ):
            if name != "context.txt":
                (workspace / name).symlink_to(refs / "case/x.pyi")
            raise error
    assert h.read_tree(refs) == {"case/x.pyi": b"keep"}
    assert failure.value.__cause__ is error
    assert not (workspace / name).is_symlink()
    assert "Artifacts:" in str(failure.value)


@pytest.mark.parametrize("name", ["context.txt", "failure.txt", "diff.patch"])
def test_diagnostic_write_errors_preserve_context(tmp_path, name):
    workspace = tmp_path / "work"
    blocked = workspace / name
    blocked.mkdir(parents=True)
    expected = tmp_path / "refs/case"
    error = h.SnapshotMismatch("Changed: x.pyi\n")
    body_ran = False
    with pytest.raises(h.HarnessError) as failure:
        with h.diagnostics(
            workspace,
            artifacts=tmp_path / "artifacts",
            reference_roots=(tmp_path / "refs",),
            case_id="case",
            check_name="stubs",
            expected=expected,
        ):
            body_ran = True
            raise error
    summary = str(failure.value)
    assert "case/stubs" in summary
    assert str(expected) in summary and str(workspace) in summary
    assert str(blocked) in summary
    assert "Diagnostic write failed" in summary
    if name == "context.txt":
        assert not body_ran
        assert isinstance(failure.value.__cause__, OSError)
    else:
        assert failure.value.__cause__ is error
        assert "Changed: x.pyi" in summary
        assert "Artifacts:" in summary


def test_artifact_retention_errors_preserve_original_failure_and_locations(tmp_path):
    workspace = tmp_path / "work"
    artifacts = tmp_path / "artifacts"
    artifacts.write_bytes(b"not a directory")
    expected = tmp_path / "refs/case"
    error = h.SnapshotMismatch("Changed: x.pyi\n")
    with pytest.raises(h.HarnessError) as failure:
        with h.diagnostics(
            workspace,
            artifacts=artifacts,
            reference_roots=(tmp_path / "refs",),
            case_id="case",
            check_name="stubs",
            expected=expected,
        ):
            raise error
    summary = str(failure.value)
    assert failure.value.__cause__ is error
    assert "Changed: x.pyi" in summary and "case/stubs" in summary
    assert str(workspace) in summary and str(expected) in summary
    assert "Artifact retention failed" in summary
    assert str(artifacts / "case/stubs") in summary
    assert "Changed: x.pyi" in (workspace / "failure.txt").read_text()
    assert artifacts.read_bytes() == b"not a directory"


@pytest.mark.parametrize(
    "branch,mode",
    [(None, None), ("v9.9", "numpy-array-use-type-var"), ("v3.0", "invalid-format")],
)
def test_case_requires_explicit_recognized_configuration(tmp_path, branch, mode):
    with pytest.raises(h.HarnessError):
        h.make_case(tmp_path, (3, 13), branch, mode)


def test_case_requires_existing_profiles_and_uses_runtime_python(tmp_path):
    mode = "numpy-array-wrap-with-annotated"
    with pytest.raises(h.HarnessError):
        h.make_case(tmp_path, (3, 13), "v3.0", mode)
    seed_catalog(h.DemoCase(tmp_path, (3, 13), "v3.0", mode))
    case = h.make_case(tmp_path, (3, 13), "v3.0", mode)
    assert case.catalog_path == tmp_path / "tests/snapshot_cases.toml"
    assert case.id == "python-3.13-pybind11-v3.0-numpy-array-wrap-with-annotated"
    with pytest.raises(h.HarnessError, match="python-3.12"):
        h.make_case(tmp_path, (3, 12), "v3.0", mode)


@pytest.mark.parametrize("failure_stage", ["generator", "formatter"])
def test_success_update_never_accepts_failed_generation_or_formatting(
    tmp_path, monkeypatch, failure_stage
):
    import test_demo_stubs as integration

    repo = tmp_path / "repo"
    case = h.DemoCase(repo, (3, 13), "v3.0", "numpy-array-wrap-with-annotated")
    seed_catalog(case)
    before = tree_state(case.repo)
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
        integration.test_demo_stubs(
            case, tmp_path / "work", True, None, messages.append
        )
    assert tree_state(case.repo) == before
    context = (tmp_path / "work/failure.txt").read_text()
    assert str(case.catalog_path) in context
    assert "demo/__init__.pyi" in context
    assert str(case.stubs_root / "seed/init.pyi") in context
    assert messages == []


def test_error_update_rejects_traceback_even_with_exit_one(tmp_path, monkeypatch):
    import test_demo_errors as integration

    case = h.DemoCase(tmp_path / "repo", (3, 13), "v3.0", "numpy-array-use-type-var")
    seed_catalog(case)
    before = tree_state(case.repo)

    def traceback_result(argv, **kwargs):
        assert argv[:4] == [sys.executable, "-I", "-m", "pybind11_stubgen"]
        assert kwargs["expected_status"] == 1
        return subprocess.CompletedProcess(
            argv, 1, b"", b"Traceback (most recent call last):\n"
        )

    monkeypatch.setattr(integration, "run_command", traceback_result)
    with pytest.raises(h.HarnessError, match="traceback"):
        integration.test_demo_errors(case, tmp_path / "work", True, None, print)
    assert tree_state(case.repo) == before
    context = (tmp_path / "work/failure.txt").read_text()
    assert str(case.catalog_path) in context
    assert str(case.errors_root / "seed/stderr.txt") in context


@pytest.mark.parametrize("kind", ["stubs", "errors"])
@pytest.mark.parametrize("update", [False, True])
def test_integration_check_and_update_paths_with_synthetic_output(
    tmp_path, monkeypatch, kind, update
):
    import test_demo_errors
    import test_demo_stubs

    case = h.DemoCase(
        tmp_path / "repo", (3, 13), "v3.0", "numpy-array-wrap-with-annotated"
    )
    integration = test_demo_stubs if kind == "stubs" else test_demo_errors
    run_test = (
        integration.test_demo_stubs if kind == "stubs" else integration.test_demo_errors
    )
    seed_catalog(case)
    before = tree_state(case.repo)
    original = load_catalog(case.repo)
    filename = "demo/__init__.pyi" if kind == "stubs" else "demo.errors.stderr.txt"
    new_content = (
        b"new stubs\n"
        if kind == "stubs"
        else b"object 0x1234abcd5678\nTerminating due to previous errors\n"
    )
    messages = []

    def generate(argv, **kwargs):
        if kind == "stubs":
            write_files(kwargs["cwd"] / "output", {filename: new_content})
            return subprocess.CompletedProcess(argv, 0, b"", b"")
        return subprocess.CompletedProcess(
            argv, 1, b"", b"object 0xABCD\nTerminating due to previous errors\n"
        )

    monkeypatch.setattr(integration, "run_command", generate)
    if kind == "stubs":
        monkeypatch.setattr(integration, "format_stubs", lambda *args: None)
    if update:
        run_test(case, tmp_path / "work", True, None, messages.append)
        fresh = load_catalog(case.repo)
        assert fresh.snapshot(case.id, kind) == {filename: new_content}
        other_kind = "errors" if kind == "stubs" else "stubs"
        assert fresh.snapshot(case.id, other_kind) == original.snapshot(
            case.id, other_kind
        )
        for other_kind in ("stubs", "errors"):
            assert fresh.snapshot("unrelated", other_kind) == original.snapshot(
                "unrelated", other_kind
            )
        assert (case.repo / ".git/index").read_bytes() == b"index sentinel"
        assert messages and str(case.catalog_path) in messages[0]
    else:
        with pytest.raises(h.HarnessError, match="Changed:"):
            run_test(case, tmp_path / "work", False, None, messages.append)
        assert tree_state(case.repo) == before
        assert messages == []


@pytest.mark.parametrize("empty_at", ["generator", "formatter"])
def test_empty_output_cannot_erase_references(tmp_path, monkeypatch, empty_at):
    import test_demo_stubs as integration

    case = h.DemoCase(
        tmp_path / "repo", (3, 13), "v3.0", "numpy-array-wrap-with-annotated"
    )
    seed_catalog(case)
    before = tree_state(case.repo)

    def generate(argv, **kwargs):
        if empty_at == "formatter":
            write_files(kwargs["cwd"] / "output", {"demo/__init__.pyi": b"new"})
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    def erase_output(output, repo, workspace, python_version):
        (output / "demo/__init__.pyi").unlink()

    monkeypatch.setattr(integration, "run_command", generate)
    monkeypatch.setattr(integration, "format_stubs", erase_output)
    expected_diagnostic = (
        "Successful demo generation did not produce demo/__init__.pyi"
        if empty_at == "generator"
        else "Normalized output lost demo/__init__.pyi"
    )
    with pytest.raises(h.HarnessError, match=expected_diagnostic):
        integration.test_demo_stubs(case, tmp_path / "work", True, None, print)
    assert tree_state(case.repo) == before
