# Testing

The native demo models a C++ library (`demo-lib`), its bindings
(`py-demo/bindings`), and a mixed Python/native package (`py-demo`).

Checks generate output in temporary directories and compare it with `stubs/`
and `errors/`. They never modify references or stage files. Updating references
is a separate, explicit operation.

## Prerequisites

Use Python 3.10 or newer. Native tests additionally need Git, a C++17 compiler,
uv, and tox with tox-uv. Tox installs the existing CMake/Eigen/Python dependencies.
Initial builds clone pybind11; normalization may download the pinned Ruff tool.

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
still runs the existing 13 native configurations; unit environments are explicit.
CI adds a separate compiler-free wheel matrix while retaining native/gemmi jobs.

## Native checks

```sh
tox -e py313-pb30-naa                 # One environment: Python 3.13, pybind11 3.0, annotated arrays.
tox -e py313-pb30-naa -- -k demo_errors  # One check in that environment.
tox                                  # Full configured matrix, serially.
```

Environment suffix `naa` means `numpy-array-wrap-with-annotated`; `nutv` means
`numpy-array-use-type-var`. Keep runs serial: the existing native build and some
reference directories are shared. Do not use `tox -p` or pytest workers yet.

After tox has installed the project and matching demo, a check can be rerun
without rebuilding:

```sh
.tox/py313-pb30-naa/bin/python -m pytest tests/test_demo_stubs.py \
  --pybind11-branch v3.0 --numpy-format numpy-array-wrap-with-annotated
```

That command tests the installed generator, not uninstalled source edits. Rerun
tox after changing generator or native fixture code. Missing configuration or a
missing demo is an error, not a skipped test.

## Update references deliberately

```sh
tox -e py313-pb30-naa -- --update-snapshots
git diff -- tests/stubs tests/errors
```

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
reference trees. Tox uses its environment temporary directory; CI uploads
`tmp/pytest-artifacts/` with separate configuration/check/run subdirectories.

## Add a regression

For harness behavior, add a small synthetic test to `test_snapshot_helpers.py`.
For compiler-free generator behavior, prefer a focused test in `tests/unit/`
with explicit expected models or text. Neither route requires a compiler.

When the regression requires real binding behavior, add or adjust the native
demo fixture, run a relevant native environment, inspect its failure, then
explicitly update that environment's expectations. Review only the intended
changes and run affected shared profiles and the compatibility matrix before
merging.

During test-only phase two, report newly discovered production bugs separately.
Do not hide them with changed expectations, unexplained skips, or snapshot
updates; production fixes require a separate scope.
