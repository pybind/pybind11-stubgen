import os
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
