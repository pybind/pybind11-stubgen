# Testing

The native demo models a C++ library (`demo-lib`), its bindings
(`py-demo/bindings`), and a mixed Python/native package (`py-demo`).

Checks generate output in temporary directories and compare logical filenames
and bytes using `snapshot_cases.toml`, with shared payloads in `stubs/` and
`errors/`. Normal checks and artifact retention never modify these references
or stage files. Updating references is a separate, explicit operation.

## Prerequisites

Use Python 3.10 or newer for compiler-free tests. Native checks require Python
3.10–3.13 for the full matrix, uv, tox with tox-uv, and a C++17 compiler. Tox
installs pinned pybind11 distributions, CMake, scikit-build-core, Ninja,
cmeel/Eigen, NumPy, and SciPy. It no longer clones pybind11 or builds/installs
demo-lib separately. Normalization still uses the existing pinned Ruff tool.

```sh
uv python install 3.10 3.11 3.12 3.13
uv tool install tox --with tox-uv
```

## Harness self-tests, without a compiler

With pytest and the TOML test dependencies installed:

```sh
python -m pytest tests/test_snapshot_helpers.py
```

Or let uv supply test dependencies, without syncing the project's native dependencies:

```sh
env -u VIRTUAL_ENV uv run --no-project --isolated --python 3.10 \
  --with 'pytest>=8,<9' --with 'tomli>=2,<3; python_version < "3.11"' \
  --with 'tomlkit>=0.13,<1' python -m pytest tests/test_snapshot_helpers.py
```

## Compiler-free production tests

`tests/unit/` covers parser/signature and annotation behavior, class ordering,
printer output, writer paths/contents, and small pure-Python generation flows.
Its fixtures are independent of `demo`; no native installation or NumPy/SciPy
is needed. The following command tests source edits directly without syncing
the development dependency group:

```sh
env -u VIRTUAL_ENV uv run --no-project --isolated --python 3.10 \
  --with 'pytest>=8,<9' --with 'tomli>=2,<3; python_version < "3.11"' \
  --with 'tomlkit>=0.13,<1' python -m pytest tests/unit tests/test_snapshot_helpers.py
```

The unit suite also covers catalog reading and copy-on-write editing. Reads
use stdlib `tomllib` on Python 3.11+ and `tomli` on 3.10; only real catalog edits
import `tomlkit`. Read-only checks and no-op updates do not import the editor
library. Focused production tests that do not exercise catalog editing remain
possible with pytest alone, for example:

```sh
env -u VIRTUAL_ENV uv run --no-project --isolated --python 3.10 \
  --with 'pytest>=8,<9' python -m pytest tests/unit/test_writer.py
```

To test a non-editable installation on each supported matrix interpreter:

```sh
uv run --no-project --with tox --with tox-uv tox \
  -e py310-unit,py311-unit,py312-unit,py313-unit
```

The unit environments install with uv, run isolated Python, and verify the
actual pytest process imports the installed generator. The default tox list
runs 11 native build profiles covering 13 cases; unit environments are explicit.
CI adds a separate compiler-free wheel matrix while retaining native/gemmi jobs.

## Native checks

The default matrix has 11 native build profiles covering the same 13 cases.
For Python 3.13 with pybind11 2.13 or 3.0, both NumPy rendering modes share one
installed fixture. Other profiles use annotated arrays. The old `-naa` and
`-nutv` tox suffixes are replaced by a mode selection within the grouped profile.

```sh
tox -e py313-pb30
tox -e py313-pb30 -- -k demo_errors
tox -e py313-pb30 -- --numpy-format numpy-array-use-type-var
tox
tox -e py313-pb30 --installpkg dist/pybind11_stubgen-3.0.0-py3-none-any.whl
```

The supplied-wheel example assumes the current generator wheel has already
been built in `dist/`; use the actual filename when the project version changes.

Tox's selected pybind11/CMake and runtime dependency versions are authoritative
for native checks both locally and in CI. NumPy/SciPy are pinned to the observed
phase-two runtime versions; fixture installation cannot replace them. The root
development dependency group is not the native test environment.

The retained labels `v2.9`, `v2.11`, `v2.12`, `v2.13`, and `v3.0` select reference
compatibility series (including via `--pybind11-branch`). They no longer designate
floating Git inputs: tox installs exact pinned pybind11 distribution versions.

Local native tox installs a generator wheel. CI supplies its existing build
artifact through the same runner. Installed origins are checked inside pytest.
After a matching tox run, a single check can be repeated without rebuilding:

```sh
STUBGEN_TEST_INSTALLED=1 .tox/py313-pb30/bin/python -I -m pytest \
  tests/test_demo_stubs.py --pybind11-branch v3.0 \
  --numpy-format numpy-array-use-type-var
```

That direct rerun checks installed origins and snapshots but does not reconstruct
tox's dependency-pin environment. Rerun tox after generator/fixture changes or
to validate the configured pins and rebuild the fixture. Missing configuration
or a missing demo is an error, not a skipped test.

Each profile owns its build directories and diagnostics. Checks can use bounded
parallel tox execution after the isolation acceptance test; they do not require
pytest workers. Reference updates remain explicit and serial.

## Catalog and shared payloads

`snapshot_cases.toml` contains `format = 1` and an explicit table for every
complete case ID. Each case has exactly two tables, `stubs` and `errors`, mapping
quoted logical filenames to literal, case-sensitive payload paths relative to
the corresponding root. There are no patterns, fallback versions, overlays,
aliases, or implicit common entries. Missing cases and missing mapped files are
errors; extra unreferenced regular payloads are inert. Symlinks are rejected.

For example, a stub entry can map `"demo/_bindings/numpy.pyi"` to
`"demo/_bindings/numpy/py310-pb213-annotated.pyi"`. Labels such as `shared` or
`py310-pb213-annotated` describe payload origins, not selectors: the catalog alone
selects the bytes, and another case may reuse that payload without renaming it.
Sharing is within one kind and logical filename, not between unrelated outputs.

## Update references deliberately

```sh
tox -e py313-pb30 -- --numpy-format numpy-array-wrap-with-annotated --update-snapshots
git diff -- tests/snapshot_cases.toml tests/stubs tests/errors
```

Run updates serially, including across tox processes. Use `-k demo_stubs` or
`-k demo_errors` with the update option to select one kind of expectation.
Generation, exit-status, traceback, fatal-run, no-output, required
`demo/__init__.pyi`, and formatting assertions still apply before mutation.
A broken command cannot become a new expectation.

Reading may share payloads; updating is case-scoped copy-on-write. Only the
selected case/kind changes; other cases and the other kind keep their effective
bytes. Unchanged entries keep their mappings. Changed files reuse an already
referenced variant with identical bytes for that kind/logical filename (the
lexicographically first path if several match). Otherwise new payloads go under
`variants/<case-id>/<n>/` in the relevant root, using the first unused positive
number and the logical filenames. Existing payloads are never overwritten.

Full stub updates match the generated file set. Scoped error updates affect only
the selected logical filenames, including deletions. After publishing the new
catalog, cleanup removes only displaced payloads that no case still references;
it never sweeps unrelated leftovers. No-op updates preserve every catalog and
payload byte, without reserialization, renaming, deduplication, or cleanup.
Repeated serial updates can reuse variants published by earlier updates.

Reports identify the catalog, case/kind, logical changes, old/new physical
references, and created/reused/removed payloads. Review all three reference
locations above. Nothing is automatically staged or committed.

New payloads are written before atomic catalog replacement. A failure before
publication leaves the old mappings and previously referenced payloads intact,
but new unreferenced payloads or a temporary catalog may remain; diagnostics
identify their locations. A detected intervening catalog edit is preserved,
not rolled back. A cleanup failure after publication explicitly reports that
the new mapping is already published. Inspect the reported paths and catalog
before any manual recovery; there is no rollback promise or bulk cleanup command.

Updates are per test, not transactional across files or a run, and do not promise
power-loss durability or concurrent-writer support. If a later check fails,
earlier successful checks may already have updated their references. Always
review the diff; do not accept unexplained changes from a bulk regeneration.

To bootstrap a deliberately added supported case, declare both kind tables
explicitly (empty tables are valid expectations), then run validated updates:

```toml
[cases."python-3.13-pybind11-v3.0-numpy-array-wrap-with-annotated".stubs]

[cases."python-3.13-pybind11-v3.0-numpy-array-wrap-with-annotated".errors]
```

Use the new case's complete ID, not the already populated example ID above.
Unknown cases are never created implicitly, and invalid/missing mapped payloads
must be repaired rather than blessed by an update. Adding a catalog case does
not schedule it in tox: execution coverage remains a separate, deliberate tox
configuration change.

## Failures and artifacts

Failures show the configuration, case ID, kind, catalog/TOML entry, logical
filename and canonical payload path (or an explicit unmapped output), file-set
changes, content diffs, and process diagnostics. Each check uses a fresh temporary
output directory. Optional `--artifacts-dir PATH` retains failure output outside the
reference trees and catalog. Neither diagnostic workspaces nor artifact paths
may overlap those locations. Pytest diagnostics remain in the environment's
`tmp/pytest-artifacts/`, with distinct case/check/run directories.

Build/install logs and fixture provenance are under
`.tox/<profile>/tmp/native/run-*/`; tox command logs are under
`.tox/<profile>/log/`. The native JUnit report is `tmp/native.xml`. CI's failure
upload includes these scoped logs and reports, not entire virtual environments.

## Add a regression

For generic harness behavior, add a small synthetic test to
`test_snapshot_helpers.py`; catalog/editor contracts belong in
`tests/unit/test_snapshot_catalog.py` and `tests/unit/test_snapshot_updates.py`.
For compiler-free generator behavior, prefer a focused test in `tests/unit/`
with explicit expected models or text. Neither route requires a compiler.

When the regression requires real binding behavior, add or adjust the native
demo fixture, run a relevant native environment, inspect its failure, then
explicitly update that environment's expectations. Review only the intended
changes and run affected shared profiles and the compatibility matrix before
merging.

Test-infrastructure changes must not hide production bugs with changed
expectations, unexplained skips, or snapshot updates. Report bugs separately;
production fixes require a separate scope. The ordinary-Python positional-only
bug and dirty-tree generator packaging issue remain outside this migration.
