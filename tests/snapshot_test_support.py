"""Independent literal catalog fixtures and non-following filesystem inventories."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

from snapshot_helpers import Snapshot

if TYPE_CHECKING:
    from snapshot_catalog import Cases


def tree_state(root: Path) -> dict[str, tuple[str, bytes | str]]:
    result = {}

    def fail(error):
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        for name in dirs + files:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            key = path.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                result[key] = ("link", os.readlink(path))
            elif stat.S_ISREG(mode):
                result[key] = ("file", path.read_bytes())
            elif stat.S_ISDIR(mode):
                result[key] = ("dir", "")
            else:
                result[key] = ("special", str(stat.S_IFMT(mode)))
    return result


def write_catalog(repo: Path, cases: Cases, payloads: dict[str, Snapshot]) -> Path:
    lines = ["format = 1", ""]
    if not cases:
        lines.extend(["[cases]", ""])
    for kind in ("stubs", "errors"):
        root = repo / "tests" / kind
        root.mkdir(parents=True, exist_ok=True)
        for name, data in payloads.get(kind, {}).items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def quote(value):
        return json.dumps(value, ensure_ascii=False)

    for case, kinds in cases.items():
        for kind in ("stubs", "errors"):
            lines.append(f"[cases.{quote(case)}.{kind}]")
            for name, reference in kinds[kind].items():
                lines.append(f"{quote(name)} = {quote(reference)}")
            lines.append("")
    (repo / "tests/snapshot_cases.toml").write_bytes("\n".join(lines).encode())
    return repo
