"""Serial, case-scoped copy-on-write catalog editing and publication."""

from __future__ import annotations

import copy
import errno
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from snapshot_catalog import (
    Cases,
    Catalog,
    changed_names,
    load_catalog,
    parse_model,
    safe_path,
    select_expected,
    validate_files,
)
from snapshot_helpers import HarnessError, Snapshot


@dataclass(frozen=True)
class UpdateReport:
    catalog: Path
    case_id: str
    kind: str
    changed: tuple[str, ...]
    old_refs: dict[str, str]
    new_refs: dict[str, str]
    created: tuple[str, ...]
    reused: tuple[str, ...]
    removed: tuple[str, ...]

    def describe(self):
        root = self.catalog.parent / self.kind
        lines = [
            f"Case: {self.case_id}/{self.kind}",
            f"Catalog: {self.catalog}; changed: {self.changed}",
        ]
        for name in self.changed:
            old = (
                str(root / self.old_refs[name])
                if name in self.old_refs
                else "<unmapped>"
            )
            new = (
                str(root / self.new_refs[name])
                if name in self.new_refs
                else "<unmapped>"
            )
            lines.append(f"{name}: {old} -> {new}")
        for action in ("created", "reused", "removed"):
            lines.append(
                f"{action}: {tuple(str(root / p) for p in getattr(self, action))}"
            )
        return "\n".join(lines)


@dataclass
class UpdatePlan:
    case_id: str
    kind: str
    changed: tuple[str, ...]
    old_refs: dict[str, str]
    new_refs: dict[str, str]
    cases: Cases
    snapshot: Snapshot
    directory: str | None
    new_files: Snapshot
    reused: tuple[str, ...]
    removed: tuple[str, ...]


def plan_update(catalog, case_id, kind, actual, only) -> UpdatePlan:
    expected = select_expected(catalog, case_id, kind, actual, only)
    changed = changed_names(expected, actual)
    old_refs = catalog.mapping(case_id, kind)
    new_refs = dict(old_refs)
    intended = catalog.snapshot(case_id, kind)
    pending = {}
    reused = set()
    for name in changed:
        if name not in actual:
            new_refs.pop(name, None)
            intended.pop(name, None)
            continue
        intended[name] = actual[name]
        matches = sorted(
            {
                mapping[kind][name]
                for mapping in catalog.cases.values()
                if name in mapping[kind]
                and catalog.pools[kind][mapping[kind][name]] == actual[name]
            }
        )
        if matches:
            new_refs[name] = matches[0]
            reused.add(matches[0])
        else:
            pending[name] = actual[name]
    directory = None
    new_files = {}
    if pending:
        number = 1
        while True:
            directory = f"variants/{case_id}/{number}"
            candidate = safe_path(catalog.repo, f"tests/{kind}/{directory}")
            if not candidate.exists():
                break
            number += 1
        for name, content in sorted(pending.items()):
            physical = f"{directory}/{name}"
            new_refs[name] = physical
            new_files[physical] = content
    cases = copy.deepcopy(catalog.cases)
    cases[case_id][kind] = new_refs
    used = {ref for kinds in cases.values() for ref in kinds[kind].values()}
    displaced = {old_refs[name] for name in changed if name in old_refs}
    removed = tuple(sorted(displaced - used))
    return UpdatePlan(
        case_id,
        kind,
        changed,
        old_refs,
        new_refs,
        cases,
        intended,
        directory,
        new_files,
        tuple(sorted(reused)),
        removed,
    )


def render_update(catalog, plan) -> bytes:
    try:
        import tomlkit
    except ImportError as exc:
        raise HarnessError("Catalog editing requires tomlkit>=0.13,<1") from exc
    document = tomlkit.parse(catalog.raw.decode("utf-8"))
    table = document["cases"][plan.case_id][plan.kind]
    newline = "\r\n" if b"\r\n" in catalog.raw else "\n"
    for name in plan.changed:
        if name in plan.new_refs:
            is_new = name not in table
            table[name] = plan.new_refs[name]
            if is_new:
                # tomlkit defaults new items to LF, even in a CRLF document.
                table[name].trivia.trail = newline
        else:
            del table[name]
    raw = tomlkit.dumps(document).encode("utf-8")
    if parse_model(raw, catalog.path) != plan.cases:
        raise HarnessError("Serialized catalog differs from the planned mappings")
    return raw


def write_payloads(catalog, plan) -> None:
    if plan.directory is None:
        return
    directory = safe_path(catalog.repo, f"tests/{plan.kind}/{plan.directory}")
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir(exist_ok=False)
    for name, content in sorted(plan.new_files.items()):
        path = safe_path(catalog.repo, f"tests/{plan.kind}/{name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)


def write_temporary_catalog(catalog, raw) -> Path:
    temporary = None
    try:
        parent = safe_path(catalog.repo, "tests")
        if not parent.is_dir():
            raise HarnessError(f"Expected catalog parent directory: {parent}")
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=catalog.path.parent,
            prefix=".snapshot_cases-",
            suffix=".toml",
        ) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), stat.S_IMODE(catalog.path.stat().st_mode))
            stream.write(raw)
    except Exception as exc:
        raise HarnessError(
            f"Temporary catalog write failed; temporary={temporary}: {exc}"
        ) from exc
    return temporary


def publish_catalog(catalog, temporary) -> None:
    for path in (catalog.path, temporary):
        safe_path(catalog.repo, path.relative_to(catalog.repo).as_posix())
        if not path.is_file():
            raise HarnessError(f"Expected regular catalog file: {path}")
    if catalog.path.read_bytes() != catalog.raw:
        raise HarnessError(f"Catalog changed since loading: {catalog.path}")
    os.replace(temporary, catalog.path)


def cleanup_payloads(catalog, plan) -> None:
    root = catalog.repo / "tests" / plan.kind
    parents = set()
    for name in plan.removed:
        path = safe_path(catalog.repo, f"tests/{plan.kind}/{name}")
        path.unlink()
        for parent in path.parents:
            if parent == root:
                break
            parents.add(parent)
    for parent in sorted(parents, key=lambda path: (-len(path.parts), str(path))):
        safe_path(catalog.repo, parent.relative_to(catalog.repo).as_posix())
        try:
            parent.rmdir()
        except OSError as exc:
            if exc.errno not in (errno.ENOTEMPTY, errno.EEXIST):
                raise


def update_snapshot(repo, case_id, kind, actual, *, only=None):
    try:
        catalog = load_catalog(repo)
        plan = plan_update(catalog, case_id, kind, actual, only)
    except HarnessError as exc:
        raise HarnessError(
            f"Case {case_id}/{kind}; catalog not published: {exc}"
        ) from exc
    report = UpdateReport(
        catalog.path,
        case_id,
        kind,
        plan.changed,
        plan.old_refs,
        plan.new_refs,
        tuple(sorted(plan.new_files)),
        plan.reused,
        plan.removed,
    )
    if not plan.changed:
        return report
    published = False
    temporary = None
    try:
        raw = render_update(catalog, plan)
        write_payloads(catalog, plan)
        pools = validate_files(catalog.repo, plan.cases)
        prospective = Catalog(catalog.repo, catalog.path, raw, plan.cases, pools)
        if prospective.snapshot(case_id, kind) != plan.snapshot:
            raise HarnessError("Written payloads differ from the planned snapshot")
        for other_case in catalog.cases:
            for other_kind in ("stubs", "errors"):
                if (other_case, other_kind) != (case_id, kind):
                    if prospective.snapshot(other_case, other_kind) != catalog.snapshot(
                        other_case, other_kind
                    ):
                        raise HarnessError("An unselected expectation changed")
        temporary = write_temporary_catalog(catalog, raw)
        publish_catalog(catalog, temporary)
        published = True
        cleanup_payloads(catalog, plan)
    except Exception as exc:
        state = "published (mappings already changed)" if published else "not published"
        paths = tuple(
            str(catalog.repo / "tests" / kind / p) for p in sorted(plan.new_files)
        )
        # lexists is diagnostic-only: inspection errors must not hide the primary error.
        existing = tuple(path for path in paths if os.path.lexists(path))
        directory = (
            catalog.repo / "tests" / kind / plan.directory
            if plan.directory is not None
            else None
        )
        existing_directory = (
            directory if directory is not None and os.path.lexists(directory) else None
        )
        cleanup = tuple(str(catalog.repo / "tests" / kind / p) for p in plan.removed)
        raise HarnessError(
            catalog.context(case_id, kind)
            + f"Update failed; catalog {state}; temporary={temporary}; "
            + f"planned payloads={paths}; existing payloads={existing}; "
            + f"planned directory={plan.directory}; existing directory={existing_directory}; "
            + f"cleanup targets={plan.removed}; "
            + f"cleanup paths={cleanup}: {exc}"
        ) from exc
    return report
