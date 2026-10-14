"""Case-scoped edits against independently authored, disposable catalogs."""

from __future__ import annotations

import copy
import errno
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import snapshot_updates as editor
from snapshot_catalog import check_case, load_catalog
from snapshot_helpers import HarnessError
from snapshot_test_support import tree_state, write_catalog
from snapshot_updates import plan_update, update_snapshot


def shared_repo(tmp_path):
    cases = {
        key: {
            "stubs": {"demo/a.pyi": "shared/a.pyi"},
            "errors": {"demo.errors.stderr.txt": "shared/error.txt"},
        }
        for key in ("a", "b")
    }
    return write_catalog(
        tmp_path / "repo",
        cases,
        {
            "stubs": {"shared/a.pyi": b"old\n", "unrelated.pyi": b"leave\n"},
            "errors": {"shared/error.txt": b"fatal\n"},
        },
    )


def assert_live_unchanged(original):
    assert original.path.read_bytes() == original.raw
    after = load_catalog(original.repo)
    for case in original.cases:
        for kind in ("stubs", "errors"):
            assert after.snapshot(case, kind) == original.snapshot(case, kind)
    for kind, pool in original.pools.items():
        for name, data in pool.items():
            assert (original.repo / "tests" / kind / name).read_bytes() == data


def test_copy_on_write_then_reuse_does_not_change_other_case(tmp_path):
    repo = shared_repo(tmp_path)
    first = update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new\n"})
    after = load_catalog(repo)
    assert after.snapshot("a", "stubs") == {"demo/a.pyi": b"new\n"}
    assert after.snapshot("b", "stubs") == {"demo/a.pyi": b"old\n"}
    assert after.snapshot("a", "errors") == {"demo.errors.stderr.txt": b"fatal\n"}
    assert first.created == ("variants/a/1/demo/a.pyi",)
    second = update_snapshot(repo, "b", "stubs", {"demo/a.pyi": b"new\n"})
    final = load_catalog(repo)
    assert final.mapping("a", "stubs") == final.mapping("b", "stubs")
    assert second.created == ()
    assert second.reused == first.created
    assert second.removed == ("shared/a.pyi",)
    assert not (repo / "tests/stubs/shared").exists()
    assert (repo / "tests/stubs/unrelated.pyi").read_bytes() == b"leave\n"
    assert (repo / "tests/errors/shared/error.txt").read_bytes() == b"fatal\n"
    text = first.describe()
    assert "Case: a/stubs" in text
    assert str(repo / "tests/snapshot_cases.toml") in text
    assert (
        f"demo/a.pyi: {repo}/tests/stubs/shared/a.pyi -> {repo}/tests/stubs/variants/a/1/demo/a.pyi"
        in text
    )
    assert "created:" in text and "reused: ()" in text and "removed: ()" in text


def test_noop_is_byte_identical(tmp_path):
    repo = shared_repo(tmp_path)
    # Even a blocked allocation namespace is irrelevant to a no-op.
    (repo / "tests/stubs/variants").write_bytes(b"occupied")
    before = tree_state(repo)
    report = update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"old\n"})
    assert report.changed == report.created == report.reused == report.removed == ()
    assert tree_state(repo) == before


def test_planning_preserves_model_and_files(tmp_path):
    repo = shared_repo(tmp_path)
    catalog = load_catalog(repo)
    model, files = copy.deepcopy(catalog.cases), tree_state(repo)
    plan = plan_update(catalog, "a", "stubs", {"demo/a.pyi": b"new\n"}, None)
    assert plan.cases != model
    assert catalog.cases == model
    assert tree_state(repo) == files
    assert plan.snapshot == {"demo/a.pyi": b"new\n"}
    plan.cases["b"]["errors"].clear()
    assert catalog.cases == model


def test_full_add_delete_uses_one_directory_and_never_overwrites_single_owner(tmp_path):
    repo = write_catalog(
        tmp_path / "repo",
        {"a": {"stubs": {"gone": "old/gone", "keep": "old/keep"}, "errors": {}}},
        {"stubs": {"old/gone": b"gone", "old/keep": b"keep", "old/inert": b"inert"}},
    )
    # An open descriptor still sees the old inode after orphan unlinking.
    with (repo / "tests/stubs/old/keep").open("rb") as old_file:
        report = update_snapshot(
            repo, "a", "stubs", {"keep": b"changed", "new/deep": b"new"}
        )
        assert old_file.read() == b"keep"
    assert report.changed == ("gone", "keep", "new/deep")
    assert report.old_refs == {"gone": "old/gone", "keep": "old/keep"}
    assert report.new_refs == {
        "keep": "variants/a/1/keep",
        "new/deep": "variants/a/1/new/deep",
    }
    assert report.created == ("variants/a/1/keep", "variants/a/1/new/deep")
    assert report.removed == ("old/gone", "old/keep")
    assert (repo / "tests/stubs/old/inert").read_bytes() == b"inert"
    assert load_catalog(repo).snapshot("a", "stubs") == {
        "keep": b"changed",
        "new/deep": b"new",
    }
    assert "gone:" in report.describe() and "-> <unmapped>" in report.describe()
    assert "new/deep: <unmapped> ->" in report.describe()


def test_only_updates_selected_error_names(tmp_path):
    repo = write_catalog(
        tmp_path / "repo",
        {"a": {"stubs": {}, "errors": {"one": "one", "two": "two", "gone": "gone"}}},
        {"errors": {"one": b"1", "two": b"2", "gone": b"g"}},
    )
    report = update_snapshot(
        repo,
        "a",
        "errors",
        {"one": b"new", "added": b"a"},
        only=frozenset({"one", "gone", "added"}),
    )
    assert report.changed == ("added", "gone", "one")
    assert load_catalog(repo).snapshot("a", "errors") == {
        "one": b"new",
        "two": b"2",
        "added": b"a",
    }
    assert report.new_refs["two"] == "two"
    assert load_catalog(repo).snapshot("a", "stubs") == {}


@pytest.mark.parametrize(
    "actual,only",
    [
        ({"outside": b"new"}, frozenset({"demo/a.pyi"})),
        ({"demo": b"ancestor"}, frozenset({"demo"})),
        ({"demo/a.pyi/child": b"descendant"}, frozenset({"demo/a.pyi/child"})),
        ({"../escape": b"bad"}, None),
        ({"demo/a.pyi": "not bytes"}, None),
    ],
)
def test_invalid_update_fails_before_mutation(tmp_path, actual, only):
    repo = shared_repo(tmp_path)
    before = tree_state(repo)
    with pytest.raises(HarnessError, match="not published"):
        update_snapshot(repo, "a", "stubs", actual, only=only)
    assert tree_state(repo) == before


@pytest.mark.parametrize("case,kind", [("unknown", "stubs"), ("a", "unknown")])
def test_unknown_selection_is_not_created(tmp_path, case, kind):
    repo = shared_repo(tmp_path)
    before = tree_state(repo)
    with pytest.raises(HarnessError, match="not published"):
        update_snapshot(repo, case, kind, {})
    assert tree_state(repo) == before


@pytest.mark.parametrize(
    "before,after", [("node", "node/child"), ("node/child", "node")]
)
def test_full_file_directory_shape_changes(tmp_path, before, after):
    repo = write_catalog(
        tmp_path / "repo",
        {"a": {"stubs": {before: "old/payload"}, "errors": {}}},
        {"stubs": {"old/payload": b"old"}},
    )
    update_snapshot(repo, "a", "stubs", {after: b"new"})
    assert load_catalog(repo).snapshot("a", "stubs") == {after: b"new"}
    assert not (repo / "tests/stubs/old").exists()
    assert (repo / "tests/stubs").is_dir()


def test_reuse_is_lexicographic_and_only_referenced_same_kind_and_name(tmp_path):
    repo = write_catalog(
        tmp_path / "repo",
        {
            "a": {"stubs": {"name": "old"}, "errors": {"name": "000-error"}},
            "b": {"stubs": {"name": "z-match", "other": "001-other"}, "errors": {}},
            "c": {"stubs": {"name": "a-match"}, "errors": {}},
        },
        {
            "stubs": {
                "old": b"old",
                "z-match": b"new",
                "a-match": b"new",
                "001-other": b"new",
                "000-inert": b"new",
            },
            "errors": {"000-error": b"new"},
        },
    )
    report = update_snapshot(repo, "a", "stubs", {"name": b"new"})
    assert report.new_refs == {"name": "a-match"}
    assert report.reused == ("a-match",)
    assert report.created == ()
    assert not (repo / "tests/stubs/variants").exists()
    assert (repo / "tests/stubs/000-inert").read_bytes() == b"new"


def test_unreferenced_identical_payload_is_not_reused(tmp_path):
    repo = shared_repo(tmp_path)
    (repo / "tests/stubs/000-inert").write_bytes(b"new\n")
    report = update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new\n"})
    assert report.created == ("variants/a/1/demo/a.pyi",)
    assert report.reused == ()
    assert (repo / "tests/stubs/000-inert").read_bytes() == b"new\n"


def test_allocation_skips_numbered_files_and_empty_directories(tmp_path):
    repo = shared_repo(tmp_path)
    parent = repo / "tests/stubs/variants/a"
    (parent / "1").mkdir(parents=True)
    (parent / "2").write_bytes(b"occupied")
    report = update_snapshot(
        repo, "a", "stubs", {"demo/a.pyi": b"new", "demo/b.pyi": b"other"}
    )
    assert report.created == ("variants/a/3/demo/a.pyi", "variants/a/3/demo/b.pyi")
    assert (parent / "1").is_dir()
    assert (parent / "2").read_bytes() == b"occupied"


@pytest.mark.parametrize(
    "relative,entry",
    [
        ("variants", "file"),
        ("variants/a", "file"),
        ("variants/a/1", "symlink"),
        ("variants/a", "symlink"),
        ("variants/a/1", "fifo"),
    ],
)
def test_bad_namespace_entries_fail_without_writes(tmp_path, relative, entry):
    repo = shared_repo(tmp_path)
    target = repo / "tests/stubs" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if entry == "file":
        target.write_bytes(b"occupied")
    elif entry == "symlink":
        target.symlink_to(tmp_path / "absent")
    else:
        os.mkfifo(target)
    before = tree_state(repo)
    with pytest.raises(HarnessError, match="not published"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert tree_state(repo) == before


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_value_replacement_preserves_exact_comments_and_newlines(tmp_path, newline):
    repo = shared_repo(tmp_path)
    text = "\n".join(
        [
            "# top comment",
            "format = 1  # format",
            "",
            "[cases.a.stubs] # selected table",
            '"demo/a.pyi"  =  "shared/a.pyi" # attached',
            "# unrelated standalone",
            "",
            "[cases.a.errors]",
            '"demo.errors.stderr.txt" = "shared/error.txt" # error',
            "",
            "[cases.b.stubs] # other case",
            '"demo/a.pyi" = "shared/a.pyi"',
            "[cases.b.errors]",
            '"demo.errors.stderr.txt" = "shared/error.txt"',
            "",
        ]
    ).replace("\n", newline)
    path = repo / "tests/snapshot_cases.toml"
    path.write_bytes(text.encode())
    update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    expected = text.replace(
        '"shared/a.pyi" # attached', '"variants/a/1/demo/a.pyi" # attached', 1
    )
    assert path.read_bytes() == expected.encode()


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_delete_and_append_preserve_unrelated_comments_and_table_order(
    tmp_path, newline
):
    repo = write_catalog(
        tmp_path / "repo",
        {"a": {"stubs": {"gone": "gone", "keep": "keep"}, "errors": {}}},
        {"stubs": {"gone": b"g", "keep": b"k"}},
    )
    text = '# top\nformat = 1\n[cases.a.stubs] # table\n"gone" = "gone" # delete me\n# keep standalone\n"keep" = "keep" # inline\n[cases.a.errors] # last\n'.replace(
        "\n", newline
    )
    path = repo / "tests/snapshot_cases.toml"
    path.write_bytes(text.encode())
    update_snapshot(repo, "a", "stubs", {"keep": b"k", "added": b"a"})
    expected = text.replace('"gone" = "gone" # delete me' + newline, "").replace(
        "[cases.a.errors]",
        'added = "variants/a/1/added"' + newline + "[cases.a.errors]",
    )
    assert path.read_bytes() == expected.encode()


def test_noop_and_readonly_work_without_editor_dependency(tmp_path):
    repo = shared_repo(tmp_path)
    before = tree_state(repo)
    script = """
import importlib.abc
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *args):
        if fullname == "tomlkit":
            raise ImportError("blocked tomlkit")
sys.meta_path.insert(0, Block())
from snapshot_catalog import check_case
from snapshot_helpers import HarnessError
repo = Path(sys.argv[2])
assert "snapshot_updates" not in sys.modules
check_case(repo, "a", "stubs", {"demo/a.pyi": b"old\\n"})
assert "snapshot_updates" not in sys.modules
check_case(repo, "a", "stubs", {"demo/a.pyi": b"old\\n"}, update=True)
assert "tomlkit" not in sys.modules
try:
    check_case(repo, "a", "stubs", {"demo/a.pyi": b"new\\n"}, update=True)
except HarnessError as exc:
    assert "tomlkit>=0.13,<1" in str(exc), str(exc)
    assert "not published" in str(exc), str(exc)
else:
    raise AssertionError("missing dependency accepted")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            script,
            str(Path(__file__).resolve().parents[1]),
            str(repo),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert tree_state(repo) == before


def test_check_case_delegates_scope_and_reports_update(tmp_path):
    repo = shared_repo(tmp_path)
    text = check_case(
        repo, "a", "stubs", {"added": b"new"}, update=True, only=frozenset({"added"})
    )
    assert "changed: ('added',)" in text
    assert str(repo / "tests/stubs/variants/a/1/added") in text
    assert load_catalog(repo).snapshot("a", "stubs") == {
        "demo/a.pyi": b"old\n",
        "added": b"new",
    }


@pytest.mark.parametrize(
    "corruption", ["path", "ownership", "serializer", "parser", "model"]
)
def test_render_validation_fails_before_allocation(tmp_path, monkeypatch, corruption):
    import tomlkit

    repo = shared_repo(tmp_path)
    before = tree_state(repo)
    real_plan = editor.plan_update
    if corruption in {"path", "ownership", "model"}:

        def bad_plan(*args):
            plan = real_plan(*args)
            if corruption == "path":
                plan.new_refs["demo/a.pyi"] = "../escape"
            elif corruption == "ownership":
                plan.new_refs["different"] = "shared/a.pyi"
                plan.changed += ("different",)
            else:
                plan.cases["b"]["errors"] = {}
            return plan

        monkeypatch.setattr(editor, "plan_update", bad_plan)
    else:

        def fail(*args):
            raise ValueError(f"injected {corruption}")

        monkeypatch.setattr(
            tomlkit, "dumps" if corruption == "serializer" else "parse", fail
        )
    with pytest.raises(HarnessError, match="not published"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert tree_state(repo) == before


@pytest.mark.parametrize(
    "stage",
    ["render_update", "write_payloads", "write_temporary_catalog", "publish_catalog"],
)
def test_prepublication_failure_preserves_live_references(tmp_path, monkeypatch, stage):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)

    def fail(*args, **kwargs):
        raise OSError(f"injected {stage}")

    monkeypatch.setattr(editor, stage, fail)
    with pytest.raises(HarnessError, match="not published") as caught:
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"changed\n"})
    assert f"injected {stage}" in str(caught.value)
    assert isinstance(caught.value.__cause__, OSError)
    assert_live_unchanged(original)
    for path in (repo / "tests/stubs/variants").rglob("*"):
        if path.is_file():
            assert str(path) in str(caught.value)
    for path in (repo / "tests").glob(".snapshot_cases-*.toml"):
        assert str(path) in str(caught.value)


def test_partial_exclusive_payload_write_reports_existing_not_uncreated_files(
    tmp_path, monkeypatch
):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    real_open = Path.open

    class PartialWrite:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, data):
            self.stream.write(data[:2])
            self.stream.flush()
            raise OSError("injected partial xb write")

    def open_file(path, mode="r", *args, **kwargs):
        stream = real_open(path, mode, *args, **kwargs)
        return PartialWrite(stream) if mode == "xb" else stream

    monkeypatch.setattr(Path, "open", open_file)
    with pytest.raises(HarnessError, match="not published") as caught:
        update_snapshot(
            repo, "a", "stubs", {"demo/a.pyi": b"changed", "demo/z.pyi": b"later"}
        )
    partial = repo / "tests/stubs/variants/a/1/demo/a.pyi"
    absent = repo / "tests/stubs/variants/a/1/demo/z.pyi"
    assert partial.read_bytes() == b"ch"
    assert not absent.exists()
    message = str(caught.value)
    assert "injected partial xb write" in message
    assert str(partial) in message and "planned directory=variants/a/1" in message
    assert f"existing payloads={(str(partial),)}" in message
    assert f"existing directory={repo}/tests/stubs/variants/a/1" in message
    assert_live_unchanged(original)


def test_exclusive_directory_creation_rejects_late_occupant(tmp_path, monkeypatch):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    real_write = editor.write_payloads

    def occupy(catalog, plan):
        directory = repo / "tests/stubs" / plan.directory
        directory.mkdir(parents=True)
        (directory / "sentinel").write_bytes(b"external")
        real_write(catalog, plan)

    monkeypatch.setattr(editor, "write_payloads", occupy)
    with pytest.raises(HarnessError, match="not published"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert (repo / "tests/stubs/variants/a/1/sentinel").read_bytes() == b"external"
    assert_live_unchanged(original)


def test_temporary_partial_write_reports_its_path_and_cause(tmp_path, monkeypatch):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    real_temporary = editor.tempfile.NamedTemporaryFile

    class PartialTemporary:
        def __init__(self, stream):
            self.stream = stream
            self.name = stream.name

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def write(self, data):
            self.stream.write(data[:7])
            self.stream.flush()
            raise OSError("injected temporary write")

        def fileno(self):
            return self.stream.fileno()

    def temporary(*args, **kwargs):
        return PartialTemporary(real_temporary(*args, **kwargs))

    monkeypatch.setattr(editor.tempfile, "NamedTemporaryFile", temporary)
    with pytest.raises(HarnessError, match="not published") as caught:
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    leftovers = list((repo / "tests").glob(".snapshot_cases-*.toml"))
    assert len(leftovers) == 1
    assert len(leftovers[0].read_bytes()) == 7
    assert str(leftovers[0]) in str(caught.value)
    assert "injected temporary write" in str(caught.value)
    assert isinstance(caught.value.__cause__.__cause__, OSError)
    assert_live_unchanged(original)


def test_replace_failure_retains_old_catalog_and_names_temporary(tmp_path, monkeypatch):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)

    def fail(*args):
        raise OSError("injected replace")

    monkeypatch.setattr(editor.os, "replace", fail)
    with pytest.raises(HarnessError, match="not published") as caught:
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    (temporary,) = (repo / "tests").glob(".snapshot_cases-*.toml")
    assert str(temporary) in str(caught.value)
    assert "injected replace" in str(caught.value)
    assert isinstance(caught.value.__cause__, OSError)
    assert_live_unchanged(original)


def test_publication_preserves_mode(tmp_path):
    repo = shared_repo(tmp_path)
    path = repo / "tests/snapshot_cases.toml"
    path.chmod(0o640)
    update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert not list(path.parent.glob(".snapshot_cases-*.toml"))


def test_stale_catalog_edit_survives_publication_attempt(tmp_path, monkeypatch):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    external = original.raw + b"\n# external edit\n"
    real_publish = editor.publish_catalog

    def edit_then_publish(catalog, temporary):
        catalog.path.write_bytes(external)
        real_publish(catalog, temporary)

    monkeypatch.setattr(editor, "publish_catalog", edit_then_publish)
    with pytest.raises(HarnessError, match="not published") as caught:
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert "changed" in str(caught.value).lower()
    assert original.path.read_bytes() == external
    assert load_catalog(repo).snapshot("a", "stubs") == {"demo/a.pyi": b"old\n"}


@pytest.mark.parametrize(
    "target,entry",
    [
        ("catalog", "symlink"),
        ("temporary", "symlink"),
        ("catalog", "directory"),
        ("temporary", "directory"),
    ],
)
def test_publish_rejects_nonregular_substitutions(tmp_path, monkeypatch, target, entry):
    repo = shared_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.write_bytes(b"untouched")
    real_publish = editor.publish_catalog

    def substitute(catalog, temporary):
        path = catalog.path if target == "catalog" else temporary
        path.unlink()
        if entry == "symlink":
            path.symlink_to(outside)
        else:
            path.mkdir()
        real_publish(catalog, temporary)

    monkeypatch.setattr(editor, "publish_catalog", substitute)
    with pytest.raises(HarnessError, match="not published"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert outside.read_bytes() == b"untouched"
    assert (repo / "tests/stubs/shared/a.pyi").read_bytes() == b"old\n"


def test_corrupted_new_payload_is_not_published(tmp_path, monkeypatch):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    real_write = editor.write_payloads

    def corrupt(catalog, plan):
        real_write(catalog, plan)
        (repo / "tests/stubs/variants/a/1/demo/a.pyi").write_bytes(b"corrupted")

    monkeypatch.setattr(editor, "write_payloads", corrupt)
    with pytest.raises(HarnessError, match="not published.*Written payloads differ"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert_live_unchanged(original)


@pytest.mark.parametrize("operation", ["unlink", "rmdir", "wrapper"])
def test_cleanup_failure_is_postpublication_and_names_leftovers(
    tmp_path, monkeypatch, operation
):
    repo = write_catalog(
        tmp_path / "repo",
        {
            "a": {"stubs": {"name": "old/deep/payload"}, "errors": {}},
            "b": {"stubs": {"name": "other/payload"}, "errors": {}},
        },
        {
            "stubs": {
                "old/deep/payload": b"old",
                "other/payload": b"other",
                "inert/leave": b"leave",
            }
        },
    )

    def fail(*args, **kwargs):
        raise OSError(errno.EACCES, f"injected cleanup {operation}")

    if operation == "wrapper":
        monkeypatch.setattr(editor, "cleanup_payloads", fail)
    else:
        monkeypatch.setattr(Path, operation, fail)
    with pytest.raises(HarnessError, match="catalog published") as caught:
        update_snapshot(repo, "a", "stubs", {"name": b"new"})
    message = str(caught.value)
    assert "mappings already changed" in message
    assert f"injected cleanup {operation}" in message
    assert isinstance(caught.value.__cause__, OSError)
    assert "cleanup targets=('old/deep/payload',)" in message
    assert str(repo / "tests/stubs/old/deep/payload") in message
    assert load_catalog(repo).snapshot("a", "stubs") == {"name": b"new"}
    assert load_catalog(repo).snapshot("b", "stubs") == {"name": b"other"}
    assert (repo / "tests/stubs/inert/leave").read_bytes() == b"leave"
    if operation == "rmdir":
        assert not (repo / "tests/stubs/old/deep/payload").exists()
        assert (repo / "tests/stubs/old/deep").is_dir()
    else:
        assert (repo / "tests/stubs/old/deep/payload").read_bytes() == b"old"


@pytest.mark.parametrize("code", [errno.ENOTEMPTY, errno.EEXIST])
def test_cleanup_suppresses_only_nonempty_directory_errors(tmp_path, monkeypatch, code):
    repo = write_catalog(
        tmp_path / "repo",
        {"a": {"stubs": {"name": "old/deep/payload"}, "errors": {}}},
        {"stubs": {"old/deep/payload": b"old"}},
    )

    def nonempty(*args):
        raise OSError(code, "nonempty")

    monkeypatch.setattr(Path, "rmdir", nonempty)
    report = update_snapshot(repo, "a", "stubs", {"name": b"new"})
    assert report.removed == ("old/deep/payload",)
    assert not (repo / "tests/stubs/old/deep/payload").exists()
    assert load_catalog(repo).snapshot("a", "stubs") == {"name": b"new"}


def test_payload_writer_rechecks_late_namespace_symlink(tmp_path, monkeypatch):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    outside = tmp_path / "outside"
    outside.mkdir()
    real_write = editor.write_payloads

    def substitute(catalog, plan):
        (repo / "tests/stubs/variants").symlink_to(outside, target_is_directory=True)
        real_write(catalog, plan)

    monkeypatch.setattr(editor, "write_payloads", substitute)
    with pytest.raises(HarnessError, match="not published.*symlink"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert tree_state(outside) == {}
    assert original.path.read_bytes() == original.raw
    assert (repo / "tests/stubs/shared/a.pyi").read_bytes() == b"old\n"


def test_payload_file_creation_is_exclusive(tmp_path, monkeypatch):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    real_open = Path.open
    target = repo / "tests/stubs/variants/a/1/demo/a.pyi"

    def occupy(path, mode="r", *args, **kwargs):
        if path == target:
            # Simulate an occupant appearing immediately before the real open.
            if mode in {"xb", "wb"}:
                with real_open(path, "wb") as stream:
                    stream.write(b"external")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", occupy)
    with pytest.raises(HarnessError, match="not published"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert target.read_bytes() == b"external"
    assert_live_unchanged(original)


def test_temporary_writer_rechecks_parent_before_creation(tmp_path, monkeypatch):
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    saved = repo / "saved-tests"
    real_write = editor.write_temporary_catalog

    def substitute(catalog, raw):
        (repo / "tests").rename(saved)
        (repo / "tests").symlink_to(saved, target_is_directory=True)
        return real_write(catalog, raw)

    monkeypatch.setattr(editor, "write_temporary_catalog", substitute)
    with pytest.raises(HarnessError, match="not published.*symlink"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"new"})
    assert not list(saved.glob(".snapshot_cases-*.toml"))
    assert (saved / "snapshot_cases.toml").read_bytes() == original.raw
    assert (saved / "stubs/shared/a.pyi").read_bytes() == b"old\n"


def test_cleanup_rechecks_orphan_before_unlink(tmp_path, monkeypatch):
    repo = write_catalog(
        tmp_path / "repo",
        {"a": {"stubs": {"name": "old"}, "errors": {}}},
        {"stubs": {"old": b"old"}},
    )
    outside = tmp_path / "outside"
    outside.write_bytes(b"untouched")
    real_cleanup = editor.cleanup_payloads

    def substitute(catalog, plan):
        old = repo / "tests/stubs/old"
        old.unlink()
        old.symlink_to(outside)
        real_cleanup(catalog, plan)

    monkeypatch.setattr(editor, "cleanup_payloads", substitute)
    with pytest.raises(HarnessError, match="catalog published.*symlink"):
        update_snapshot(repo, "a", "stubs", {"name": b"new"})
    assert (repo / "tests/stubs/old").is_symlink()
    assert outside.read_bytes() == b"untouched"
    assert b"variants/a/1/name" in (repo / "tests/snapshot_cases.toml").read_bytes()
