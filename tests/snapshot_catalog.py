"""Strict, read-only literal snapshot catalogs (no editor or native dependencies)."""

from __future__ import annotations

import stat
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from snapshot_helpers import (
    HarnessError,
    Snapshot,
    SnapshotMismatch,
    diff_tree,
    read_tree,
    relative_file,
)

Cases = dict[str, dict[str, dict[str, str]]]
KINDS = ("stubs", "errors")


def validate_name(value: object, *, component: bool = False) -> Path:
    if not isinstance(value, str) or "\0" in value:
        raise HarnessError(f"Invalid snapshot path: {value!r}")
    path = relative_file(value)
    if component and len(path.parts) != 1:
        raise HarnessError(f"Invalid case identifier: {value!r}")
    return path


def safe_path(repo: Path, relative: str) -> Path:
    parts = validate_name(relative).parts
    path = repo
    for index, part in enumerate(parts):
        path = path / part
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise HarnessError(
                f"Unable to inspect snapshot path: {path}: {exc}"
            ) from exc
        if stat.S_ISLNK(mode):
            raise HarnessError(f"Unexpected symlink: {path}")
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            raise HarnessError(f"Non-directory snapshot parent: {path}")
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise HarnessError(f"Unexpected filesystem entry: {path}")
    return path


def _validate_logical_names(names: Iterable[str]) -> None:
    names = set(names)
    for name in names:
        path = validate_name(name)
        if any(parent.as_posix() in names for parent in path.parents):
            raise HarnessError(f"Conflicting snapshot paths: {name}")


def parse_model(raw: bytes, path: Path) -> Cases:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomli as tomllib
        except ImportError as exc:
            raise HarnessError(
                f"Catalog {path}: install test dependency "
                "tomli>=2,<3; python_version < '3.11'"
            ) from exc
    try:
        model = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise HarnessError(f"Invalid TOML catalog {path}: {exc}") from exc
    if set(model) != {"format", "cases"}:
        raise HarnessError(
            f"Catalog {path}: expected root keys format/cases; "
            f"missing {sorted({'format', 'cases'} - model.keys())}, "
            f"extra {sorted(model.keys() - {'format', 'cases'})}"
        )
    if type(model["format"]) is not int or model["format"] != 1:
        raise HarnessError(f"Catalog {path}: format must be integer 1")
    if not isinstance(model["cases"], dict):
        raise HarnessError(f"Catalog {path}: cases must be a table")
    cases: Cases = {}
    owners: dict[tuple[str, str], str] = {}
    for case_id, kinds in model["cases"].items():
        entry = f"Catalog {path}: cases[{case_id!r}]"
        try:
            validate_name(case_id, component=True)
            if not isinstance(kinds, dict):
                raise HarnessError("must be a table")
            if set(kinds) != set(KINDS):
                raise HarnessError(
                    f"expected stubs/errors tables; missing {sorted(set(KINDS) - kinds.keys())}, "
                    f"extra {sorted(kinds.keys() - set(KINDS))}"
                )
        except HarnessError as exc:
            raise HarnessError(f"{entry}: {exc}") from exc
        cases[case_id] = {}
        for kind in KINDS:
            table = kinds[kind]
            kind_entry = f"{entry}[{kind!r}]"
            if not isinstance(table, dict):
                raise HarnessError(f"{kind_entry}: must be a table")
            cases[case_id][kind] = {}
            for name, reference in table.items():
                try:
                    validate_name(name)
                    validate_name(reference)
                    owner = owners.setdefault((kind, reference), name)
                    if owner != name:
                        raise HarnessError(
                            f"Ambiguous payload ownership: {reference!r} is used for "
                            f"both {owner!r} and {name!r}"
                        )
                except HarnessError as exc:
                    raise HarnessError(f"{kind_entry}[{name!r}]: {exc}") from exc
                cases[case_id][kind][name] = reference
            try:
                _validate_logical_names(table)
            except HarnessError as exc:
                raise HarnessError(f"{kind_entry}: {exc}") from exc
    return cases


def validate_files(repo: Path, cases: Cases) -> dict[str, Snapshot]:
    pools = {}
    for kind in KINDS:
        root = repo / "tests" / kind
        try:
            safe_path(repo, f"tests/{kind}")
            if not root.is_dir():
                raise HarnessError(f"Expected payload directory: {root}")
            pools[kind] = read_tree(root)
        except (OSError, HarnessError) as exc:
            raise HarnessError(
                f"Payload pool {root} (including unreferenced entries): {exc}"
            ) from exc
    for case_id, kinds in cases.items():
        for kind, mapping in kinds.items():
            for name, reference in mapping.items():
                if reference not in pools[kind]:
                    raise HarnessError(
                        f"Missing mapped file cases[{case_id!r}][{kind!r}][{name!r}]: "
                        f"{repo / 'tests' / kind / reference}"
                    )
    return pools


@dataclass(frozen=True)
class Catalog:
    repo: Path
    path: Path
    raw: bytes
    cases: Cases
    pools: dict[str, Snapshot]

    def mapping(self, case_id: str, kind: str) -> dict[str, str]:
        if case_id not in self.cases:
            raise HarnessError(f"Catalog {self.path}: unknown case {case_id!r}")
        if kind not in KINDS:
            raise HarnessError(f"Catalog {self.path}: unknown kind {kind!r}")
        return dict(self.cases[case_id][kind])

    def snapshot(self, case_id: str, kind: str) -> Snapshot:
        return {
            name: self.pools[kind][ref]
            for name, ref in self.mapping(case_id, kind).items()
        }

    def context(
        self, case_id: str, kind: str, names: Iterable[str] | None = None
    ) -> str:
        mapping = self.mapping(case_id, kind)
        lines = [f"Catalog: {self.path}", f"Case: {case_id}/{kind}"]
        for name in sorted(mapping if names is None else names):
            target = (
                self.repo / "tests" / kind / mapping[name]
                if name in mapping
                else "<unmapped>"
            )
            lines.append(f"Entry cases[{case_id!r}][{kind!r}][{name!r}]: {target}")
        return "\n".join(lines) + "\n"


def load_catalog(repo: Path) -> Catalog:
    path = repo / "tests/snapshot_cases.toml"
    try:
        repo = repo.resolve(strict=True)
        path = repo / "tests/snapshot_cases.toml"
        safe_path(repo, "tests/snapshot_cases.toml")
        if not path.is_file():
            raise HarnessError(f"Expected catalog file: {path}")
        raw = path.read_bytes()
        cases = parse_model(raw, path)
        pools = validate_files(repo, cases)
    except (OSError, RuntimeError, HarnessError) as exc:
        raise HarnessError(f"Catalog {path}: {exc}") from exc
    return Catalog(repo, path, raw, cases, pools)


def select_expected(
    catalog: Catalog,
    case_id: str,
    kind: str,
    actual: Snapshot,
    only: frozenset[str] | None,
) -> Snapshot:
    _validate_logical_names(actual)
    for name, content in actual.items():
        if not isinstance(content, bytes):
            raise HarnessError(f"Snapshot content must be bytes: {name}")
    if only is not None:
        for name in only:
            validate_name(name)
        if actual.keys() - only:
            raise HarnessError("Actual output exceeds the selected snapshot scope")
    expected = catalog.snapshot(case_id, kind)
    if only is not None:
        expected = {name: content for name, content in expected.items() if name in only}
    return expected


def changed_names(expected: Snapshot, actual: Snapshot) -> tuple[str, ...]:
    return tuple(
        name
        for name in sorted(expected.keys() | actual.keys())
        if name not in expected or name not in actual or expected[name] != actual[name]
    )


def check_case(
    repo: Path,
    case_id: str,
    kind: str,
    actual: Snapshot,
    *,
    only: frozenset[str] | None = None,
) -> str:
    try:
        catalog = load_catalog(repo)
        expected = select_expected(catalog, case_id, kind, actual, only)
    except HarnessError as exc:
        raise HarnessError(f"Case {case_id}/{kind}: {exc}") from exc
    context = catalog.context(case_id, kind, expected.keys() | actual.keys())
    difference = diff_tree(expected, actual)
    if difference:
        raise SnapshotMismatch(context + difference)
    return context + "changed: ()"
