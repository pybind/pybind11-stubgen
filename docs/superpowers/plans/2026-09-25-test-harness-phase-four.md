# Test Harness Phase Four Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deduplicate active native expectations using an explicit TOML catalog and safe case-scoped copy-on-write updates, without changing effective expectations.

**Architecture:** Retain the two payload roots and existing generation/normalization pipeline. A small reader validates literal case mappings and compares logical snapshots; a separate editor publishes new payloads before atomically replacing the catalog. Migrate recorded baseline bytes, not generated output.

**Tech Stack:** Python 3.10–3.13, pytest 8, stdlib tomllib / conditional tomli, tomlkit, existing uv/tox/scikit-build-core native runner.

**Spec:** [Approved phase-four design](../specs/2026-09-25-test-harness-phase-four-design.md). Read it completely before this plan.

## Global Constraints

- Continue in `/home/virtuald/src/ext/pybind11-stubgen/.worktrees/test-harness-phase-one`, branch `test-harness-phase-one`; do not touch other worktrees.
- Preservation anchor: `4c84bad5dfb95b63980be8c629c3c6a2746829cb`, already rebased onto `prune-historical-snapshots` (`b651555`). Never restore the 155 pruned entries.
- All production files under `pybind11_stubgen/`, the C++ fixture and its build configuration, and all existing demo Python source/module identities remain unchanged.
- Preserve exact effective filenames/bytes/order for all 13 cases and both native checks per case. Deduplication is not regeneration or expectation correction.
- Preserve native pins, generator backend/package discovery/metadata, Ruff configuration/pin and normalization, installed-origin/runtime guards, and existing 300-second snapshot / 600-second build-install timeouts.
- Compiler-free tests require pytest and the approved TOML dependencies, not demo, NumPy/SciPy, native setup or formatter downloads. No new test/support `__init__.py` files.
- Add `tomli>=2,<3; python_version < '3.11'` and `tomlkit>=0.13,<1` only as development/test dependencies. Review scoped lock changes; no upgrade operation or unrelated upgrades.
- Keep workflow triggers, matrix membership, gemmi jobs, artifact retention policy, publication conditions and permissions unchanged.
- Catalog reads and no-op updates do not import tomlkit; ordinary checks never write references or the index. No fallback/overlay/version-range selection or new execution matrix.
- Updates are explicit and serial, including across tox processes. No all-files/all-run transaction, concurrent-writer support or power-loss durability claim.
- No push, PR, merge, release tag, remote workflow run or publication. Preserve this branch/worktree and all prior evidence.
- Keep ordinary-Python positional-only behavior, dirty-tree generator packaging, and the deferred permanent actual-tox inventory gate separate. Investigate failures rather than adjusting pins, sorting stderr, weakening tests, skipping or bulk-updating references.

---

## Workspace, baseline and evidence

All shell blocks run from the existing worktree root. Tool calls do not share shell variables; set `E` in every block that uses it:

```sh
E="$PWD/.superpowers/sdd/2026-09-25-test-harness-phase-four"
git check-ignore -q "$E"
git status --short
git merge-base --is-ancestor prune-historical-snapshots HEAD
df -h .
```

The rebase baseline is already recorded in `rebase-baseline/summary.json`: four source suites ×192 and the supplied-wheel native route, 11 profiles /1,093 tests /26 comparisons. `rebase-after.json` records every old effective case's filename/hash inventory; `rebase-commit-map.json` maps historical hashes. Reuse these as historical evidence, not as proof of changed implementation. Before Task 1, verify no non-documentation changes since the anchor and repeat source endpoint suites.

Use unique log names and `UV_LINK_MODE=copy`; unset `VIRTUAL_ENV`, `PYTHONPATH`, `PYTEST_ADDOPTS` and inherited `STUBGEN_*` in verification drivers. Source checks intentionally permit checkout imports; installed checks use `-I` and `STUBGEN_TEST_INSTALLED=1`. Preserve `.tox/<profile>/{tmp,log}` into this phase's evidence directory before tox can clear them. Do not copy whole environments or delete retained data to regain space.

Create an immutable oracle by extracting `git archive 4c84bad` into `$E/oracle-source` before migration. Use the old `snapshot_helpers.py` from that archive, not the new reader, to capture the following literal 13-case inventory into `$E/oracle.json`. Encode bytes as hexadecimal, retain all logical paths, and assert equality with `rebase-after.json` hashes. The literal list is an audit oracle, not execution configuration:

```python
A = "numpy-array-wrap-with-annotated"
T = "numpy-array-use-type-var"
CASES = [
    ((3, 10), "v3.0", A), ((3, 11), "v3.0", A),
    ((3, 12), "v3.0", A), ((3, 13), "v3.0", A),
    ((3, 13), "v3.0", T),
    ((3, 10), "v2.13", A), ((3, 11), "v2.13", A),
    ((3, 12), "v2.13", A), ((3, 13), "v2.13", A),
    ((3, 13), "v2.13", T),
    ((3, 13), "v2.9", A), ((3, 13), "v2.11", A),
    ((3, 13), "v2.12", A),
]
```

After importing the archived helper in a separate process, the capture loop is:

```python
oracle = {}
for version, branch, mode in CASES:
    case = old_helpers.make_case(archive_root, version, branch, mode)
    oracle[case.id] = {}
    for kind, root, profile in (
        ("stubs", case.stubs_root, case.stub_profile),
        ("errors", case.errors_root, case.error_profile),
    ):
        tree = old_helpers.read_tree(old_helpers.resolve_profile(root, profile))
        oracle[case.id][kind] = {name: data.hex() for name, data in tree.items()}
assert len(oracle) == 13
assert all(len(kinds["stubs"]) == 31 for kinds in oracle.values())
```

Here `archive_root` is `$E/oracle-source`; `old_helpers` is imported after inserting `str(archive_root / "tests")` into `sys.path`; write `oracle` with `json.dumps(..., indent=2, sort_keys=True)`. JSON here is ignored audit evidence, not the shipped catalog. Never import old/new modules of the same name in one process to compute both sides of the proof.

At each task: retain focused red/green logs, negative controls, cumulative endpoint results, hooks, diff review and a report in `task-N-report.md`. Scoped commits follow each task. Investigate before continuing if a previously passing contract fails.

## File map and task boundaries

| File | Responsibility | Task |
| --- | --- | --- |
| `tests/snapshot_catalog.py` | TOML schema/path validation, physical loading, logical comparison/context | 1 |
| `tests/snapshot_test_support.py` | Independent synthetic TOML/payload fixtures and filesystem inventory for tests | 1 |
| `tests/unit/test_snapshot_catalog.py` | Reader, confinement, missing/extra data, dependency contracts | 1 |
| `pyproject.toml`, `uv.lock`, `tox.ini`, `.github/workflows/ci.yml` | Approved test dependency provisioning only | 1 |
| `tests/snapshot_updates.py` | Copy-on-write planning, TOML edits, publication and scoped cleanup | 2 |
| `tests/unit/test_snapshot_updates.py` | Editor behavior, no-op/isolation/failure contracts | 2 |
| `tests/snapshot_cases.toml`, `tests/stubs/**`, `tests/errors/**` | Mechanical reference migration | 3 |
| `tests/snapshot_helpers.py`, `tests/test_demo_stubs.py`, `tests/test_demo_errors.py` | Catalog selection and diagnostic glue, not process rewrites | 3 |
| `tests/test_snapshot_helpers.py` | Adapt only layout-dependent synthetic integration fixtures/assertions | 3 |
| `tests/unit/test_snapshot_catalog.py` | Permanent independent catalog inventory/closure checks | 3 |
| `tests/README.md` | Dependency commands in Task 1; complete new workflow in Task 4 | 1, 4 |

Tasks 1 and 2 leave the old native reference route active and test the new modules synthetically. Task 3 switches the native route and payload layout together. Do not publish a half-migrated state. Task 4 supplies full acceptance and final documentation.

Every worker brief includes Global Constraints, workspace/baseline, this file map, the shared interface contract and its task text. Give the Task 3 worker/controller the Task 4 evidence-wrapper recipes for its first matrix run; these are reusable ignored audit tools, not a dependency on unimplemented shipped code.

## Shared interface contract

Types below are defined in Task 1 and consumed unchanged thereafter:

```python
Snapshot = dict[str, bytes]  # import the existing alias from snapshot_helpers
Cases = dict[str, dict[str, dict[str, str]]]
KINDS = ("stubs", "errors")
```

`Catalog` is a frozen dataclass with `repo: Path`, `path: Path`, `raw: bytes`, `cases: Cases`, and `pools: dict[str, Snapshot]`. Treat its nested dictionaries as immutable; editor planning uses `copy.deepcopy`. Methods:

- `mapping(case_id: str, kind: str) -> dict[str, str]`: validate selection, return a copy.
- `snapshot(case_id: str, kind: str) -> Snapshot`: logical name → referenced bytes, not the whole pool.
- `context(case_id: str, kind: str, names: Iterable[str] | None = None) -> str`: catalog/case/kind plus logical entry → absolute path, or `<unmapped>`.

Reader functions:

- `validate_name(value: object, *, component: bool = False) -> Path`.
- `safe_path(repo: Path, relative: str) -> Path`: repo is the already resolved trusted root; inspect every existing component with `lstat`, reject symlinks/special files and non-directory intermediate components. Missing suffixes are allowed for planning; this function creates nothing.
- `parse_model(raw: bytes, path: Path) -> Cases`: pure schema/path/ownership validation, without requiring new planned files to exist.
- `validate_files(repo: Path, cases: Cases) -> dict[str, Snapshot]`: validate both roots, scan all entries with existing `read_tree`, and require every referenced file. Unreferenced regular files remain inert.
- `load_catalog(repo: Path) -> Catalog`: resolve trusted repo, validate/read `tests/snapshot_cases.toml`, parse and load files; wrap filesystem/parse failures with catalog context and original cause.
- `select_expected(catalog: Catalog, case_id: str, kind: str, actual: Snapshot, only: frozenset[str] | None) -> Snapshot`: validate every actual byte value/path and scope; return the selected expected snapshot.
- `changed_names(expected: Snapshot, actual: Snapshot) -> tuple[str, ...]`: sorted logical differences.
- Final `check_case(repo: Path, case_id: str, kind: str, actual: Snapshot, *, update: bool = False, only: frozenset[str] | None = None) -> str`: normal path loads/compares and returns context. Task 1 implements the read-only signature without `update`; Task 2 adds that keyword and lazy editing delegation. Mismatches use existing `SnapshotMismatch` so `diff.patch` retention continues.

Task 2 exports `update_snapshot` with the same arguments except `update`, returning `UpdateReport`. `UpdateReport` fields: `catalog: Path`, `case_id: str`, `kind: str`, `changed: tuple[str, ...]`, `old_refs/new_refs: dict[str, str]`, and `created/reused/removed: tuple[str, ...]` (physical relative filenames). `describe() -> str` includes all fields with absolute reference locations. No-op reports have no created/reused/removed files.

---

### Task 1: Strict read-only catalog and test dependencies

**Files:** Create the reader, shared synthetic support and reader tests listed above. Edit only dev requirements in root pyproject, necessary lock metadata/package entries, tox dependency lists, the CI compiler-free installation step/name and README dependency commands.

**Interfaces:** Consumes existing `HarnessError`, `SnapshotMismatch`, `Snapshot`, `relative_file`, `read_tree`, `diff_tree`. Produces all Task 1 interfaces above; editor delegation is added in Task 2, not a fake implementation now.

- [ ] **Step 1: Add independent fixtures and first reader contracts.**

The fixture helper must not call reader/editor code. Its API is `write_catalog(repo: Path, cases: Cases, payloads: dict[str, Snapshot]) -> Path`, returning `repo`; it creates both roots, writes supplied byte payloads, then renders a small TOML document with literal strings. `tree_state(root: Path) -> dict[str, tuple[str, bytes | str]]` inventories directories, regular bytes, raw link targets and special-entry tags using `os.walk(..., followlinks=False)`/`lstat`; never read a FIFO. Include an inert `.git/index` sentinel in preservation tests, and use real index audits in acceptance.

Use JSON string quoting with `ensure_ascii=False` only as a fixture string-literal encoder (its escapes are TOML-compatible for these strings), not as a catalog format:

```python
import json
import os
from pathlib import Path
import stat


def tree_state(root):
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


def write_catalog(repo, cases, payloads):
    lines = ["format = 1", ""]
    for kind in ("stubs", "errors"):
        root = repo / "tests" / kind
        root.mkdir(parents=True, exist_ok=True)
        for name, data in payloads.get(kind, {}).items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    quote = lambda value: json.dumps(value, ensure_ascii=False)
    for case, kinds in cases.items():
        for kind in ("stubs", "errors"):
            lines.append(f"[cases.{quote(case)}.{kind}]")
            for name, reference in kinds[kind].items():
                lines.append(f"{quote(name)} = {quote(reference)}")
            lines.append("")
    (repo / "tests/snapshot_cases.toml").write_bytes("\n".join(lines).encode())
    return repo
```

Start tests with literal mappings and a payload not referenced by the catalog:

```python
from pathlib import Path
import pytest
from snapshot_catalog import load_catalog, check_case
from snapshot_helpers import HarnessError, SnapshotMismatch
from snapshot_test_support import write_catalog, tree_state


def sample(tmp_path):
    cases = {
        "a": {"stubs": {"demo/a.pyi": "shared/a.pyi"}, "errors": {}},
        "b": {"stubs": {"demo/a.pyi": "shared/a.pyi"}, "errors": {}},
    }
    return write_catalog(tmp_path / "repo", cases, {
        "stubs": {"shared/a.pyi": b"old\n", "unused.pyi": b"inert\n"},
    })


def test_literal_selection_and_read_only_failure(tmp_path):
    repo = sample(tmp_path)
    before = tree_state(repo)
    catalog = load_catalog(repo)
    assert catalog.snapshot("a", "stubs") == {"demo/a.pyi": b"old\n"}
    with pytest.raises(SnapshotMismatch) as exc:
        check_case(repo, "a", "stubs", {"demo/extra.pyi": b"new\n"})
    message = str(exc.value)
    assert "Missing: demo/a.pyi" in message
    assert "Unexpected: demo/extra.pyi" in message
    assert "<unmapped>" in message
    assert str(repo / "tests/stubs/shared/a.pyi") in message
    assert tree_state(repo) == before


@pytest.mark.parametrize("name", ["", "../x", "/x", "a\\b", "a//b", "a/./b", "x\0y"])
def test_unsafe_reference_names_are_rejected(tmp_path, name):
    repo = sample(tmp_path)
    text = (repo / "tests/snapshot_cases.toml").read_text()
    import json
    text = text.replace('"shared/a.pyi"', json.dumps(name))
    (repo / "tests/snapshot_cases.toml").write_text(text)
    before = tree_state(repo)
    from snapshot_catalog import parse_model
    with pytest.raises(HarnessError, match="[Uu]nsafe|[Ii]nvalid"):
        parse_model(text.encode(), repo / "tests/snapshot_cases.toml")
    with pytest.raises(HarnessError):
        load_catalog(repo)
    assert tree_state(repo) == before
```

Add parametrized literal malformed documents covering format `true`, format `2`, non-table `cases`, missing/extra kind, non-string reference, duplicate TOML keys, ancestor-conflicting logical names and one physical file owned by two logical names. Require the specific schema/path error, not just any exception. For example:

```python
@pytest.mark.parametrize("raw, clue", [
    (b"format = true\n[cases.a]\nstubs = {}\nerrors = {}\n", "format"),
    (b"format = 2\n[cases.a]\nstubs = {}\nerrors = {}\n", "format"),
    (b"format = 1\ncases = 2\n", "cases"),
    (b"format = 1\n[cases.a]\nstubs = 2\nerrors = {}\n", "stubs"),
    (b"format = 1\n[cases.a.stubs]\n", "errors"),
    (b"format = 1\nformat = 1\n[cases]\n", "TOML"),
])
def test_schema_failures(tmp_path, raw, clue):
    from snapshot_catalog import parse_model
    with pytest.raises(HarnessError, match=clue):
        parse_model(raw, tmp_path / "snapshot_cases.toml")
```

For filesystem negatives, replace the catalog, `tests`, a payload root, a nested directory, a mapped file and an unreferenced file with symlinks (including dangling/outside links), one scenario per fresh fixture. Assert no outside/sentinel writes. Test missing roots/files, nonregular entries and read/scan `OSError` propagation with retained cause. Unknown case/kind must fail rather than fall back. Explicit empty kind tables must load.

- [ ] **Step 2: Record the initial RED, then declare approved dependencies.**

Run the new reader file before implementing it; missing-module collection failure is the initial RED only. Later behavioral controls must also prove the actual guards are sensitive.

```sh
env -u VIRTUAL_ENV UV_LINK_MODE=copy uv run --no-project --isolated --python 3.10 \
  --with 'pytest>=8,<9' --with 'tomli>=2,<3; python_version < "3.11"' \
  --with 'tomlkit>=0.13,<1' python -m pytest tests/unit/test_snapshot_catalog.py -q
```

Add the two requirements from Global Constraints to `[dependency-groups].dev` and to both tox `deps` lists. Do not sync the root dev group to run isolated tests. The CI compiler-free installation command becomes:

```sh
uv pip install --python .venv/bin/python 'pytest>=8,<9' \
  'tomli>=2,<3; python_version < "3.11"' 'tomlkit>=0.13,<1' dist/*.whl
```

Rename that step to describe test dependencies, not “pytest only.” Keep its wheel, interpreter and installed-pytest commands unchanged. Update both README compiler-free commands to supply the two requirements, adding `--isolated` to the harness-only uv command too. Keep focused production-only tests free of native packages.

Run `uv lock` without `--upgrade`. Compare old/new package `(name, version, source)` inventories with stdlib tomllib on Python 3.13: every prior package record must remain; only tomlkit/new necessary metadata may be added. Inspect all lock diffs. If unrelated versions move, investigate before proceeding.

- [ ] **Step 3: Implement the reader, without connecting native tests yet.**

Use `from __future__ import annotations`. Implement pure model validation before filesystem loading. This path validator is the shared starting point:

```python
import stat
from snapshot_helpers import HarnessError, relative_file


def validate_name(value, *, component=False):
    if not isinstance(value, str) or "\0" in value:
        raise HarnessError(f"Invalid snapshot path: {value!r}")
    path = relative_file(value)
    if component and len(path.parts) != 1:
        raise HarnessError(f"Invalid case identifier: {value!r}")
    return path


def safe_path(repo, relative):
    parts = validate_name(relative).parts
    path = repo
    for index, part in enumerate(parts):
        path = path / part
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            raise HarnessError(f"Unexpected symlink: {path}")
        if index < len(parts) - 1 and not stat.S_ISDIR(mode):
            raise HarnessError(f"Non-directory snapshot parent: {path}")
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise HarnessError(f"Unexpected filesystem entry: {path}")
    return path
```

`parse_model` imports the version-selected parser inside the function, reports missing tomli with its installation requirement, decodes UTF-8 without newline translation, and wraps parser errors with `TOML` plus the catalog path. Validate exact root keys `format/cases`, `type(format) is int and format == 1`, string safe case IDs and exactly `stubs/errors` mappings. Require string safe values. Reject logical ancestor conflicts in each table and maintain `(kind, physical_name) -> logical_name` ownership across cases. Return fresh plain nested dictionaries.

`validate_files` calls `safe_path(repo, "tests/stubs")` and `safe_path(repo, "tests/errors")`, requires actual directories, and then calls existing `read_tree` for each root. This scans even unreferenced entries and rejects nested symlinks/special files. Every mapped relative name must exist in the corresponding pool dictionary. Schema/path failures identify their offending TOML entry where known; missing mapped-file errors include case, kind, logical name and absolute target. Wrap `OSError` with catalog/root/path context and keep `__cause__`. A scan failure on an unreferenced entry must identify it as such, not invent a mapping.

The dataclass methods are straightforward literal lookups:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Catalog:
    repo: Path
    path: Path
    raw: bytes
    cases: dict[str, dict[str, dict[str, str]]]
    pools: dict[str, dict[str, bytes]]

    def mapping(self, case_id, kind):
        if case_id not in self.cases:
            raise HarnessError(f"Catalog {self.path}: unknown case {case_id!r}")
        if kind not in ("stubs", "errors"):
            raise HarnessError(f"Catalog {self.path}: unknown kind {kind!r}")
        return dict(self.cases[case_id][kind])

    def snapshot(self, case_id, kind):
        return {name: self.pools[kind][ref]
                for name, ref in self.mapping(case_id, kind).items()}

    def context(self, case_id, kind, names=None):
        mapping = self.mapping(case_id, kind)
        lines = [f"Catalog: {self.path}", f"Case: {case_id}/{kind}"]
        for name in sorted(mapping if names is None else names):
            target = self.repo / "tests" / kind / mapping[name] if name in mapping else "<unmapped>"
            lines.append(f"Entry cases[{case_id!r}][{kind!r}][{name!r}]: {target}")
        return "\n".join(lines) + "\n"
```

`select_expected` validates all actual names/content before comparison, rejects logical ancestor conflicts and validates every `only` name. Reject actual keys outside `only`. Return either the whole logical expected snapshot or its exact scope. Use `bytes`, not decoded/string-normalized content. `changed_names` compares key presence and bytes in sorted union order.

Implement the normal comparison route:

```python
def check_case(repo, case_id, kind, actual, *, only=None):
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
```

The old native route remains active in this commit. Task 2 extends this tested read-only function with the explicit update keyword; no editor stub or unsupported update mode is exposed in Task 1.

- [ ] **Step 4: Prove confinement/read-only behavior and run cumulative tests.**

Run focused and cumulative compiler-free suites on Python 3.10 and 3.13 with the dependencies above. In a fresh subprocess install an import blocker for `tomlkit` and `snapshot_updates`, then load/compare a valid synthetic catalog; require success. A separate import blocker for tomli/tomllib/tomlkit must still allow importing `native_matrix` and its existing helper-only matrix tests. On Python 3.10, a direct reader subprocess blocked from importing tomli must report the dependency clearly; do not remove pytest's own tomli dependency and misattribute a pytest startup error.

Use process-local negative controls: bypass `validate_name` for a traversal test, omit unmapped-output comparison, or remove a schema guard, then require the corresponding new test to fail for the intended assertion. Restore unmodified green runs; never ship mutants. Inventory the complete reference trees/catalog (currently absent)/index before and after tests.

Run all-files hooks and inspect dependencies/CI diff. Confirm no root runtime dependencies, native pins, production files, native setup, or existing expectations changed.

- [ ] **Step 5: Self-review and commit Task 1.**

```sh
git add tests/snapshot_catalog.py tests/snapshot_test_support.py \
  tests/unit/test_snapshot_catalog.py pyproject.toml uv.lock tox.ini \
  .github/workflows/ci.yml tests/README.md
git diff --cached --check
git commit -m "test: add strict TOML snapshot catalog reader"
```

Review gate: schema/path/data correctness, whole-catalog validation, read-only guarantees, lazy import boundaries, and narrowly scoped dependency wiring.

### Task 2: Case-scoped editor and failure-sensitive publication

**Files:** Create `tests/snapshot_updates.py` and `tests/unit/test_snapshot_updates.py`; add lazy update delegation to `tests/snapshot_catalog.py`.

**Interfaces:** Consumes Task 1 reader/model/context utilities and shared independent fixtures. Produces `UpdateReport`/`update_snapshot` described above, plus internal helpers with explicit responsibilities:

- `plan_update(catalog, case_id, kind, actual, only) -> UpdatePlan` performs no writes.
- `render_update(catalog, plan) -> bytes` lazily imports tomlkit and validates resulting model.
- `write_payloads(catalog, plan) -> None` exclusively creates the planned directory/files.
- `write_temporary_catalog(catalog, raw) -> Path` creates a sibling file, preserves original file mode, and reports its path if writing fails.
- `publish_catalog(catalog, temporary) -> None` revalidates safe path and unchanged raw bytes immediately before `os.replace`.
- `cleanup_payloads(catalog, plan) -> None` removes only planned orphan files/affected empty ancestors; unexpected errors propagate.

`UpdatePlan` is a dataclass with `case_id`, `kind`, `changed`, `old_refs`, `new_refs`, `cases` (deep-copied proposed model), `snapshot` (intended full selected-kind bytes), `directory: str | None`, `new_files: Snapshot` (physical names), and `reused/removed: tuple[str, ...]`.

Use the following concrete report type; annotations and field order are shared with the orchestrator below:

```python
from dataclasses import dataclass
from pathlib import Path


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
        lines = [f"Case: {self.case_id}/{self.kind}",
                 f"Catalog: {self.catalog}; changed: {self.changed}"]
        for name in self.changed:
            old = str(root / self.old_refs[name]) if name in self.old_refs else "<unmapped>"
            new = str(root / self.new_refs[name]) if name in self.new_refs else "<unmapped>"
            lines.append(f"{name}: {old} -> {new}")
        for action in ("created", "reused", "removed"):
            lines.append(f"{action}: {tuple(str(root / p) for p in getattr(self, action))}")
        return "\n".join(lines)
```

- [ ] **Step 1: Write sharing, reuse, no-op and scoped-update RED tests.**

Use independently rendered fixtures, not the editor to establish preconditions:

```python
import pytest
from snapshot_catalog import load_catalog
from snapshot_helpers import HarnessError
from snapshot_updates import update_snapshot
from snapshot_test_support import write_catalog, tree_state


def shared_repo(tmp_path):
    cases = {
        key: {"stubs": {"demo/a.pyi": "shared/a.pyi"},
              "errors": {"demo.errors.stderr.txt": "shared/error.txt"}}
        for key in ("a", "b")
    }
    return write_catalog(tmp_path / "repo", cases, {
        "stubs": {"shared/a.pyi": b"old\n", "unrelated.pyi": b"leave\n"},
        "errors": {"shared/error.txt": b"fatal\n"},
    })


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
    assert (repo / "tests/stubs/unrelated.pyi").read_bytes() == b"leave\n"


def test_noop_is_byte_identical(tmp_path):
    repo = shared_repo(tmp_path)
    before = tree_state(repo)
    report = update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"old\n"})
    assert report.changed == report.created == report.reused == report.removed == ()
    assert tree_state(repo) == before


def test_planning_preserves_model_and_files(tmp_path):
    import copy
    from snapshot_updates import plan_update
    repo = shared_repo(tmp_path)
    catalog = load_catalog(repo)
    original_model = copy.deepcopy(catalog.cases)
    original_files = tree_state(repo)
    plan = plan_update(catalog, "a", "stubs", {"demo/a.pyi": b"new\n"}, None)
    assert plan.cases != original_model
    assert catalog.cases == original_model
    assert tree_state(repo) == original_files
```

Add literal cases for full add/delete, `only` preserving other mappings, actual keys outside scope, a prospective logical ancestor conflict with an unselected scoped entry, file/directory shape changes, pre-existing numbered directories/files and bad namespace parents. Assert one numbered directory per update contains all newly needed files, and matching variants are chosen lexicographically only among referenced files of the same kind/name. An identical unreferenced file must stay inert. Existing referenced files must never be overwritten, even for a single consumer.

Use hand-authored LF and CRLF TOML with top-level/table/inline comments. Replace one value and require an exact expected text replacement; delete only that entry's inline comment with the entry, preserve unrelated comments, and append new entries without reordering old tables. No-op subprocesses blocked from importing tomlkit must pass; changed updates in that process must fail before filesystem mutation and name the missing dependency.

- [ ] **Step 2: Run focused RED tests and implement side-effect-free planning/rendering.**

Use the Task 1 isolated command with `tests/unit/test_snapshot_updates.py`. Record initial RED separately from later guard mutations.

Planning algorithm (implement directly, not as a rule framework):

```python
import copy


def plan_update(catalog, case_id, kind, actual, only):
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
        matches = sorted({
            mapping[kind][name]
            for mapping in catalog.cases.values()
            if name in mapping[kind]
            and catalog.pools[kind][mapping[kind][name]] == actual[name]
        })
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
    return UpdatePlan(case_id, kind, changed, old_refs, new_refs, cases,
                      intended, directory, new_files, tuple(sorted(reused)), removed)
```

Validate the prospective model before writing. The physical directory number is a label, not a fallback or version selector. `safe_path` treats any existing numbered file/directory as occupied, and rejects symlink/special entries or non-directory parents. If there are no logical changes, return the empty report before importing tomlkit or choosing/creating directories.

Rendering operates only on changed entries, preserving existing keys where values did not change:

```python
def render_update(catalog, plan):
    try:
        import tomlkit
    except ImportError as exc:
        raise HarnessError("Catalog editing requires tomlkit>=0.13,<1") from exc
    document = tomlkit.parse(catalog.raw.decode("utf-8"))
    table = document["cases"][plan.case_id][plan.kind]
    for name in plan.changed:
        if name in plan.new_refs:
            table[name] = plan.new_refs[name]
        else:
            del table[name]
    raw = tomlkit.dumps(document).encode("utf-8")
    if parse_model(raw, catalog.path) != plan.cases:
        raise HarnessError("Serialized catalog differs from the planned mappings")
    return raw
```

Add tests for invalid planned paths/ownership and parser/serializer failure before any allocation. The editor may not bypass strict model validation just because it constructed the data.

- [ ] **Step 3: Implement safe publication and phase-specific failures.**

`write_payloads` rechecks safe paths. Create `variants/<case-id>` parents only after checking every existing component; create the numbered directory with `exist_ok=False`. Within it, create needed logical parent directories and open every new file with `xb`. Never call `write_bytes` on a pre-existing reference. A failure can leave only newly allocated, unreferenced files/directories.

`write_temporary_catalog` uses `tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=catalog.path.parent, prefix=".snapshot_cases-", suffix=".toml")`. Record its name immediately and preserve `stat.S_IMODE(catalog.path.stat().st_mode)` before closing. If its write fails, the raised `HarnessError` must include the temporary path and original cause. Validate the catalog's parent path before creating the temporary file.

`publish_catalog` rechecks catalog/temporary paths against symlink/nonregular substitutions and compares on-disk catalog bytes with `catalog.raw`. If different, leave the external edit intact and fail. Then call `os.replace(temporary, catalog.path)`.

The orchestrator has this fixed order:

```python
def update_snapshot(repo, case_id, kind, actual, *, only=None):
    try:
        catalog = load_catalog(repo)
        plan = plan_update(catalog, case_id, kind, actual, only)
    except HarnessError as exc:
        raise HarnessError(f"Case {case_id}/{kind}; catalog not published: {exc}") from exc
    report = UpdateReport(catalog.path, case_id, kind, plan.changed,
                          plan.old_refs, plan.new_refs, tuple(sorted(plan.new_files)),
                          plan.reused, plan.removed)
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
                    if prospective.snapshot(other_case, other_kind) != catalog.snapshot(other_case, other_kind):
                        raise HarnessError("An unselected expectation changed")
        temporary = write_temporary_catalog(catalog, raw)
        publish_catalog(catalog, temporary)
        published = True
        cleanup_payloads(catalog, plan)
    except Exception as exc:
        state = "published" if published else "not published"
        raise HarnessError(
            catalog.context(case_id, kind)
            + f"Update failed; catalog {state}; temporary={temporary}; "
            + f"planned payloads={tuple(str(catalog.repo / 'tests' / kind / p) for p in sorted(plan.new_files))}; "
            + f"planned directory={plan.directory}; cleanup targets={plan.removed}: {exc}"
        ) from exc
    return report
```

The helper that creates a temporary file includes its path in its own failure, since assignment in the caller may not yet have completed. For pre-publication payload failures, report the allocated directory and every existing planned payload so a partially written file is discoverable. Do not imply a planned but never created file exists. No automatic rollback or unrelated orphan sweep.

Cleanup unlinks only `plan.removed`, each resolved through `safe_path`. After all successful unlinks, collect affected parent directories strictly below the appropriate root, deduplicate them, and attempt `rmdir` deepest-first. Suppress only `ENOTEMPTY/EEXIST`; propagate other errors. Do not remove roots, recursively delete, or collect siblings. A post-publication error explicitly says mappings already changed.

Add keyword-only `update: bool = False` to `check_case` and put this branch before the unchanged read-only body:

```python
if update:
    from snapshot_updates import update_snapshot
    return update_snapshot(repo, case_id, kind, actual, only=only).describe()
```

- [ ] **Step 4: Inject failures at each boundary and prove restoration.**

Parametrize the helpers above for pre-publication failure; compare only original referenced files/catalog as well as asserting any new leftovers are reported (full filesystem equality is not promised after writes start):

```python
@pytest.mark.parametrize("stage", [
    "render_update", "write_payloads", "write_temporary_catalog", "publish_catalog",
])
def test_prepublication_failure_preserves_live_references(tmp_path, monkeypatch, stage):
    import snapshot_updates as editor
    repo = shared_repo(tmp_path)
    original = load_catalog(repo)
    def fail(*args, **kwargs):
        raise OSError(f"injected {stage}")
    monkeypatch.setattr(editor, stage, fail)
    with pytest.raises(HarnessError, match="not published"):
        update_snapshot(repo, "a", "stubs", {"demo/a.pyi": b"changed\n"})
    assert original.path.read_bytes() == original.raw
    after = load_catalog(repo)
    for case in original.cases:
        for kind in ("stubs", "errors"):
            assert after.snapshot(case, kind) == original.snapshot(case, kind)
```

These outer-boundary cases are not sufficient alone. Also inject actual low-level partial `xb` writes, temporary-file writes, `os.replace`, orphan `unlink`, and directory `rmdir`. Require original cause and correct publication state. For post-publication cleanup failure, selected expectations are new, others unchanged, and leftovers are named. Mutate the catalog immediately before calling the real publication helper and prove the external bytes survive. Simulate corrupted new payload bytes before physical validation and require failure without publication.

Add behavior controls disabling copy-on-write (overwrite the shared file), reusing an unreferenced candidate, removing raw-byte stale-edit detection, and swallowing cleanup `OSError`; each must break a named contract test. Restore and rerun focused plus cumulative source endpoint suites. No mutation reaches real references.

- [ ] **Step 5: Self-review and commit Task 2.**

```sh
git add tests/snapshot_updates.py tests/unit/test_snapshot_updates.py tests/snapshot_catalog.py
git diff --cached --check
git commit -m "test: add case-scoped TOML snapshot updates"
```

Review gate: no-op import/byte behavior, in-memory planning, isolation across case/kind/scope, deterministic reuse/allocation, comment preservation, publication ordering and cleanup/error semantics. Old native tests remain on their old reference route until Task 3.

### Task 3: Mechanical migration and native integration

**Files:** Create catalog and new payloads, remove old copies/aliases; adapt `DemoCase`/`make_case`, native reference glue, layout-dependent helper tests, and add shipped catalog inventory tests.

**Interfaces:** Consumes `load_catalog`, `check_case`, `UpdateReport` and independent archive oracle. Produces a `DemoCase.catalog_path` property, retaining `id`, `stubs_root`, `errors_root`, runtime version and configuration fields. Remove obsolete `stub_profile/error_profile` properties from the native case model; keep generic directory helper APIs unchanged, never as fallback.

- [ ] **Step 1: Write failing catalog inventory and native-glue tests.**

Add a test of the actual repository catalog's exact 13 case IDs using the independent literal list from the baseline section, not a list generated by the reader. Require `demo/__init__.pyi` and `demo.errors.stderr.txt` in their respective kinds. Assert every payload file is referenced, no symlinks exist, and no identical same-kind/name variants have multiple physical copies. Keep the exact baseline 31-file sets and 61-payload count in migration evidence, not permanent assertions that would block future legitimate file/variant additions. The independent oracle checks exact initial filenames and bytes.

Adapt the existing synthetic integration fixture setup with the shared literal TOML writer. For example:

```python
case = h.DemoCase(repo, (3, 13), "v3.0", "numpy-array-wrap-with-annotated")
write_catalog(repo, {
    case.id: {
        "stubs": {"demo/__init__.pyi": "seed/init.pyi"},
        "errors": {"demo.errors.stderr.txt": "seed/stderr.txt"},
    },
}, {
    "stubs": {"seed/init.pyi": b"original"},
    "errors": {"seed/stderr.txt": b"original"},
})
```

After a synthetic successful update, assert through a fresh `load_catalog` that selected bytes changed and unrelated kind/case data did not. Failure tests must compare the catalog and both pools, not just a now-obsolete directory. Preserve the existing generator/formatter failure, traceback, no-output and empty-generation guards and their expected diagnostics. Make the selection test require an existing catalog/case and the runtime Python ID rather than directory profile properties.

Only these existing test functions need layout adaptation:
`test_case_requires_existing_profiles_and_uses_runtime_python`,
`test_success_update_never_accepts_failed_generation_or_formatting`,
`test_error_update_rejects_traceback_even_with_exit_one`,
`test_integration_check_and_update_paths_with_synthetic_output`, and
`test_empty_output_cannot_erase_references`. Retain all generic filesystem,
process, formatting, diagnostics and entrypoint tests. New diagnostic/catalog
protection regressions belong in the new unit files unless they directly extend
an existing diagnostic parametrization; explain any collection-count change.

Record RED before migration/wiring. The permanent inventory assertion should fail because the catalog is not yet present; synthetic integration tests should fail at the old selection route, not be skipped.

- [ ] **Step 2: Wire literal selection and protect catalog diagnostics.**

`DemoCase.catalog_path` returns `repo / "tests/snapshot_cases.toml"`. In `make_case`, preserve version/branch/mode validation and ID construction, then lazily import `load_catalog`, validate selection of both kinds and return the case. Prepend the constructed case ID to catalog/preflight `HarnessError` messages and retain their cause. Do not cache its catalog globally/session-wide or import the reader while importing `BRANCHES`.

In both native tests, set `expected = case.catalog_path`, include it along with both roots in `reference_roots`, and replace only the final comparison/update call:

```python
message = check_case(
    case.repo, case.id, "stubs", actual, update=update_snapshots
)
if update_snapshots:
    report_update(message)
```

For errors, keep `filename = "demo.errors.stderr.txt"`, the current validated `stderr`, kind `"errors"`, and `only=frozenset({filename})`. All generator argv, cwd, status checks, logging, formatting order, address normalization, output assertions and timeout helpers remain unchanged.

Extend `diagnostics` with optional `reference_details: str = ""`, appended to context before writing it; preserve old callers. Compute the selected mapping context with the reader so generator/formatter failures as well as diffs identify the TOML entries and real payload paths. Preflight failures remain explicit setup failures with catalog/case/path context. Test a workspace equal to/above the catalog and an artifact path inside a catalog-path symlink; all must fail before reference writes. Existing diagnostic symlink and secondary-error contracts still apply with the catalog in the protected set.

The subprocess grouped-mode test in `tests/unit/test_native_support.py` copies only three existing support files and overrides the native fixture. It must continue passing because reader imports are lazy; do not turn it into a native/catalog setup test.

- [ ] **Step 3: Generate the catalog from the oracle, then remove old references.**

Create `$E/migrate_snapshots.py`, an ignored one-shot script run with Python 3.13 + tomlkit. It must refuse to run if catalog/new destinations already exist or if current old reference bytes/links differ from the pre-migration inventory. First calculate all mappings/payloads in memory, verify no collisions, and retain the manifest preview as evidence. No generator invocation.

The grouping/naming core is:

```python
from collections import defaultdict
from pathlib import PurePosixPath
import re

groups = defaultdict(list)
for case_id, kinds in oracle.items():
    for name, encoded in kinds["stubs"].items():
        groups[(name, bytes.fromhex(encoded))].append(case_id)
new_cases = {case: {"stubs": {}, "errors": {}} for case in sorted(oracle)}
new_payloads = {}
for (name, content), members in sorted(groups.items()):
    chosen = min(members)
    match = re.fullmatch(
        r"python-(\d+)\.(\d+)-pybind11-v(\d+)\.(\d+)-numpy-array-(wrap-with-annotated|use-type-var)",
        chosen,
    )
    assert match, chosen
    major, minor, pbmajor, pbminor, mode = match.groups()
    label = "shared" if len(members) == len(oracle) else (
        f"py{major}{minor}-pb{pbmajor}{pbminor}-"
        + ("annotated" if mode == "wrap-with-annotated" else "type-var")
    )
    logical = PurePosixPath(name)
    physical = (logical.parent / logical.stem / (label + logical.suffix)).as_posix()
    assert physical not in new_payloads
    new_payloads[physical] = content
    for case in members:
        new_cases[case]["stubs"][name] = physical
assert len(new_payloads) == 59
```

For stderr, retain exact current `tests/errors/pybind11-v2.9/demo.errors.stderr.txt` and `tests/errors/pybind11-v3.0/demo.errors.stderr.txt`. Match each oracle stderr by exact bytes to those two files; require exactly one match and map directly to it. Verify no canonical stderr bytes change.

Render one TOML document via tomlkit with integer format 1 and complete explicit case/kind tables, inserting sorted cases and sorted logical filenames. Validate `parse_model` equals the proposed model before writing. Write new stub payloads exclusively, then the catalog. Remove only the original tracked stub files/links and three old stderr aliases, using the saved list and explicit `git rm -- <paths>`; retain the two stderr files. Remove now-empty old directories without recursive deletion. Do not use a blanket `git add -A` or regenerate payloads.

The temporary overlap with old symlinks cannot be loaded by the new strict reader; remove old entries before running `load_catalog`. This is one coordinated working-tree migration, committed only after all gates pass.

Verify all 13 new effective case/kind maps against oracle **bytes**, then cross-check hashes against `rebase-after.json`. Require exactly 61 regular payloads, no links, every payload referenced and no pruned-only data. Retain old→new mapping and Git staged/unstaged inventory before committing.

- [ ] **Step 4: Run glue negatives, preservation audits and the first full native matrix.**

Run focused and cumulative source endpoint suites. Repeat synthetic generator/formatter/empty-output/traceback negatives with the new catalog: all failures leave both pools/catalog/index unchanged and preserve diagnostics. Test a successful synthetic update with two selected modes in one process so the second sees fresh mappings.

Using the audit wrapper defined in Task 4, run all default native profiles serially through the local generator-wheel route. Preserve their old tmp/log trees before tox resets them. Inspect all JUnit case IDs, the actual 11 expanded tox names, two checks per mode and no skips/errors. Require the current canonical catalog/pool/index state to remain unchanged through the batch. Account for the number of harness self-tests rather than assuming an old total.

For a real mismatch/retention control, use a disposable archived checkout and existing installed native interpreter; change one copied referenced payload, run exactly that case's stub check with `--artifacts-dir` outside copied references, and require failure naming catalog entry/logical file/canonical path plus retained process logs/diff. Both real and copied references remain unchanged by check mode. Restore copied bytes and pass. Never update the real catalog to make this control green.

- [ ] **Step 5: Self-review and commit the coordinated migration.**

```sh
git add tests/snapshot_cases.toml tests/stubs tests/errors tests/snapshot_helpers.py \
  tests/test_demo_stubs.py tests/test_demo_errors.py tests/test_snapshot_helpers.py \
  tests/unit/test_snapshot_catalog.py
# Include only any new diagnostic tests explicitly added to the new unit files.
git diff --cached --check
git commit -m "test: share snapshot payloads through explicit TOML cases"
```

Review gate: exact byte/file-set equivalence, no revived historical data, all consumers switched coherently, safety/diagnostics preserved, native flags/process contracts unchanged, no hidden fallback or count/coverage loss.

### Task 4: Documentation and complete local acceptance

**Files:** Finish `tests/README.md`; all verification scripts/reports below stay under this phase's ignored evidence directory. No implementation changes unless acceptance reveals a justified defect, which needs a focused regression and affected reruns.

**Interfaces:** Consumes the complete catalog route, oracle, Task 1 test dependencies and unchanged phase-three tox/native provenance outputs. Produces retained acceptance evidence and the final docs commit.

- [ ] **Step 1: Document the user workflow precisely.**

Keep existing native profile commands/flags and direct installed reruns. Explain catalog literal maps, payload labels as origins rather than selectors, and the distinction between shared reading and case-scoped updating. Update examples to inspect all three reference locations:

```sh
tox -e py313-pb30 -- --numpy-format numpy-array-wrap-with-annotated --update-snapshots
git diff -- tests/snapshot_cases.toml tests/stubs tests/errors
```

Document `-k demo_stubs`/`-k demo_errors`, serial updates, no-op byte guarantees, numbered new variants, reuse, scoped deletions, and explicit empty tables to bootstrap a deliberately added supported case. Adding a catalog case does not schedule it in tox. Explain pre-publication leftovers and post-publication cleanup failures; no rollback promise, bulk GC command or implicit unknown-case creation. Normal checks/artifacts never modify references.

Document these compiler-free commands instead of syncing the root native dev group:

```sh
env -u VIRTUAL_ENV uv run --no-project --isolated --python 3.10 \
  --with 'pytest>=8,<9' --with 'tomli>=2,<3; python_version < "3.11"' \
  --with 'tomlkit>=0.13,<1' python -m pytest tests/unit tests/test_snapshot_helpers.py
```

Keep production-only focused tests possible with pytest alone where the selected tests do not exercise catalog editing. Preserve diagnostics/build log locations, exact pin authority, installed guards, and separate production/packaging bug boundaries.

- [ ] **Step 2: Create the reusable command/reference audit wrapper.**

Save this as `$E/audit.py` before Task 3's first native run; it is an evidence tool, not shipped code. Invocation is `python "$E/audit.py" LABEL -- COMMAND ...`. It must write unique logs and record failures/timeouts before raising, with 3600-second overall timeout and no shared-shell-variable assumptions:

```python
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
E = Path(__file__).resolve().parent
label = sys.argv[1]
assert len(Path(label).parts) == 1 and not Path(label).is_absolute() and label not in (".", "..")
assert sys.argv[2] == "--"
command = sys.argv[3:]
log = E / f"{label}.log"
record = E / f"{label}.json"
assert not (log.exists() or log.is_symlink() or record.exists() or record.is_symlink())

def inventory():
    result = {}
    for relative in ("tests/stubs", "tests/errors", "tests/snapshot_cases.toml"):
        start = root / relative
        paths = [start]
        if start.is_dir() and not start.is_symlink():
            for directory, dirs, files in os.walk(start, followlinks=False):
                paths.extend(Path(directory) / name for name in dirs + files)
        for path in paths:
            key = path.relative_to(root).as_posix()
            if path.is_symlink():
                result[key] = ["link", os.readlink(path)]
            elif path.is_file():
                result[key] = ["file", hashlib.sha256(path.read_bytes()).hexdigest()]
            elif path.is_dir():
                result[key] = ["dir"]
            elif not path.exists():
                result[key] = ["missing"]
            else:
                result[key] = ["special"]
    return {"references": result, "index": subprocess.check_output(
        ["git", "ls-files", "--stage", "-z"], cwd=root).decode()}

env = {k: v for k, v in os.environ.items() if not k.startswith("STUBGEN_")}
for key in ("VIRTUAL_ENV", "PYTHONPATH", "PYTEST_ADDOPTS"):
    env.pop(key, None)
env["UV_LINK_MODE"] = "copy"
before = inventory()
status = None
error = None
try:
    with log.open("xb") as stream:
        status = subprocess.run(command, cwd=root, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=3600).returncode
except Exception as exc:
    error = repr(exc)
finally:
    after = inventory()
    record.write_text(json.dumps({"command": command, "returncode": status,
        "error": error, "before": before, "after": after,
        "unchanged": before == after}, indent=2) + "\n")
assert status == 0 and error is None and before == after, record
print(record)
```

Preserve previous tox outputs using a separate unique batch directory and record every move before each invocation. Save this second script as `$E/preserve_tox.py`, invoked with `LABEL PROFILE...`:

```python
import json
from pathlib import Path
import shutil
import sys

root = Path.cwd()
E = Path(__file__).resolve().parent
label, *profiles = sys.argv[1:]
assert len(Path(label).parts) == 1 and label not in (".", "..")
destination = E / f"{label}-previous-outputs"
destination.mkdir()
moved = []
for profile in profiles:
    assert len(Path(profile).parts) == 1 and profile not in (".", "..")
    for kind in ("tmp", "log"):
        source = root / ".tox" / profile / kind
        if source.exists():
            target = destination / profile / kind
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            moved.append({"from": str(source), "to": str(target)})
            (destination / "moved.json").write_text(json.dumps(moved, indent=2) + "\n")
print(destination)
```

Move only these tmp/log trees; keep environment contents and prior reports. Before a later batch, verify and retain the current command logs, JUnit, builder evidence/logs/CMake caches, exact fixture wheel hash/payload, and installed-package probes. Also retain the local generator wheel and `.tox/.pkg/log/` for a local-wheel batch, correlated with the actual backend/install records; do not assume temporary install-copy paths remain available. Installed extensions and metadata will change on the next installation: capture their verification receipts now, not afterward. Relocated evidence contains original absolute paths; use the recorded prefix relocation when reading its files. Do not merely retain paths to subsequently deleted files.

- [ ] **Step 3: Build a clean supplied artifact and test all compiler-free routes.**

Build from a fresh clean tracked-source archive at the current implementation revision (not from the dirty root `build/` tree). Name each archive/source/dist uniquely and preserve earlier artifacts. Save absolute wheel path and SHA256 **before any installation** to `$E/generator-wheel.path` and `$E/generator-wheel.sha256`.

```sh
E="$PWD/.superpowers/sdd/2026-09-25-test-harness-phase-four"
mkdir "$E/acceptance-source" "$E/acceptance-dist"
git archive HEAD -o "$E/acceptance-source.tar"
tar -xf "$E/acceptance-source.tar" -C "$E/acceptance-source"
(cd "$E/acceptance-source" && env -u VIRTUAL_ENV UV_LINK_MODE=copy \
  uv build --wheel --out-dir "$E/acceptance-dist")
```

Use Python to require exactly one wheel, save its absolute path/hash, inspect its exact 15-file `pybind11_stubgen/` production inventory including `py.typed` against tracked source and require no nested `build/` payload. Do not substitute a dirty-root wheel for this route.

For each 3.10/3.11/3.12/3.13, create fresh `$E/source-VERSION` and `$E/wheel-VERSION` environments and install only pytest/TOML test dependencies, plus the saved wheel in the latter. Commands:

```sh
E="$PWD/.superpowers/sdd/2026-09-25-test-harness-phase-four"
WHEEL=$(< "$E/generator-wheel.path")
for v in 3.10 3.11 3.12 3.13; do
  uv venv --python "$v" "$E/source-$v"
  uv venv --python "$v" "$E/wheel-$v"
  for route in source wheel; do
    UV_LINK_MODE=copy uv pip install --python "$E/$route-$v/bin/python" \
      'pytest>=8,<9' 'tomli>=2,<3; python_version < "3.11"' 'tomlkit>=0.13,<1'
  done
  UV_LINK_MODE=copy uv pip install --python "$E/wheel-$v/bin/python" "$WHEEL"
  env -u STUBGEN_TEST_INSTALLED "$E/source-$v/bin/python" -m pytest \
    tests/unit tests/test_snapshot_helpers.py -q
  STUBGEN_TEST_INSTALLED=1 "$E/wheel-$v/bin/python" -I -m pytest \
    tests/unit tests/test_snapshot_helpers.py -q
done
```

Run these via an evidence driver to retain each command/status/log and before/after reference/index state; the shell illustrates exact argv, not permission to lose failure evidence. Collect test IDs separately and confirm the expected count and no skips/xfails. Run installed-origin wrong-origin RED without `-I`, then restore `-I` and pass; test the actual pytest guard, not just an import probe.

In each fresh environment, use `importlib.util.find_spec` to require demo, numpy, scipy, cmake, pybind11, scikit_build_core, ninja and cmeel absent. Assert source generator origin is the checkout; wheel origin is inside the intended prefix. Verify no editor import with a blocker during read/no-op separately; full suites legitimately install tomlkit for edit tests.

Run all four explicit unit tox profiles with the audit wrapper and preserved old outputs:

```sh
E="$PWD/.superpowers/sdd/2026-09-25-test-harness-phase-four"
python "$E/audit.py" final-unit -- uv run --no-project --isolated \
  --with tox --with tox-uv tox -e py310-unit,py311-unit,py312-unit,py313-unit \
  --result-json "$E/final-unit-result.json"
```

Require 12 complete compiler-free selections in total, actual isolated installed guard behavior in the eight installed routes, and collection accounting for all prior test intent plus new tests.

- [ ] **Step 4: Verify both full native routes and bounded parallel checking.**

Before each command preserve selected profiles' tmp/log trees. Reload the saved artifact path every time:

```sh
E="$PWD/.superpowers/sdd/2026-09-25-test-harness-phase-four"
WHEEL=$(< "$E/generator-wheel.path")
python "$E/audit.py" final-local -- uv run --no-project --isolated \
  --with tox --with tox-uv tox --result-json "$E/final-local-result.json"
# Preserve/copy this batch's logs, XML and native evidence before the next command.
python "$E/audit.py" final-supplied -- uv run --no-project --isolated \
  --with tox --with tox-uv tox --installpkg "$WHEEL" \
  --result-json "$E/final-supplied-result.json"
# Preserve/copy this batch's logs, XML and native evidence before the next command.
python "$E/audit.py" final-parallel -- uv run --no-project --isolated \
  --with tox --with tox-uv tox -p 2 -e py310-pb213,py313-pb30 \
  --installpkg "$WHEEL" --result-json "$E/final-parallel-result.json"
```

Run these as separate recorded batches with actual preservation between them, not by pasting the comment-only boundaries without implementing preservation.

For each batch inspect real `tox list -d --no-desc` output and all corresponding JUnit files. Require the exact eleven names from the spec, both modes only for py313-pb30/py313-pb213, 26 native case/check IDs per full route, and no failures/errors/skips/unexpected deselection. Calculate the harness count from collected IDs and check per-profile totals. Compare executed logical case IDs with the actual catalog key set and oracle.

Inspect the builder evidence and logs for all eight unchanged native versions, runtime before/after equality, extension origin/hash, exact fixture Python payload plus one extension, supplied generator path, real isolated pytest invocation and grouped-mode extension reuse. For parallel checking verify disjoint invocation-owned paths and both result inventories; references/catalog/index must remain unchanged.

Write `$E/check_supplied_wheel.py` using only stdlib to check in every installed wheel environment and each of the 11 native supplied-route interpreters:

- Independently saved pre-run SHA equals current saved artifact bytes.
- Exactly 15 installed production files including `py.typed` equal the wheel and tracked source, with no extra production files; installed origin lies under that interpreter's prefix.
- `importlib.metadata.distribution("pybind11-stubgen").read_text("direct_url.json")` has the exact absolute wheel `as_uri()` URL, no query/fragment/remote authority; installed wheel is not an editable directory.
- `archive_info` is a dictionary. Empty is accepted because uv was observed to omit hashes. If `hashes` or legacy `hash` is present, validate every provided algorithm/digest against the artifact rather than ignoring malformed data; the independently saved SHA256 remains mandatory.
- Correlate actual successful exact-wheel install argv in retained tox logs/result records; no subsequent source replacement is permitted on the supplied route.

Implement the checker as follows; the command-log correlation remains an independent batch audit, since it cannot be inferred just from an installed package:

```python
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
import zipfile
import pybind11_stubgen

wheel = Path(sys.argv[1]).absolute()
saved = sys.argv[2]
assert len(saved) == 64 and all(c in "0123456789abcdef" for c in saved)
assert hashlib.sha256(wheel.read_bytes()).hexdigest() == saved, "artifact hash"
repo = Path(__file__).resolve().parents[3]
tracked = subprocess.check_output(
    ["git", "ls-files", "pybind11_stubgen"], cwd=repo, text=True
).splitlines()
expected = {name: (repo / name).read_bytes() for name in tracked}
assert len(expected) == 15 and "pybind11_stubgen/py.typed" in expected
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert len(names) == len(set(names)), "duplicate wheel entries"
    assert not any("build" in Path(name).parts for name in names), "dirty wheel"
    payload = {name: archive.read(name) for name in names
               if name.startswith("pybind11_stubgen/") and not name.endswith("/")}
assert payload == expected, "wheel production inventory/bytes"
prefix = Path(sys.prefix).resolve()
package = Path(pybind11_stubgen.__file__).resolve().parent
assert package.is_relative_to(prefix), "generator origin"
installed = {}
for path in package.rglob("*"):
    if path.is_file() and "__pycache__" not in path.relative_to(package).parts:
        assert path.resolve().is_relative_to(prefix), path
        installed["pybind11_stubgen/" + path.relative_to(package).as_posix()] = path.read_bytes()
assert installed == expected, "installed production inventory/bytes"
dist = importlib.metadata.distribution("pybind11-stubgen")
metadata = json.loads(dist.read_text("direct_url.json"))
assert metadata["url"] == wheel.as_uri(), "installed artifact URL/path"
url = urlsplit(metadata["url"])
assert url.scheme == "file" and not (url.netloc or url.query or url.fragment)
assert "dir_info" not in metadata, "not an archive installation"
info = metadata["archive_info"]
assert isinstance(info, dict)
if "hashes" in info:
    assert isinstance(info["hashes"], dict) and info["hashes"], "hash schema"
    for algorithm, digest in info["hashes"].items():
        assert isinstance(algorithm, str) and isinstance(digest, str)
        assert hashlib.new(algorithm, wheel.read_bytes()).hexdigest() == digest, "metadata hash"
if "hash" in info:
    assert isinstance(info["hash"], str)
    algorithm, separator, digest = info["hash"].partition("=")
    assert separator and algorithm and digest, "legacy hash schema"
    assert hashlib.new(algorithm, wheel.read_bytes()).hexdigest() == digest, "legacy hash"
print(json.dumps({"python": sys.executable, "wheel": str(wheel),
    "sha256": saved, "origin": str(package), "metadata": metadata,
    "production_files": sorted(installed)}, indent=2))
```

Unsupported/malformed hash algorithms fail rather than being ignored; known provided hashes are recomputed, while saved SHA256 is always required independently. Invoke this with each target environment's Python, using `-I`, and pass the original saved hash, not a freshly substituted value. Prove wrong saved digest and byte-identical alternate wheel path are rejected, then restore green. Set `STUBGEN_TEST_INSTALLED=1` when invoking pytest; the standalone checker also enforces origin directly.

For example, save the actual expanded names once before the full native batches and audit supplied installations before their environments are changed again:

```sh
E="$PWD/.superpowers/sdd/2026-09-25-test-harness-phase-four"
WHEEL=$(< "$E/generator-wheel.path")
SAVED_SHA=$(< "$E/generator-wheel.sha256")
uv run --no-project --isolated --with tox --with tox-uv \
  tox list -d --no-desc > "$E/final-native-envs.txt"
while IFS= read -r profile; do
  ".tox/$profile/bin/python" -I "$E/check_supplied_wheel.py" "$WHEEL" "$SAVED_SHA"
done < "$E/final-native-envs.txt"
```

Record each probe's stdout/status separately in the evidence driver; also run it in all four fresh wheel environments. Do not regenerate the saved SHA to make a negative control pass.

- [ ] **Step 5: Complete controls, preservation audit and final docs commit.**

Run final focused reader/editor negatives and restored greens, plus the disposable real native mismatch/retention control from Task 3. Updates and mutation controls operate only in disposable repositories/fixtures; the real migrated catalog/payloads never receive `--update-snapshots` during acceptance. All 61 migrated payloads and their effective case bytes must still match the oracle after every native batch.

Check protected paths against the preservation anchor:

```sh
git diff --exit-code 4c84bad -- pybind11_stubgen tests/demo-lib \
  tests/py-demo tests/build_native.py tests/native_support.py tests/native_matrix.py \
  tests/conftest.py .pre-commit-config.yaml
uv lock --check
uv run --no-sync pre-commit run --all-files
git diff --check
```

For allowed-file changes, independently compare pyproject excluding exactly the two added dev requirements; compare tox except those two dependency additions; compare CI except the compiler-free install step's name/requirements. All other sections, native pins, formatter config, generator metadata and publication policy must match the anchor. Review generic helper/process/normalization bodies against the anchor and require unchanged semantics; account explicitly for the permitted case/diagnostic glue and synthetic fixture adaptation.

Rerun affected acceptance after any fix. Request final cumulative review against the approved spec and preservation anchor; do not treat worker reports as independent controller verification. Record exact command/status/count/identity results, negative controls, preserved output locations, limits and any separate bugs in `$E/final-report.md`. No remote acceptance claim.

```sh
git add tests/README.md
git diff --cached --check
git commit -m "docs: document shared snapshots and copy-on-write updates"
git status --short
```

Verify the final tree is clean, runtime/reference changes remain exactly scoped, and tests cover the final implementation revision (a README-only final commit does not change the tested implementation). Preserve the branch, worktree, backup ref and ignored evidence.

## Spec coverage and completion boundary

| Spec requirement | Deliverable/evidence |
| --- | --- |
| Literal TOML mappings, complete schema/path/payload validation | Task 1 reader and negative tests |
| tomllib/tomli selection, lazy tomlkit and native-matrix imports | Tasks 1–2 subprocess import controls |
| Approved dev/test dependencies without runtime/native drift | Task 1 config/lock diff; Task 4 independent preservation audit |
| Case/kind/scope copy-on-write, reuse, no-op and presentation | Task 2 editor and byte/consumer tests |
| Publication ordering, leftovers, cleanup and stale edits | Task 2 low-level failure injection and phase-specific diagnostics |
| Catalog-protected diagnostics; unchanged process guards | Task 3 synthetic integration and real copied mismatch control |
| Exact 13-case bytes, 61 payload migration, no historical resurrection | Independent archived oracle and Task 3 mapping audit |
| All source/wheel/unit versions and both native routes | Task 4 twelve suites, two full matrices and artifact identity checks |
| Parallel read-only isolation and reference/index safety | Task 4 bounded parallel batch and per-command inventories |
| Docs, review evidence, separate bugs and local-only scope | Task 4 handoff |

Implementation ends here. Do not use this phase to fix production behavior, clean up unrelated generic helpers, redesign tox, change native pins, or run remote publication. The execution-method choice follows plan review; no implementation begins as part of writing this document.
