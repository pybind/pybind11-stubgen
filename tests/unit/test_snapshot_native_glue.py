import subprocess

import pytest

from snapshot_catalog import load_catalog
from snapshot_helpers import DemoCase, HarnessError, diagnostics, make_case
from snapshot_test_support import tree_state, write_catalog


def native_repo(tmp_path):
    cases = [
        DemoCase(tmp_path / "repo", (3, 13), "v3.0", mode)
        for mode in ("numpy-array-wrap-with-annotated", "numpy-array-use-type-var")
    ]
    write_catalog(
        cases[0].repo,
        {
            case.id: {
                "stubs": {"demo/__init__.pyi": "seed/init.pyi"},
                "errors": {"demo.errors.stderr.txt": "seed/stderr.txt"},
            }
            for case in cases
        },
        {
            "stubs": {"seed/init.pyi": b"old"},
            "errors": {"seed/stderr.txt": b"errors"},
        },
    )
    return cases


@pytest.mark.parametrize("fault", ["missing", "unknown", "symlink"])
def test_selection_preflight_names_case_catalog_and_keeps_cause(tmp_path, fault):
    case, _ = native_repo(tmp_path)
    path = case.repo / "tests/snapshot_cases.toml"
    if fault == "missing":
        path.unlink()
    elif fault == "unknown":
        case = DemoCase(case.repo, (3, 12), case.branch, case.numpy_format)
    else:
        saved = path.with_suffix(".saved")
        path.rename(saved)
        path.symlink_to(saved)
    before = tree_state(case.repo)
    with pytest.raises(HarnessError) as exc:
        make_case(case.repo, case.python_version, case.branch, case.numpy_format)
    assert case.id in str(exc.value)
    assert str(path) in str(exc.value)
    assert exc.value.__cause__ is not None
    assert tree_state(case.repo) == before


@pytest.mark.parametrize("location", ["catalog", "parent", "artifact-symlink"])
def test_catalog_is_protected_before_native_reference_writes(
    tmp_path, monkeypatch, location
):
    import test_demo_stubs as integration

    case, _ = native_repo(tmp_path)
    catalog = case.repo / "tests/snapshot_cases.toml"
    workspace = tmp_path / "work"
    artifacts = None
    if location == "catalog":
        workspace = catalog
    elif location == "parent":
        workspace = catalog.parent
    else:
        alias = tmp_path / "catalog-alias"
        alias.symlink_to(catalog)
        artifacts = alias / "nested"
    before = tree_state(case.repo)

    def unexpected_process(*args, **kwargs):
        pytest.fail("process started before reference protection")

    monkeypatch.setattr(integration, "run_command", unexpected_process)
    with pytest.raises(HarnessError, match="reference tree"):
        integration.test_demo_stubs(case, workspace, True, artifacts, print)
    assert tree_state(case.repo) == before


def test_diagnostic_details_survive_secondary_write_failure(tmp_path, monkeypatch):
    import snapshot_helpers as helpers

    case, _ = native_repo(tmp_path)
    catalog = load_catalog(case.repo)
    details = catalog.context(case.id, "stubs")
    original = helpers._write_diagnostic

    def fail_summary(path, content):
        if path.name == "failure.txt":
            raise OSError("secondary diagnostic failure")
        original(path, content)

    monkeypatch.setattr(helpers, "_write_diagnostic", fail_summary)
    primary = HarnessError("generator failed")
    with pytest.raises(HarnessError) as exc:
        with diagnostics(
            tmp_path / "work",
            artifacts=None,
            reference_roots=(catalog.path, case.stubs_root, case.errors_root),
            case_id=case.id,
            check_name="stubs",
            expected=catalog.path,
            reference_details=details,
        ):
            raise primary
    assert exc.value.__cause__ is primary
    assert details in str(exc.value)
    assert "secondary diagnostic failure" in str(exc.value)
    assert details in (tmp_path / "work/context.txt").read_text()


def test_two_native_modes_update_serially_with_fresh_mappings(tmp_path, monkeypatch):
    import test_demo_stubs as integration

    first, second = native_repo(tmp_path)
    before = load_catalog(first.repo)

    def generate(argv, **kwargs):
        target = kwargs["cwd"] / "output/demo/__init__.pyi"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"new")
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr(integration, "run_command", generate)
    monkeypatch.setattr(integration, "format_stubs", lambda *args: None)
    messages = []
    integration.test_demo_stubs(first, tmp_path / "first", True, None, messages.append)
    intermediate = load_catalog(first.repo)
    assert intermediate.snapshot(second.id, "stubs") == {"demo/__init__.pyi": b"old"}
    integration.test_demo_stubs(
        second, tmp_path / "second", True, None, messages.append
    )
    after = load_catalog(first.repo)
    for case in (first, second):
        assert after.snapshot(case.id, "stubs") == {"demo/__init__.pyi": b"new"}
        assert after.mapping(case.id, "stubs") == intermediate.mapping(
            first.id, "stubs"
        )
        assert after.snapshot(case.id, "errors") == before.snapshot(case.id, "errors")
    assert len(after.pools["stubs"]) == 1
    assert len(messages) == 2
