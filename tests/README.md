# Testing

The native demo models a C++ library (`demo-lib`), its bindings
(`py-demo/bindings`), and a mixed Python/native package (`py-demo`).

Checks generate output in temporary directories and compare it with `stubs/`
and `errors/`. They never modify references or stage files. Updating references
is a separate, explicit operation.

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

With pytest installed:

```sh
python -m pytest tests/test_snapshot_helpers.py
```

Or let uv supply only pytest, without syncing the project's native dependencies:

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest tests/test_snapshot_helpers.py
```

## Compiler-free production tests

`tests/unit/` covers parser/signature and annotation behavior, class ordering,
printer output, writer paths/contents, and small pure-Python generation flows.
Its fixtures are independent of `demo`; no native installation or NumPy/SciPy
is needed. The following command tests source edits directly without syncing
the development dependency group:

```sh
uv run --no-project --isolated --with 'pytest>=8,<9' python -m pytest \
  tests/unit tests/test_snapshot_helpers.py
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

## Update references deliberately

```sh
tox -e py313-pb30 -- --numpy-format numpy-array-wrap-with-annotated --update-snapshots
git diff -- tests/stubs tests/errors
```

Do not update shared references concurrently. Existing aliases and per-test,
nontransactional update semantics are unchanged.

Use `-k demo_stubs` or `-k demo_errors` with the update option to select one kind
of expectation. Generation, exit-status, no-output, and formatting assertions
still apply in update mode. A broken command cannot become a new expectation.

Updates report their canonical destination and changed paths. Some directories
are aliases (for example, Python 3.13 uses the Python 3.12 reference directory).
An update to shared expectations affects every profile using that directory;
review and recheck those profiles. Aliases are preserved, and unrelated profiles
are not rewritten. Nothing is automatically staged or committed.

Updates are per test, not transactional across a run. If a later check fails,
earlier successful checks may already have updated their references. Always
review the diff; do not accept unexplained changes from a bulk regeneration.

## Failures and artifacts

Failures show the configuration, resolved reference location, file-set changes,
content diffs, and process diagnostics. Each check uses a fresh temporary output
directory. Optional `--artifacts-dir PATH` retains failure output outside the
reference trees. Pytest diagnostics remain in the environment's
`tmp/pytest-artifacts/`, with distinct case/check/run directories.

Build/install logs and fixture provenance are under
`.tox/<profile>/tmp/native/run-*/`; tox command logs are under
`.tox/<profile>/log/`. The native JUnit report is `tmp/native.xml`. CI's failure
upload includes these scoped logs and reports, not entire virtual environments.

## Add a regression

For harness behavior, add a small synthetic test to `test_snapshot_helpers.py`.
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
