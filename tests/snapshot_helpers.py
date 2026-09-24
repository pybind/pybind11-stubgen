from __future__ import annotations

import difflib
import os
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
        kind = "Missing" if name not in actual else "Unexpected" if name not in expected else "Changed"
        differences.append(f"{kind}: {name}\n")
        before = expected.get(name, b"").decode("utf-8", errors="backslashreplace")
        after = actual.get(name, b"").decode("utf-8", errors="backslashreplace")
        differences.extend(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile=f"expected/{name}", tofile=f"actual/{name}",
        ))
    return "".join(differences)
