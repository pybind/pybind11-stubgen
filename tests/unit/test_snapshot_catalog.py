from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from snapshot_catalog import (
    changed_names,
    check_case,
    load_catalog,
    parse_model,
    safe_path,
    select_expected,
    validate_name,
)
from snapshot_helpers import HarnessError, SnapshotMismatch
from snapshot_test_support import tree_state, write_catalog


def test_shipped_catalog_has_complete_literal_coverage_and_shared_payloads():
    catalog = load_catalog(Path(__file__).resolve().parents[2])
    annotated = "numpy-array-wrap-with-annotated"
    type_var = "numpy-array-use-type-var"
    cases = [
        ((3, 10), "v3.0", annotated),
        ((3, 11), "v3.0", annotated),
        ((3, 12), "v3.0", annotated),
        ((3, 13), "v3.0", annotated),
        ((3, 13), "v3.0", type_var),
        ((3, 10), "v2.13", annotated),
        ((3, 11), "v2.13", annotated),
        ((3, 12), "v2.13", annotated),
        ((3, 13), "v2.13", annotated),
        ((3, 13), "v2.13", type_var),
        ((3, 13), "v2.9", annotated),
        ((3, 13), "v2.11", annotated),
        ((3, 13), "v2.12", annotated),
    ]
    assert set(catalog.cases) == {
        f"python-{major}.{minor}-pybind11-{branch}-{mode}"
        for (major, minor), branch, mode in cases
    }
    for kind, required in (
        ("stubs", "demo/__init__.pyi"),
        ("errors", "demo.errors.stderr.txt"),
    ):
        referenced = set()
        variants = {}
        for case in catalog.cases:
            mapping = catalog.mapping(case, kind)
            assert required in mapping
            for name, reference in mapping.items():
                referenced.add(reference)
                key = (name, catalog.pools[kind][reference])
                assert variants.setdefault(key, reference) == reference
        assert referenced == set(catalog.pools[kind])
        assert all(
            entry[0] in ("file", "dir")
            for entry in tree_state(catalog.repo / "tests" / kind).values()
        )


def sample(tmp_path):
    cases = {
        "a": {"stubs": {"demo/a.pyi": "shared/a.pyi"}, "errors": {}},
        "b": {"stubs": {"demo/a.pyi": "shared/a.pyi"}, "errors": {}},
    }
    repo = write_catalog(
        tmp_path / "repo",
        cases,
        {"stubs": {"shared/a.pyi": b"old\n", "unused.pyi": b"inert\n"}},
    )
    (repo / ".git").mkdir()
    (repo / ".git/index").write_bytes(b"inert index sentinel\0")
    return repo


def test_empty_catalog_fixture_round_trips(tmp_path):
    repo = write_catalog(tmp_path / "repo", {}, {})

    catalog = load_catalog(repo)

    assert catalog.cases == {}
    assert catalog.pools == {"stubs": {}, "errors": {}}
    assert (repo / "tests/stubs").is_dir()
    assert (repo / "tests/errors").is_dir()


def test_literal_selection_and_read_only_failure(tmp_path):
    repo = sample(tmp_path)
    before = tree_state(repo)
    catalog = load_catalog(repo)
    assert catalog.snapshot("a", "stubs") == {"demo/a.pyi": b"old\n"}
    assert catalog.snapshot("b", "stubs") == {"demo/a.pyi": b"old\n"}
    assert catalog.snapshot("a", "errors") == {}
    assert catalog.raw == (repo / "tests/snapshot_cases.toml").read_bytes()
    assert catalog.repo == repo.resolve()
    mapping = catalog.mapping("a", "stubs")
    mapping.clear()
    assert catalog.mapping("a", "stubs") == {"demo/a.pyi": "shared/a.pyi"}
    assert check_case(repo, "a", "stubs", {"demo/a.pyi": b"old\n"}).endswith(
        "changed: ()"
    )
    with pytest.raises(SnapshotMismatch) as exc:
        check_case(repo, "a", "stubs", {"demo/extra.pyi": b"new\n"})
    message = str(exc.value)
    assert "Missing: demo/a.pyi" in message
    assert "Unexpected: demo/extra.pyi" in message
    assert "<unmapped>" in message
    assert str(repo / "tests/stubs/shared/a.pyi") in message
    assert "Case: a/stubs" in message
    assert tree_state(repo) == before


@pytest.mark.parametrize("name", ["", "../x", "/x", "a\\b", "a//b", "a/./b", "x\0y"])
def test_unsafe_reference_names_are_rejected(tmp_path, name):
    repo = sample(tmp_path)
    path = repo / "tests/snapshot_cases.toml"
    text = path.read_text().replace('"shared/a.pyi"', json.dumps(name))
    path.write_text(text)
    before = tree_state(repo)
    with pytest.raises(HarnessError, match="[Uu]nsafe|[Ii]nvalid") as exc:
        parse_model(text.encode(), path)
    assert "cases" in str(exc.value)
    assert "stubs" in str(exc.value)
    assert "demo/a.pyi" in str(exc.value)
    with pytest.raises(HarnessError):
        load_catalog(repo)
    assert tree_state(repo) == before


@pytest.mark.parametrize(
    "raw, clue",
    [
        (b"format = true\n[cases.a]\nstubs = {}\nerrors = {}\n", "format"),
        (b"format = 2\n[cases.a]\nstubs = {}\nerrors = {}\n", "format"),
        (b"format = 1\ncases = 2\n", "cases"),
        (b"format = 1\n[cases.a]\nstubs = 2\nerrors = {}\n", "stubs"),
        (b"format = 1\n[cases.a.stubs]\n", "errors"),
        (b"format = 1\nformat = 1\n[cases]\n", "TOML"),
        (b"[cases]\n", "format"),
        (b"format = 1\n", "cases"),
        (b"format = 1\nextra = 0\n[cases]\n", "extra"),
        (b"format = 1\n[cases]\na = 3\n", "cases.*a"),
        (b"format = 1\n[cases.a]\nstubs = {}\nerrors = {}\nextra = {}\n", "extra"),
        (b"format = 1\n[cases.a]\nstubs = {x = 2}\nerrors = {}\n", "stubs.*x"),
        (b'format = 1\n[cases.a]\nstubs = {"../x" = "a"}\nerrors = {}\n', "Unsafe"),
        (b'format = 1\n[cases."a/b"]\nstubs = {}\nerrors = {}\n', "case identifier"),
        (
            b'format = 1\n[cases.a]\nstubs = {x = "a", "x/y" = "b"}\nerrors = {}\n',
            "Conflicting.*x/y",
        ),
        (
            b'format = 1\n[cases.a]\nstubs = {x = "a", y = "a"}\nerrors = {}\n',
            "ownership.*a",
        ),
        (
            b'format = 1\n[cases.a]\nstubs = {x = "a"}\nerrors = {}\n[cases.b]\nstubs = {y = "a"}\nerrors = {}\n',
            "ownership.*a",
        ),
        (b"\xff", "TOML"),
    ],
)
def test_schema_failures(tmp_path, raw, clue):
    path = tmp_path / "snapshot_cases.toml"
    with pytest.raises(HarnessError, match=clue) as exc:
        parse_model(raw, path)
    assert str(path) in str(exc.value)


def test_pure_model_allows_planned_files_and_separate_kind_ownership(tmp_path):
    raw = b'format = 1\r\n[cases.a]\r\nstubs = {x = "shared"}\r\nerrors = {y = "shared"}\r\n'
    assert parse_model(raw, tmp_path / "absent.toml") == {
        "a": {"stubs": {"x": "shared"}, "errors": {"y": "shared"}}
    }


@pytest.mark.parametrize(
    "relative, dangling",
    [
        ("tests/snapshot_cases.toml", False),
        ("tests", False),
        ("tests/stubs", False),
        ("tests/errors", False),
        ("tests/stubs/shared", False),
        ("tests/stubs/shared/a.pyi", False),
        ("tests/stubs/unused.pyi", False),
        ("tests/stubs/unused.pyi", True),
        ("tests/snapshot_cases.toml", True),
    ],
)
def test_symlinks_are_rejected_without_outside_writes(tmp_path, relative, dangling):
    repo = sample(tmp_path)
    path = repo / relative
    outside = tmp_path / "outside"
    if path.is_dir():
        shutil.copytree(path, outside)
        shutil.rmtree(path)
    else:
        outside.write_bytes(path.read_bytes())
        path.unlink()
    path.symlink_to(tmp_path / "missing" if dangling else outside)
    before = tree_state(tmp_path)
    with pytest.raises(HarnessError, match="symlink") as exc:
        load_catalog(repo)
    assert str(path) in str(exc.value)
    assert tree_state(tmp_path) == before


@pytest.mark.parametrize(
    "relative, clue",
    [
        ("tests/snapshot_cases.toml", "snapshot_cases.toml"),
        ("tests/stubs", "stubs"),
        ("tests/errors", "errors"),
        ("tests/stubs/shared/a.pyi", "cases.*a.*stubs.*demo/a.pyi"),
    ],
)
def test_missing_roots_and_mapped_files(tmp_path, relative, clue):
    repo = sample(tmp_path)
    path = repo / relative
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    before = tree_state(repo)
    with pytest.raises(HarnessError, match=clue) as exc:
        load_catalog(repo)
    assert str(path) in str(exc.value)
    assert tree_state(repo) == before


@pytest.mark.parametrize(
    "relative, replacement",
    [
        ("tests/snapshot_cases.toml", "directory"),
        ("tests/stubs", "file"),
        ("tests/stubs/shared/a.pyi", "directory"),
        ("tests/stubs/unused.pyi", "fifo"),
        ("tests/errors/special", "fifo"),
    ],
)
def test_nonregular_entries(tmp_path, relative, replacement):
    repo = sample(tmp_path)
    path = repo / relative
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    if replacement == "directory":
        path.mkdir()
    elif replacement == "file":
        path.write_bytes(b"not a directory")
    else:
        os.mkfifo(path)
    before = tree_state(repo)
    with pytest.raises(HarnessError, match="directory|file|entry") as exc:
        load_catalog(repo)
    assert str(path) in str(exc.value)
    assert tree_state(repo) == before


def test_whole_catalog_is_validated_before_selection(tmp_path):
    repo = sample(tmp_path)
    path = repo / "tests/snapshot_cases.toml"
    path.write_text(
        path.read_text().replace(
            '[cases."b".errors]', '[cases."b".errors]\n"err" = "absent"'
        )
    )
    with pytest.raises(HarnessError, match="cases.*b.*errors.*err"):
        check_case(repo, "a", "stubs", {"demo/a.pyi": b"old\n"})


@pytest.mark.parametrize("operation", ["catalog-read", "payload-read", "scan", "lstat"])
def test_filesystem_errors_retain_cause_and_context(tmp_path, monkeypatch, operation):
    repo = sample(tmp_path)
    target = {
        "catalog-read": repo / "tests/snapshot_cases.toml",
        "payload-read": repo / "tests/stubs/unused.pyi",
        "scan": repo / "tests/stubs/unreferenced",
        "lstat": repo / "tests/stubs",
    }[operation]
    if operation == "scan":
        target.mkdir()
    before = tree_state(repo)
    failure = OSError("injected failure", str(target))
    if operation == "scan":
        original = os.scandir

        def scan(path):
            if Path(path) == target:
                raise failure
            return original(path)

        monkeypatch.setattr(os, "scandir", scan)
    else:
        method = "lstat" if operation == "lstat" else "read_bytes"
        original = getattr(Path, method)

        def access(path, *args, **kwargs):
            if path == target:
                raise failure
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, method, access)
    with pytest.raises(HarnessError) as exc:
        load_catalog(repo)
    assert str(target) in str(exc.value)
    assert str(repo / "tests/snapshot_cases.toml") in str(exc.value)
    cause = exc.value
    while cause.__cause__ is not None:
        cause = cause.__cause__
    assert cause is failure
    if operation in {"payload-read", "scan"}:
        assert "unreferenced" in str(exc.value)
        assert "cases[" not in str(exc.value)  # Never invent ownership for inert files.
    monkeypatch.undo()
    assert tree_state(repo) == before


@pytest.mark.parametrize(
    "case, kind, clue",
    [("absent", "stubs", "unknown case"), ("a", "bad", "unknown kind")],
)
def test_unknown_selection_never_falls_back(tmp_path, case, kind, clue):
    repo = sample(tmp_path)
    before = tree_state(repo)
    with pytest.raises(HarnessError, match=clue):
        check_case(repo, case, kind, {})
    assert tree_state(repo) == before


@pytest.mark.parametrize(
    "actual, only, clue",
    [
        ({"../escape": b"x"}, None, "Unsafe"),
        ({"x\0y": b"x"}, None, "Invalid"),
        ({1: b"x"}, None, "Invalid"),
        ({"x": "text"}, None, "bytes"),
        ({"x": bytearray(b"x")}, None, "bytes"),
        ({"x": b"", "x/y": b""}, None, "Conflicting"),
        ({}, frozenset({"../x"}), "Unsafe"),
        ({"demo/a.pyi": b"old\n"}, frozenset(), "scope"),
    ],
)
def test_invalid_actual_and_scope(tmp_path, actual, only, clue):
    repo = sample(tmp_path)
    before = tree_state(repo)
    with pytest.raises(HarnessError, match=clue):
        check_case(repo, "a", "stubs", actual, only=only)
    assert tree_state(repo) == before


def test_scope_selects_exact_logical_names(tmp_path):
    repo = sample(tmp_path)
    catalog = load_catalog(repo)
    assert select_expected(catalog, "a", "stubs", {}, frozenset()) == {}
    assert select_expected(catalog, "a", "stubs", {}, frozenset({"demo/a.pyi"})) == {
        "demo/a.pyi": b"old\n"
    }
    assert select_expected(catalog, "a", "stubs", {}, frozenset({"new"})) == {}
    check_case(repo, "a", "stubs", {}, only=frozenset())
    with pytest.raises(SnapshotMismatch, match="Unexpected: new"):
        check_case(repo, "a", "stubs", {"new": b""}, only=frozenset({"new"}))


def test_byte_identity_and_sorted_changes(tmp_path):
    repo = write_catalog(
        tmp_path / "repo",
        {"a": {"stubs": {"é.pyi": "raw.pyi"}, "errors": {}}},
        {"stubs": {"raw.pyi": b"\xff\r\n"}},
    )
    before = tree_state(repo)
    check_case(repo, "a", "stubs", {"é.pyi": b"\xff\r\n"})
    with pytest.raises(SnapshotMismatch, match="Changed: é.pyi"):
        check_case(repo, "a", "stubs", {"é.pyi": b"\xff\n"})
    assert changed_names(
        {"z": b"", "a": b"x", "same": b"y"}, {"b": b"", "a": b"X", "same": b"y"}
    ) == ("a", "b", "z")
    assert changed_names({"x": b""}, {"x": b""}) == ()
    assert tree_state(repo) == before


def test_safe_path_planning_and_trusted_repository_alias(tmp_path):
    repo = sample(tmp_path)
    before = tree_state(repo)
    assert (
        safe_path(repo, "tests/stubs/new/deep.pyi") == repo / "tests/stubs/new/deep.pyi"
    )
    with pytest.raises(HarnessError, match="Non-directory"):
        safe_path(repo, "tests/stubs/unused.pyi/child")
    assert validate_name("single", component=True) == Path("single")
    with pytest.raises(HarnessError, match="case identifier"):
        validate_name("two/parts", component=True)
    alias = tmp_path / "trusted-alias"
    alias.symlink_to(repo, target_is_directory=True)
    assert load_catalog(alias).repo == repo.resolve()
    assert tree_state(repo) == before


BLOCKER = """
import importlib.abc
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in BLOCKED:
            raise ModuleNotFoundError('blocked: ' + fullname)
sys.meta_path.insert(0, Block())
"""


def run_blocked(code, blocked):
    support = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            f"BLOCKED = {blocked!r}\n"
            + BLOCKER
            + f"\nsys.path.insert(0, {str(support)!r})\n"
            + code,
        ],
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""
    return result.stdout


def test_read_only_never_imports_editor(tmp_path):
    repo = sample(tmp_path)
    before = tree_state(repo)
    assert run_blocked(
        f"""
from pathlib import Path
from snapshot_catalog import check_case
print(check_case(Path({str(repo)!r}), 'a', 'stubs', {{'demo/a.pyi': b'old\\n'}}))
assert not BLOCKED.intersection(sys.modules)
""",
        {"tomlkit", "snapshot_updates"},
    ).endswith("changed: ()\n")
    assert tree_state(repo) == before


def test_parser_dependency_is_actionable_and_version_selected():
    output = run_blocked(
        """
from pathlib import Path
from snapshot_catalog import parse_model
from snapshot_helpers import HarnessError
try:
    result = parse_model(b'format = 1\\n[cases]\\n', Path('example.toml'))
except HarnessError as error:
    assert sys.version_info < (3, 11)
    print(error)
else:
    assert sys.version_info >= (3, 11)
    assert result == {}
    print('stdlib parser')
""",
        {"tomli", "tomlkit"},
    )
    if sys.version_info < (3, 11):
        assert re.search(r"tomli>=2,<3", output)
    else:
        assert output == "stdlib parser\n"
