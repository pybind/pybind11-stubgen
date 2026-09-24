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
