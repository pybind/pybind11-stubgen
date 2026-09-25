# Test harness phase two: compiler-free production tests

## Status and starting point

The scope, test structure, and execution/acceptance design below were approved
in conversation. This written specification is awaiting user review before an
implementation plan is written. No phase-two implementation is included here.

Build on `test-harness-phase-one` at `a306491`, including the uv tox installation
fix and the separately reviewed stderr-order corrections. Use the existing
isolated worktree; do not merge or publish phase one as a prerequisite.

Phase one's last recorded local verification passed all 13 native tox
configurations, 99 tests each. Remote CI and diagnostic artifact-upload
acceptance remain unverified. The user explicitly deferred those remote checks
and authorized proceeding with phase two; this is not a claim that remote
acceptance passed.

This implements phase two of the
[phase-one roadmap](2026-09-24-test-harness-phase-one-design.md#later-phase-roadmap).
It does not include the shared orchestration/build changes or snapshot
reorganization reserved for phases three and four.

## Goal

Add fast, focused tests of existing generator behavior that run without a native
demo installation or compiler. Failures should identify a parser, annotation,
class-ordering, printer, or writer contract rather than require interpreting a
large generated-tree diff.

Phase two is test-only: production behavior is preserved. Any newly discovered
production bugs are reported separately instead of being fixed or silently
accepted as new desired behavior.

## Scope and invariants

Allowed changes:

- New tests and narrowly scoped test support under `tests/unit/`.
- Explicit compiler-free environments in `tox.ini`.
- A compiler-free job matrix and its gating dependency in
  `.github/workflows/ci.yml`.
- Test documentation and the phase-two design/implementation-plan documents.

Preserve unchanged:

- All files under `pybind11_stubgen/`; no testability refactors or runtime fixes.
- Native source, build configuration, `tests/install-demo-module.sh`, and the
  existing mixed Python/native demo package, including its Python fixtures.
- All reference contents and aliases under `tests/stubs/` and `tests/errors/`.
- Existing snapshot comparison, update, normalization, and diagnostic behavior.
- The 13 native tox configurations, their default environment list, and native
  CI configurations. Keep their native execution serial locally.
- Existing gemmi CLI jobs and publication trigger/credentials.

Do not add a snapshot framework, coverage-percentage target, production
dependency, broad dependency upgrade, or third-party fixture dependency. No
push, pull request, remote workflow execution, or publication is part of this
work. Configuring a future CI job does not authorize executing it remotely.

## Chosen approach

Use focused production tests with small independent Python fixtures. Prefer
explicit model and output assertions, with a few small parser-to-printer-to-writer
smoke tests to establish that the pieces fit together.

Alternatives considered:

1. Extract the existing Python demo fixtures. This would reuse examples but
   risks changing module identities, native package layout, and snapshots.
2. Add only pure-Python end-to-end snapshots. This would provide broad coverage
   but retain coarse failures and unnecessary expectation-management overhead.

Neither alternative is needed for the first compiler-free production layer.

## Test organization and data flow

Use the following organization, with only small shared helpers where repeated
setup genuinely warrants them:

```text
tests/unit/
    conftest.py
    fixtures/                   # Small independent Python modules/packages.
    test_parser.py
    test_annotations.py
    test_class_ordering.py
    test_printer.py
    test_writer.py
    test_pipeline.py
```

Keep the test directories from introducing an import path that shadows an
installed generator in wheel tests. Fixture packages use distinctive names and
are used only by tests, not imported by production. Do not change distribution
package discovery in this phase: the existing installed distribution already
contains test files, so excluding them would be a separate packaging change.

The fixtures depend only on the standard library. They do not import `demo`,
its native bindings, NumPy, SciPy, or the existing `demo.pure_python` package:
importing that package initializes the native-dependent parent. Existing demo
fixtures remain untouched and continue to serve native integration coverage.

Use production parser construction via `arg_parser`, `CLIArgs`, and
`stub_parser_from_args` for composed behavior, with a fresh parser per test.
Small direct tests may target a relevant parsing or ordering helper, but do not
recreate the production mixin stack in test code or substitute mocked parsing
for the behavior being tested.

Tests follow these boundaries:

- Parser/annotation tests: explicit Python objects or signature strings to
  structured production models and expected diagnostics.
- Printer/order tests: explicitly constructed production models to exact output
  lines and dependency-respecting order.
- Writer tests: explicit models plus the real printer to temporary paths and
  exact file bytes.
- Pipeline tests: independent Python fixture modules through the real parser,
  printer, and writer to a small, explicitly asserted output tree.

Expected results are hand-specified, not generated by the implementation under
test. No formatter is needed to compare the printer's own output, and no
snapshot-update operation is introduced.

## Coverage contracts

### Parser

Cover ordinary inspectable Python signatures and pybind11-style docstring
signatures supplied as strings or Python test objects; no compiled function is
required for the latter.

Cases include argument annotations/defaults, positional-only and keyword-only
arguments, variadic arguments, overload structure/order, and malformed or
non-signature docstrings. Check model fields and documented fallback/diagnostic
behavior rather than only the number of returned functions. Add focused
module/class traversal coverage using independent Python fixtures where it
supports ordering and pipeline contracts.

### Annotations

Cover nested parameterized types, unions, literal values, and malformed
expressions. Assert structured annotations, preserving distinctions between
resolved types, values, and invalid expressions. Include relevant composed
normalization behavior without requiring NumPy/SciPy imports.

Exercise Python-version-specific behavior on the appropriate interpreter.
Version conditions must be explicit and explained by syntax/runtime support,
not broad skips that hide a broken fixture. Newer syntax must not prevent test
collection on Python 3.10; keep it in strings or suitably isolated fixtures.

### Class ordering

Cover base-before-derived ordering, class-body aliases and print-safe field
values that reference sibling classes, dotted local references, and independent
classes retaining stable input priority. Check irrelevant external/unsafe
references and duplicate dependency edges without changing sorting policy.

Include empty/singleton inputs, nested class scopes, and cyclic dependencies.
For cycles, assert the existing warning and deterministic fallback ordering;
do not redesign the fallback. A small printer/pipeline case must also exercise
ordering so that helper-only tests cannot miss broken integration.

### Printer

Construct minimal models to cover argument separators, annotations/defaults,
function/method/decorator rendering, representative property/class output,
imports, docstrings, and module structure. Verify invalid-expression rendering
and value-comment options with explicit expected output.

Prefer one clear contract per case rather than a large all-features fixture.
For small complete outputs, supplement exact text checks with a syntax parse
where valid on the current Python version; parsing alone is not an oracle for
correct output.

### Writer

Use `tmp_path` and the real printer to cover a standalone module, a package
including an empty package, nested submodules, explicit output subdirectories,
and both supported `.pyi`/`.py` extensions. Assert the exact file set, UTF-8
contents, and final newlines. Include the existing failure contract for invalid
output roots and propagation of write failures using portable setup.

Do not add output cleanup, transactional writes, path validation, or other new
writer guarantees. Tests cover current intended behavior only.

### Small pipeline checks

Use a few compact independent fixtures to connect parsing, finalization,
printing, and writing. Assert meaningful imports/signatures/order and exact
small output trees. Keep these checks in-process unless a specific process
boundary is necessary; native CLI coverage already exists.

## Isolation and error handling

Create fresh mutable models and parser instances per test. Use pytest temporary
directories for output. Any fixture manipulation of `sys.modules`, import paths,
logging, or environment must be scoped and restored, including failure paths.
Do not rely on execution order or another test's imports.

Expected invalid input is tested by asserting the relevant diagnostic and
fallback. Avoid global ignore-all-errors configuration or blanket log
suppression. Native configuration options are unnecessary for this suite, and
collecting/running it must not request the existing native demo fixtures.

When a new case reveals an unexpected production failure:

1. Reproduce it and distinguish a test-assumption error from a production bug.
2. Record the minimal input, expected/current result, affected versions, and
   relevant code location separately in the implementation report.
3. Do not change production or update native references to make it pass.
4. Do not silently replace a valid assertion with observed buggy output or
   introduce an unexplained skip/xfail. If it blocks an agreed contract, surface
   that boundary for a user decision before claiming acceptance.

## Local execution

Document the direct source-checkout command:

```sh
uv run --no-project --with 'pytest>=8,<9' python -m pytest \
  tests/unit tests/test_snapshot_helpers.py
```

This provides pytest without syncing the native-heavy development dependency
group. The suite needs only the standard library, pytest and its dependencies,
and the generator code. Running it must not build/install the demo, download a
formatter, or invoke a compiler.

Add explicit tox environments named `py310-unit`, `py311-unit`, `py312-unit`, and
`py313-unit`, invoked together with:

```sh
uv run --no-project --with tox --with tox-uv tox \
  -e py310-unit,py311-unit,py312-unit,py313-unit
```

Keep the default native `env_list` unchanged. Unit environments must override
inherited native setup, dependencies, environment settings, and commands; merely
changing the pytest selection is insufficient. Install the generator
non-editably using uv with the environment interpreter selected explicitly,
then run the same compiler-free selection against that installed package.
Do not require pip inside the tox environment.

Use isolated Python invocation and test import layout that keep the checkout
from shadowing the installation. Verify the generator import origin in the
actual pytest process for installed-package runs, not only in an unrelated
preflight process. The direct source command remains intentionally distinct
from installed-package verification.

## CI configuration

Add a separate compiler-free matrix for Python 3.10, 3.11, 3.12, and 3.13. Consume
the existing build job's wheel artifact. Install only that wheel and pytest
(with its dependencies) into a fresh uv environment, then run the compiler-free
selection with installed-origin enforcement. Do not use `uv sync` or install
the native development group in these jobs.

Preserve the existing native and gemmi jobs. Add the new job to the publication
job's dependency gate so future releases cannot bypass it; do not change the
publication condition or permissions. No remote jobs will be launched during
this phase. Report remote results as unverified, not inferred from local runs.

## Verification and acceptance

Implementation is ready for local acceptance when:

- The compiler-free suite and harness self-tests pass on all four Python
  versions via the explicit unit tox environments.
- A clean pytest-only source run succeeds without optional/native packages, and
  the documented fast command does not invoke native setup or formatting.
- Installed-package runs enforce import origin during pytest. Locally built
  wheel verification exercises the CI-style setup on Python 3.10–3.13 without
  syncing development dependencies. Fixture imports do not substitute for the
  installed generator or require the native demo.
- Tests cover all five focused areas plus small pipeline checks with explicit
  expectations. Review checks that assertions are discriminating, not merely
  successful execution or results recomputed by production helpers.
- All 13 existing native tox environments still pass unfiltered and serially.
  These checks leave reference bytes, alias targets, and the Git index unchanged.
- Production, native/demo sources, installation script, and snapshots have no
  changes from the phase-two base. Review configuration diffs for preserved
  native/gemmi coverage and untouched publication triggers.
- Lock checks and existing pre-commit hooks pass. No dependency update is planned.
- Any discovered bugs and verification limits are reported explicitly. Remote
  CI and actual artifact-upload validation remain deferred by user choice.

These are behavioral and isolation criteria, not a target test count or coverage
percentage. The implementation plan will break this design into reviewable,
subagent-sized tasks after the user approves this written specification.
