# Test harness phase four: shared snapshots and explicit variants

## Status and baseline

The user approved file-level sharing, an explicit TOML catalog, development/test
TOML dependencies, case-scoped copy-on-write updates, and the safety and
verification design below. The user has also approved this written specification.
No phase-four implementation is included here.

Continue on `test-harness-phase-one` in its existing worktree. At the user's
request it was rebased onto `prune-historical-snapshots` (`b651555`). The new
preservation anchor is **`4c84bad5dfb95b63980be8c629c3c6a2746829cb`**. All 32
harness commits replayed without conflicts; the resulting tree differs from
pre-rebase `e8fbf84` only by the pruning branch's 155 deletions. Every surviving
tracked blob/mode and all 13 active cases' effective expectations are unchanged.
The backup ref is `backup/test-harness-phase-one-before-prune-e8fbf84`.

Rebase evidence and old/new commit correspondence are retained under
`.superpowers/sdd/2026-09-25-test-harness-phase-four/`. Earlier specifications and
reports contain historical hashes; do not reinterpret them as this phase's
baseline. Do not restore pruned references or modify other worktrees.

Fresh rebased verification passed four isolated source suites of 192 tests on
Python 3.10–3.13 and the entire supplied-wheel native route: 11 profiles, 1,093
tests, 13 logical cases, and 26 native checks. Reference/index audits, hooks,
lock and whitespace checks passed. This is a baseline, not implementation
acceptance or evidence of remote CI execution.

This implements the [phase-one roadmap's snapshot organization phase](2026-09-24-test-harness-phase-one-design.md#phase-4-snapshot-organization),
building on [phase-three orchestration](2026-09-25-test-harness-phase-three-design.md).

## Goal and selected approach

Store each distinct expectation once per logical output filename, while making
all case-to-reference choices explicit and reviewable. Preserve exact effective
expectations, compatibility coverage, read-only checking, and guarded updates.
Do not introduce fallback, overlay, inheritance, or version-range selection.

The pruned baseline contains 317 tracked reference entries: 312 regular files
and five symlinks. There are 61 distinct contents, occupying 88,888 bytes rather
than 280,479 bytes of repeated payload. Each active case has 31 stub filenames;
18 filenames are identical across all cases and 13 have genuine variants.
There are nine distinct complete stub trees. The migration should result in
**59 stub payloads and two stderr payloads**, plus one catalog, not 13 copies of
a complete tree. These are migration targets, not permanent limits on future
regressions or variants.

Alternatives rejected:

- Whole-tree aliases leave most duplication within the distinct trees.
- File symlinks broaden the filesystem and update safety surface.
- JSON was rejected for the catalog in favor of TOML and comment-preserving
  editing.

The catalog describes expectations. Tox remains the execution and dependency
configuration authority; do not derive a second execution matrix from it.

## Scope and preservation

Allowed changes:

- New `tests/snapshot_cases.toml` and reorganized payloads under `tests/stubs/`
  and `tests/errors/`; remove obsolete physical copies and aliases.
- Focused catalog reading/comparison and editing helpers under `tests/`.
- The `DemoCase` reference-selection integration in `tests/snapshot_helpers.py`
  and narrowly necessary native test/diagnostic glue.
- Adapt layout-dependent synthetic integration fixtures and assertions; add
  compiler-free catalog/editor regression tests under `tests/unit/`.
- Development/test dependency declarations and their necessary lock entries;
  tox/CI provisioning of those dependencies, without orchestration changes.
- Test documentation, this specification, and its implementation plan.

Preserve:

- All production files under `pybind11_stubgen/`, the C++ fixture and its build
  configuration, and all existing demo Python source/module identities.
- Exact effective expected filenames and bytes for every active case, including
  stderr order. Deduplication is not regeneration or expectation correction.
- All 13 cases and both native checks per case; installed-origin/runtime guards,
  dual-mode reuse, build isolation, and both generator-wheel routes.
- Native dependency pins, root generator metadata/backend/package discovery,
  Ruff configuration/pin, normalization, and subprocess invocation semantics.
- Existing 300-second snapshot process timeouts and 600-second native build/
  installation timeouts, failure propagation, and diagnostic retention.
- Compiler-free production/support coverage without demo, NumPy/SciPy, native
  setup or formatter downloads. The approved TOML dependencies are the narrow
  exception to the previous pytest/stdlib-only test dependency boundary.
- Workflow triggers, matrix membership, gemmi jobs, artifact retention policy,
  publication conditions and permissions.

No new test/support `__init__.py` files, broad refactoring or dependency upgrades,
production fixes, additional platforms/interpreters, pruning beyond the already
rebased branch, or permanent migration/overlay framework. Keep ordinary-Python
positional-only behavior, dirty-tree generator packaging, and the previously
deferred permanent real-tox inventory gate separate. No push, PR, merge, release
tag, remote workflow run or publication is part of this work.

## Catalog and payload layout

Use **`tests/snapshot_cases.toml`**, with TOML 1.0-compatible syntax, a top-level
integer `format = 1`, and a `cases` table. Each case key is the existing complete
`DemoCase.id`, including runtime Python, pybind11 series and NumPy mode. Keep
existing diagnostic case IDs and pytest parameter IDs unchanged.

Every case contains exactly two tables, `stubs` and `errors`. Each table maps a
logical generated relative filename to a physical relative payload filename.
Stub values are relative to `tests/stubs/`; error values are relative to
`tests/errors/`. Keys and paths are literal, case-sensitive strings, not patterns.
Dots and slashes in logical filenames must be quoted in TOML.

This excerpt illustrates two entries per stub table; the actual catalog must
contain each case's entire expected file set, not just these entries:

```toml
format = 1

[cases."python-3.13-pybind11-v2.13-numpy-array-wrap-with-annotated".stubs]
"demo/pure_python/functions.pyi" = "demo/pure_python/functions/shared.pyi"
"demo/_bindings/numpy.pyi" = "demo/_bindings/numpy/py310-pb213-annotated.pyi"

[cases."python-3.13-pybind11-v2.13-numpy-array-wrap-with-annotated".errors]
"demo.errors.stderr.txt" = "pybind11-v2.9/demo.errors.stderr.txt"

[cases."python-3.13-pybind11-v2.13-numpy-array-use-type-var".stubs]
"demo/pure_python/functions.pyi" = "demo/pure_python/functions/shared.pyi"
"demo/_bindings/numpy.pyi" = "demo/_bindings/numpy/py313-pb213-type-var.pyi"

[cases."python-3.13-pybind11-v2.13-numpy-array-use-type-var".errors]
"demo.errors.stderr.txt" = "pybind11-v2.9/demo.errors.stderr.txt"
```

Use human-readable payload labels, not hashes. For initial stub migration, group
by logical filename and exact bytes. A universally shared file gets `shared`;
other groups use the lexicographically smallest full case ID in the group as
the representative. Render its label as `py<major><minor>-pb<series-without-dots>`
plus `-annotated` or `-type-var`, for example `py310-pb213-annotated`. Place these
under the logical filename's parent/stem with its original suffix, as illustrated.
Record the resulting inventory before migration. Keep the two existing canonical
stderr files and map all relevant cases directly to them.

Labels describe a payload's origin, not a selection rule. A reference can later
be reused by another case without renaming it. Sharing is within the same check
kind and logical output filename, not across unrelated files merely because
both happen to contain the same bytes. Reject a physical payload mapped to two
different logical filenames within its kind.

There are no default tables, implicit common files, includes, aliases or inherited
values. A missing case is an error; do not select a nearby Python or pybind11
version. A missing expected filename means the generated filename is unexpected,
not that lookup should search another directory. Empty kind tables are valid
explicit expectations, but native success still requires `demo/__init__.pyi`
and native error runs still require their established fatal-process contracts.
Unknown cases are never created implicitly by an update.

All migrated payloads are regular files. Retaining `tests/stubs/` preserves its
existing Ruff exclusion; do not change formatting policy or reformat payloads.

## Components and dependency direction

Keep the implementation small and test-side:

- `tests/snapshot_catalog.py`: read/validate TOML, select a case and check kind,
  resolve payloads, construct the existing logical `dict[str, bytes]` snapshot,
  and compare/report logical file-set and byte differences.
- `tests/snapshot_updates.py`: plan and perform a selected-case update, preserve
  TOML presentation, publish mappings, and perform narrowly scoped cleanup.
- `tests/snapshot_helpers.py`: retain generic filesystem, diff, process,
  normalization and diagnostic primitives; adapt the case model to identify the
  catalog instead of treating version directories as the native reference API.
- Native tests: keep generation and validation bodies intact apart from
  reference selection, catalog comparison/update calls, and diagnostic context.
- `tests/unit/test_snapshot_catalog.py` and
  `tests/unit/test_snapshot_updates.py`: focused synthetic behavior contracts.

Reuse the existing diff/diagnostic primitives rather than creating another
normalizer or subprocess runner. Generic direct-directory helpers may remain
for their existing self-tests; they must not become a legacy lookup fallback.
Adapt only layout-dependent synthetic integration tests to the new reference
model, preserving their failure/update intent.

Keep catalog imports lazy where needed so importing `BRANCHES` for the stdlib
native-matrix adapter does not acquire a TOML dependency. Catalog reads must not
import the editor. Do not cache catalog contents across native tests: explicit
serial updates in one pytest session must see the previous test's committed
mapping changes.

## Development and test dependencies

Add these requirements to the root development dependency group:

```toml
dev = [
    "tomli>=2,<3; python_version < '3.11'",
    "tomlkit>=0.13,<1",
]
```

This is an additive excerpt, not a replacement for existing dev requirements.
Use stdlib `tomllib` on Python >=3.11 and `tomli` on 3.10. Import `tomlkit` only
when a real catalog edit is needed; read-only checks and no-op updates must not
require it to be importable. Missing required tooling must produce an actionable
error, never a different parser/editor fallback or skipped test.

Declare the same test requirements in the native and explicit unit tox
environments: native self-tests exercise update behavior too. Update the CI
compiler-free wheel installation step and README isolated commands to supply
these requirements without syncing the native development group. Runtime
package requirements and the eight pinned native dependencies stay unchanged.

Update `uv.lock` without an upgrade operation. The current lock already records
`tomli` 2.4.0 transitively; adding its direct conditional requirement must not
be used to upgrade unrelated packages. Review the resolved `tomlkit` addition
and every other lock diff. These are test dependencies, not a new runtime extra.

Documentation probes using `tomlkit` 0.15.1 on Python 3.10, 3.11 and 3.13
validated the examples and comment-preserving value replacement with both LF
and CRLF line endings. These probes check the library choice, not the future
catalog updater's correctness.

## Validation and read-only comparison

Validate the complete catalog's structure and referenced payloads, not only the
selected case. Fail clearly on unsupported format, wrong types, unknown fields,
malformed/duplicate TOML keys, missing kind tables, missing files, nonregular
entries, conflicting logical file/ancestor paths, or ambiguous payload ownership.
The format value must be an integer, not a boolean accepted through Python's
integer subclass relationship.

Validate case identifiers as single safe path components. Validate logical and
physical filenames as nonempty canonical POSIX relative paths: reject absolute
paths, traversal, backslashes, NULs and noncanonical spellings. Physical paths
must stay within the correct payload root. Reject symlinks in the catalog path,
payload roots and anywhere beneath those roots, including unreferenced or
dangling links. Scan both payload trees for unsafe entry types, but use only
catalog-referenced files to construct expectations or find reusable variants.
Do not relax the existing rejection of symlinks in generated output. Resolve the
trusted repository location once; do not mistake an ordinary ancestor above that
location for a payload alias.

Read referenced files as bytes. Compare the exact logical filename set and
contents, using existing diff semantics. An extra pool file does not become an
expectation merely because it exists. Unreferenced regular files are not searched
for alternatives and are not automatically garbage-collected by reads; this
also permits diagnosing leftovers from an interrupted update. The migration
and successful-update tests separately verify the intended payload inventory.

Normal checks never alter the catalog, payloads or Git index. Invalid references
are errors even in update mode: do not silently recreate a missing mapped file
or bless a corrupted catalog from generated output.

## Explicit case-scoped updates

Retain `--update-snapshots` and existing mode/check selection. An update selects
one case and one kind; the other kind and every other case retain exactly their
previous effective expectations. Preserve scoped error-file updates: an `only`
selection changes only the selected logical filenames and rejects actual output
outside that scope. Full stub updates match the entire generated stub file set.

All current generation, formatting, expected-exit, traceback, termination-marker,
no-output and required-`demo/__init__.pyi` checks run before reference mutation.
An invalid generator/formatter result can never become an expectation.

For a valid changed snapshot:

1. Load and validate the catalog and actual logical paths/bytes. Compute the
   complete proposed selected-table change in memory before writing anything.
2. Keep unchanged mappings. For each new/changed logical filename, reuse an
   already referenced variant with exactly the same bytes for that kind/name;
   choose the lexicographically smallest relative payload path if several match.
   Never rewrite an existing referenced payload, even if only the selected case
   uses it.
3. Otherwise allocate one new directory for this case/kind update under
   `variants/<case-id>/<n>/`, where `n` is the first unused positive integer,
   starting at 1. Put all newly needed payloads beneath it using their unchanged
   logical filenames. Skip occupied numbered entries, even empty directories;
   reject unsafe or non-directory namespace parents. At this stage choose paths
   without creating them; step 5 creates the directory/files exclusively. Never
   overwrite occupied paths, follow links or use hashes as filenames. Allocate
   nothing if every changed file can be reused.
4. Remove deleted logical filenames only from the selected table/scope. Preserve
   other tables and the comments/order/formatting of untouched TOML entries.
   Value replacements retain attached comments; deleting an entry may remove
   that entry's own inline comment, not unrelated comments. Use `tomlkit`, not
   regular-expression or whole-document regeneration.
5. Parse/validate the serialized TOML against the proposed mapping model before
   filesystem mutation. Create and write all new payloads, then validate the
   prospective catalog against the resulting physical files before publication.
6. Write a sibling temporary catalog. Immediately before atomic replacement,
   recheck that the on-disk catalog still matches the loaded bytes; abort rather
   than overwrite a detected intervening edit. Atomically replace the catalog
   file. This is the mapping publication point, not a transaction over all files
   or the entire test run. Do not claim crash/power-loss durability or support
   for concurrent writers.
7. After publication, delete only old payload files displaced by this update
   that are no longer referenced anywhere in the resulting catalog. Never sweep
   unrelated unreferenced files, touch another case's payload, or recursively
   delete a subtree. Empty-directory cleanup is limited to affected ancestors
   beneath a payload root; unexpected filesystem errors propagate.

No-op updates do not edit, reserialize, rename, deduplicate or clean anything;
all catalog and payload bytes remain identical. Do not automatically split
identical references just because update mode was requested. Repeated serial
updates producing the same bytes converge on existing referenced variants,
without requiring a separate deduplication command.

If writing a payload, temporary catalog or catalog replacement fails before
publication, the old catalog and all previously referenced payloads remain
unchanged by this operation. A detected external catalog edit must be left
intact, not rolled back. New unreferenced files or a temporary catalog may remain;
report their exact locations and the primary error rather than undertaking a
broad rollback/cleanup framework.
If cleanup fails after publication, fail explicitly and report that the new
mapping is already published, with cleanup paths. Do not claim rollback or
suppress the original error behind secondary diagnostic failures.

Updates are serial, including across tox processes; bounded parallel checking
remains supported. Detecting an intervening catalog edit is not a locking
protocol. Never stage or commit user expectations automatically.

## Diagnostics and pytest integration

Failure context identifies the unchanged case ID, check kind, catalog path and
TOML entry, logical filename, and canonical payload path where one exists.
Unexpected output is explicitly identified as having no mapping. Continue
showing logical missing/unexpected/changed-file diffs, not merely a diff of TOML
text. Retain generator/Ruff commands, cwd, statuses, stdout/stderr and artifacts.

Extend reference-location protection to cover the catalog as well as both
payload roots. Diagnostic workspaces, retained artifacts and diagnostic symlinks
must not overwrite any of these. Preserve existing context when diagnostic
writing or retention itself fails. Catalog/preflight errors before generation
must name the offending catalog/case/path; they need not invent subprocess logs
for a process that was never started.

Successful update reports list logical changes, old/new physical references,
created/reused/removed files, and catalog changes for the selected case/kind.
Replace the old advice that updating a shared directory changes all aliases:
copy-on-write deliberately prevents that propagation. No fake canonical
profile directory should be reported when selection is actually through TOML.

Keep in-process installed provenance and runtime version/extension checks.
Continue ordinary failures across grouped modes. Do not require a native import
or a formatter download for catalog/editor or synthetic integration self-tests.

## Mechanical migration and coverage

The supported inventory remains:

| Profiles | NumPy modes |
| --- | --- |
| `py310-pb30`, `py311-pb30`, `py312-pb30` | Annotated |
| `py313-pb30` | Annotated and type-var |
| `py310-pb213`, `py311-pb213`, `py312-pb213` | Annotated |
| `py313-pb213` | Annotated and type-var |
| `py313-pb29`, `py313-pb211`, `py313-pb212` | Annotated |

Mode strings remain `numpy-array-wrap-with-annotated` and
`numpy-array-use-type-var`. Each logical case retains stub and fatal-error tests.

Before moving payloads, record an independent baseline oracle from the rebased
legacy layout, including alias resolution, logical filenames and byte hashes.
Retain source bytes or access to the anchored Git objects for exact comparisons.
The migration uses those expectations, not fresh generator output. A one-off
migration/audit script belongs in this phase's ignored evidence workspace, not
as a permanent compatibility loader in the harness.

Create the catalog and unique regular payloads, integrate lookup, and remove the
old copies/aliases as one coordinated migration boundary. Compare every new
case/kind snapshot to the independent pre-migration oracle; assert exact
filenames and bytes, all 13 cases, no pruned-only data, and the 61-payload target.
Also verify every committed payload is referenced. Keep a mapping inventory so
reviewers can trace relocated files despite Git's rename heuristics.

Do not mistake a test using a literal case list for proof of actual tox execution.
Acceptance must inspect expanded tox profiles and real pytest/JUnit case IDs and
compare them with catalog coverage. This is not an additional production matrix
or a new permanent tox-config inspection subsystem.

## Tests and acceptance

Use failing behavioral tests before implementation, then focused and cumulative
runs. Where existing code already contains a guard, use a specific negative
control to prove the new test is sensitive rather than weakening the guard.

Compiler-free regression coverage includes:

- Literal mappings and complete logical file-set comparison; exact shared and
  variant bytes, unknown cases, invalid schema/paths, duplicate keys, missing
  files, directory/file conflicts, and symlink escapes.
- Read-only catalog/payload/index preservation; no editor import during reads
  or no-op updates; native-matrix import remains stdlib-only.
- Copy-on-write with two or more consumers, stable unaffected case/kind data,
  reuse of a matching referenced variant, deterministic collision handling,
  additions/removals, scoped updates, and no unrelated garbage collection.
- TOML comments/order and untouched formatting, no-op byte identity, repeated
  serial updates observing fresh mappings, and removal of only newly orphaned
  old payloads.
- Failures during payload creation/write, temporary catalog write, replacement
  and post-publication cleanup; rejection of an intervening catalog edit;
  unchanged old references before publication and accurate post-publication
  diagnostics, including secondary log/retention errors.
- Existing generator/formatter failure, empty-output, traceback and fatal-run
  update guards using synthetic native-test invocations, not new expectations.

Final local acceptance:

1. Fresh source and clean installed-wheel suites plus explicit unit tox suites
   on Python 3.10–3.13. Record exact collection/pass counts; preserve prior test
   intent and add the catalog/editor contracts, with no skips or xfails masking
   failures. Confirm compiler-free optional/native-module absence and actual
   pytest installed-origin enforcement, including wrong-origin red/green.
2. All 11 native profiles / 13 cases through both local generator-wheel and
   supplied-clean-wheel routes. Verify both native checks per case, no unexpected
   skips/deselection, unchanged pins/installed provenance, and dual-mode reuse.
   Build the supplied artifact from a clean archive, not the dirty checkout.
3. Preserve supplied artifact identity using the phase-three established checks:
   independently saved pre-run hash, exact installed file URL, unchanged wheel,
   exact installed production inventory/bytes and successful install commands;
   validate metadata hashes when present, without requiring uv's absent field.
4. Two-profile bounded parallel check with no updates; catalog/payload/index
   inventories unchanged. Test update behavior and injected failures only in
   disposable fixtures/copies, not by regenerating real references.
5. Audit catalog/payload bytes and symlinks plus Git index within every native
   batch. Separately prove migrated effective expectations against the baseline
   oracle and protected production/fixture/config paths against `4c84bad`.
6. `uv lock --check`, all-files hooks and whitespace checks. Review scoped
   dependency changes rather than requiring the intentionally edited lock and
   dev group to remain byte-identical. Verify unrelated CI/config sections and
   all eight native pins remain unchanged.

Each native profile still runs its harness self-tests in addition to two checks
per selected mode. If test counts change, account for the precise collected IDs;
do not accept only a summary or hardcode a historical total after adding tests.

## Documentation, evidence and handoff

Update `tests/README.md` with the catalog/payload layout, literal variant
selection, test dependency installation, serial copy-on-write update workflow,
addition/removal behavior, no-op guarantees, new failure context and limits after
partial failure. Explain how to deliberately add a new case: declare it and its
kind tables explicitly, then populate via validated updates; do not silently
extend coverage from a missing-case lookup. Keep direct installed reruns and
the distinction between compatibility labels and pinned distributions.

Use only this phase's ignored evidence workspace for new scripts/reports/logs.
Retain previous phase evidence and preserve tox tmp/log trees before commands
reset them. The rebase baseline currently leaves approximately 13 GiB free;
check space before disk-heavy acceptance and ask before deleting retained data.
Record per-task changes, review findings, exact commands, failures and restored
greens. Keep the branch/worktree in place after completion.

Remote CI, gemmi execution on GitHub, actual artifact uploads and publication
remain unverified unless separately authorized and executed. A local green
matrix and YAML checks do not establish remote acceptance. Report newly exposed
bugs separately, without silent pin changes, stderr sorting, weakened assertions
or blanket snapshot updates.
