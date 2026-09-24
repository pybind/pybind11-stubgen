# Phase 1: Non-mutating pytest test harness

Date: 2026-09-24

Status: Design approved in chat; written specification awaiting review.

Repository baseline: `5057f41` (`Prepare 3.0 release`).

## Goal

Make checking generated stubs a normal, non-mutating test operation, distinct
from deliberately updating reference outputs. Preserve the existing native demo,
compatibility coverage, and snapshot layout during this migration.

This document specifies phase 1. Later phases are a roadmap, not implementation
requirements for this change. No production stub-generation behavior is changed.

## Current behavior and motivation

`tox.ini` and `.github/workflows/ci.yml` select Python, pybind11, and NumPy-format
configurations. `tests/install-demo-module.sh` builds and installs the native
fixture. Two shell scripts then check generated stubs and error messages.

The stub checker writes into `tests/stubs`, formats the output with Ruff, stages
it with Git, and compares it against `HEAD`. The error checker attempts an
analogous stderr comparison, but its path resolver selects the wrong destination.
This mixes verification with reference updates and makes test results depend on
repository state.

The investigation also identified incorrect path handling and exit-status
checking in the error script, and a quoted wildcard that prevents the stub
script from clearing old output. The replacement must test these failure modes,
not reproduce the scripts literally.

## Scope and approach

Use ordinary pytest tests and a small shared snapshot helper. Do not add a
snapshot plugin or retain the shell checkers behind pytest wrappers.

- A plugin could reduce comparison code, but introduces another abstraction for
  the existing directory snapshots and aliases.
- Shell wrappers would minimize migration work but retain the unsafe behavior.
- A small Python helper makes path resolution, comparison, and update behavior
  explicit and independently testable.

### Included

- Non-mutating comparisons of generated stubs and error messages.
- Explicit, narrowly scoped snapshot updates.
- Subprocess status assertions and failure diagnostics.
- Compiler-free tests of the harness itself.
- Minimal pytest wiring in tox and CI, including failure artifacts.
- Contributor documentation for checking, updating, and adding regressions.

### Excluded

- Native build restructuring or dependency-version harmonization.
- Removing matrix configurations or combining NumPy modes into one build.
- Snapshot deduplication, renaming, or replacement of existing directory aliases.
- Broad unit coverage of production parser/printer code.
- Changes to the `gemmi` smoke-test job or production CLI options.
- New platform support or parallel local native builds.

## Components and responsibilities

| File | Responsibility |
| --- | --- |
| `tests/conftest.py` | Register test options; supply configuration, subprocess, temporary-directory, and artifact fixtures. |
| `tests/snapshot_helpers.py` | Resolve permitted snapshot destinations, compare output, normalize results, and perform explicit updates. Keep functions small and testable without the native demo. |
| `tests/test_snapshot_helpers.py` | Exercise comparison, update, path-safety, normalization, and subprocess-contract behavior using synthetic fixtures. |
| `tests/test_demo_stubs.py` | Generate successful demo stubs and compare the complete output tree. |
| `tests/test_demo_errors.py` | Assert the error exit code, normalized stderr, and absence of generated stubs. |
| `pyproject.toml`, `uv.lock`, `tox.ini` | Declare pytest and configure its invocation. |
| `.github/workflows/ci.yml` | Replace shell checks with pytest and upload diagnostics on failure. |
| `README.md`, `tests/README.md` | Explain the new workflows and fixture organization. |

Remove `tests/check-demo-stubs-generation.sh` and
`tests/check-demo-errors-generation.sh` once their callers have migrated. Do not
maintain two implementations of comparison or updating.

Keep `tests/install-demo-module.sh`, the demo sources, and their build
configuration unchanged. Test helpers must not import or build the native demo
when only harness self-tests are selected.

## Configuration and preserved coverage

One pytest integration invocation targets one configuration. The actual Python
interpreter supplies the Python version; callers supply these options:

- `--pybind11-branch`, using the existing values such as `v3.0`.
- `--numpy-format`, using `numpy-array-wrap-with-annotated` or
  `numpy-array-use-type-var`.
- `--update-snapshots`, absent by default.
- `--artifacts-dir`, an optional destination outside the reference trees.

Native tests require explicit configuration and an installed matching demo.
Missing configuration or an unavailable demo is an actionable failure, not a
silent skip or an automatic build. Harness self-tests need neither native
configuration nor the demo.

A supported profile uses a recognized branch and NumPy format and has reference
directories for the running, supported Python version. The following table
records existing CI/tox coverage, not an additional matrix to maintain in test
code. Preserve all 13 existing integration configurations:

| pybind11 branch | Python versions | NumPy format | Cases |
| --- | --- | --- | --- |
| `v3.0` | 3.10, 3.11, 3.12, 3.13 | annotated | 4 |
| `v3.0` | 3.13 | type variable | 1 |
| `v2.13` | 3.10, 3.11, 3.12, 3.13 | annotated | 4 |
| `v2.13` | 3.13 | type variable | 1 |
| `v2.12` | 3.13 | annotated | 1 |
| `v2.11` | 3.13 | annotated | 1 |
| `v2.9` | 3.13 | annotated | 1 |

Use the existing expectation paths:

- Stubs: `tests/stubs/python-X.Y/pybind11-BRANCH/NUMPY_FORMAT/`.
- Errors: `tests/errors/pybind11-BRANCH/demo.errors.stderr.txt`.

Resolve configured directory aliases deliberately, preserving them on disk.
Unsupported configurations and absent profile directories fail clearly; there
is no fallback to a nearby version. This phase does not add new profiles.

## Check-mode data flow

1. Resolve the selected reference path and validate its containment in the
   appropriate reference root.
2. Create a fresh temporary workspace for each integration test, separate from
   reference files and native build directories.
3. Run the installed generator in the pytest interpreter's environment. Use
   `sys.executable -I -m pybind11_stubgen` with the temporary working directory so
   CI exercises the installed wheel rather than importing the checkout through
   the working directory or `PYTHONPATH`. Do not use `uv run` inside the helper,
   where it could reinstall the project over the wheel being tested.
4. Capture the command, exit status, stdout, stderr, and generated files.
5. Validate the process contract, normalize applicable results, and compare
   against the working-tree reference files. Comparison never consults Git or
   `HEAD`.
6. On failure, report the configuration and relevant differences, and retain
   diagnostics in the temporary workspace or requested artifact directory.

The successful-generation test retains the existing CLI arguments, including
error-ignore expressions, enum locations, safe-value representations, NumPy
format, value comments, and `--exit-code`. It requires status `0`, then compares
both the complete relative file set and file contents.

The error test retains the existing error-producing invocation, requires status
`1`, compares normalized stderr, and verifies that its output location contains
no generated stubs. Before comparison or updating, require the generator's
`Terminating due to previous errors` diagnostic and reject Python tracebacks.
An absent executable, import traceback, status `0`, or any other unexpected
status must not be accepted as the intended error behavior, including in update
mode.

Comparisons must detect added, missing, changed, and unexpected files. Compare
normalized bytes; decode text for readable diffs. Tool caches and diagnostic
files belong outside the generated-output tree. Neither
passing nor failing checks may write to reference trees or the Git index.

## Normalization and diagnostics

Preserve the current normalization policy:

- Resolve the Ruff version from the existing pre-commit pin; do not introduce a
  second independent pin in phase 1.
- Apply Ruff formatting, then the `I,RUF022` fixes, with the running interpreter's
  target version.
- Make repository Ruff configuration explicit when running in temporary
  directories so changing the working directory does not silently change
  formatting. Keep Ruff's cache outside the compared output tree.
- Replace hexadecimal addresses in captured error messages with
  `0x1234abcd5678`, matching the existing normalization.
- Do not add broad sorting, annotation rewriting, or other normalization that
  could hide generator regressions.

A process-contract violation or formatting failure fails the test before
accepting output or updating its expectations. Include captured diagnostics even
if no output tree was produced. Apply a 300-second timeout to the generator and
each formatting subprocess, reporting the command and captured output on timeout.
This timeout does not change the native build's execution policy.

Failure reports include the logical configuration, resolved reference location,
missing/extra filenames, and unified content diffs. With `--artifacts-dir`, retain
available generated output, process diagnostics, and diffs under separate
configuration/test paths. Validate that this destination is outside both
reference roots before writing to it.

CI will use `tmp/pytest-artifacts/`, already covered by the repository's `tmp`
ignore rule, and upload diagnostics after either integration test fails. Nothing
is written alongside the checked-in snapshots as an artifact.

## Explicit update semantics

`--update-snapshots` changes only the behavior after an individual test has
successfully generated and validated its output. It does not relax status,
normalization, path-safety, or no-output assertions.

For each selected snapshot:

1. Resolve its existing profile directory under `tests/stubs` or `tests/errors`.
   Reject paths that escape the permitted root, including symlink escapes.
2. Report the logical profile and canonical destination. Explain in the docs
   that directory aliases share expectations with other logical profiles.
3. Validate the generated file tree and destination before modifying references.
   Reject unexpected symlinks within generated output or the selected snapshot
   contents; existing directory aliases in the profile path remain supported.
4. Copy validated content into that destination. For stub trees, remove stale
   reference files belonging to that selected tree so its file set exactly
   matches the generated tree. For errors, update only the selected stderr file.
5. Preserve directory aliases, unrelated profiles, and unrelated repository
   files. Never stage or commit anything.
6. Report changed paths so the developer can review the resulting Git diff.

Updates are per selected test, not a transaction across an entire pytest session
or tox matrix. A later failure does not undo updates made by an earlier successful
test. A test with failed generation or normalization must not update its own
references. Document this boundary rather than promising global rollback.

Run updates serially. Existing native build directories and aliased expectations
are shared; this phase does not make `tox -p` or pytest worker parallelism safe.
CI runs in check mode only.

## Local and CI integration

Add a Python-3.10-compatible pytest dependency to the existing development and
tox dependency declarations, and update `uv.lock`. Keeping these declarations in
two places is intentional for phase 1; consolidation belongs to phase 3.

Tox continues to build the demo with the existing script and install the project
as before. Replace shell checks with pytest, pass the branch and NumPy format
explicitly, and forward user test arguments. Remove the obsolete Python-tag
exchange file because pytest can read its own interpreter version. Change tox's
description from regeneration to checking.

CI keeps its existing matrix, CMake choices, native build steps, wheel
installation, and `gemmi` job. Run both new integration tests in one pytest
invocation without fail-fast behavior, so a stub mismatch does not suppress the
error check. Run harness self-tests as well, and upload failure artifacts after
pytest. Do not invoke a project-resolving wrapper after installing the wheel.

The contributor documentation will present these target workflows after
implementation (these are not commands supported by the current harness):

```sh
# Harness self-tests: requires pytest, but no C++ build or installed demo.
python -m pytest tests/test_snapshot_helpers.py

# Build and check one native configuration.
tox -e py313-pb30-naa

# Explicitly update that configuration, then review the changes.
tox -e py313-pb30-naa -- --update-snapshots
git diff -- tests/stubs tests/errors

# Check all configured environments, serially.
tox
```

Also document environment/tool installation, selecting an individual integration
test, rerunning pytest against an already installed demo, where failure artifacts
are stored, and how to add a regression fixture and update only its expectations.
The README should link to `tests/README.md` rather than duplicate the full guide.

## Verification and acceptance criteria

Harness tests use synthetic files and subprocess results, not the native demo.
They must establish:

- Identical output passes; changed, missing, and extra files fail with useful
  diagnostics, including filenames containing spaces and nested paths.
- Passing and failing checks preserve reference content and the Git index,
  including pre-existing developer changes.
- Explicit updates add, replace, and remove only the selected reference files;
  unrelated profiles and files remain unchanged.
- Alias chains resolve correctly, aliases survive updates, and escaping paths,
  unsupported profiles, and unexpected nested symlinks are rejected safely.
- Unexpected statuses, absent commands, tracebacks, timeouts, and formatting
  failures cannot be accepted by update mode; the error test also rejects
  generated stubs and missing fatal-diagnostic termination markers.
- Address normalization is narrow and deterministic, and normalization command
  failures retain useful diagnostics.
- Artifact collection cannot write into either reference root.
- Harness self-tests run with pytest alone, without native fixture setup.

Validate representative native configurations while developing the migration,
then exercise all 13 preserved configurations in CI before merging. Verify that
CI still tests the installed wheel and that the existing `gemmi` job remains
unchanged. Check snapshot content and index state before and after check-mode
runs, including a deliberately induced mismatch in an isolated test fixture.

Do not assume existing snapshots are correct merely because the old scripts
appeared to pass. The error checker could miss regressions and stale stub files
could survive cleanup. Investigate newly exposed differences individually. Any
necessary reference correction must be explained and reviewed separately from
the mechanical harness migration, not accepted by a blanket regeneration.

## Later-phase roadmap

### Phase 2: Compiler-free production tests

Add focused parser, annotation, class-ordering, printer, and writer tests.
Separate pure-Python fixtures from the package that imports native bindings.
Retain real pybind11 integration coverage.

### Phase 3: Shared orchestration and simpler native builds

Unify local/CI configuration and dependency choices. Run NumPy modes against a
shared compiled fixture. Remove the redundant standalone demo-library build,
isolate build directories by environment, and evaluate a standard build backend
and pinned pybind11 releases. Preserve installed-wheel coverage.

### Phase 4: Snapshot organization

Share identical expectations and use explicit variants only where outputs
genuinely differ. Preserve compatibility coverage and avoid a complex fallback
or overlay framework. Do this only after the new harness gives trustworthy,
non-mutating comparisons.

Each later phase requires its own scoped design and implementation plan.
