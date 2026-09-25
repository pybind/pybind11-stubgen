# Test harness phase three: shared orchestration and native builds

## Status and starting point

The orchestration, fixture-build, and acceptance sections were approved in
conversation. This written specification awaits user review. The runtime
NumPy reconciliation described below was discovered while preparing the document
and is explicitly part of that review, not a silently approved dependency change.
No phase-three implementation is included here.

Continue on `test-harness-phase-one` in its existing isolated worktree. The
current baseline is `807e7e44a1536699faf0070978303f58caa45648`; earlier handoff
hashes predate rewritten history and are not this phase's preservation anchor.
Do not merge, push, or publish earlier phases as a prerequisite.

This implements phase three of the
[phase-one roadmap](2026-09-24-test-harness-phase-one-design.md#later-phase-roadmap).
The [phase-two test layer](2026-09-25-test-harness-phase-two-design.md) remains in
place. Fresh source runs during specification preparation passed all 155
compiler-free tests on Python 3.10 and 3.13. Earlier recorded acceptance includes
all four supported interpreters and all 13 native cases; repeat the native
baseline on the current revision before implementation changes its setup.

Remote CI, gemmi execution on GitHub, and actual diagnostic artifact-upload
acceptance remain deferred by user choice. Local evidence must not be described
as remote acceptance.

## Goal and chosen approach

Make local and CI native checks use the same configuration and commands. Build
one native fixture for each Python/pybind11 combination, then use it for all
configured NumPy rendering modes. Simplify fixture packaging without changing
the generator, demo behavior, or expectations.

Use tox as the shared driver and authoritative native execution configuration.
CI derives its native matrix from tox instead of maintaining a second list of
versions, dependency choices, installation commands, and pytest commands.
Replace the fixture's handwritten setuptools/CMake bridge with scikit-build-core
if the compatibility evaluation passes. Retain cmeel-provided Eigen.

Alternatives considered:

1. Keep 13 environments and share compiled wheels through a cache. This retains
   existing names but adds cache keys, invalidation, and concurrency concerns.
2. Introduce a standalone orchestration framework shared by tox and CI. This
   duplicates responsibilities tox already provides.

The user selected grouping the modes within 11 tox environments. Small helpers
may translate resolved tox configuration to CI JSON or prepare a fixture build;
they must not become an independent configuration system or environment manager.

## Scope and invariants

Allowed changes:

- Native environment definitions and package-install orchestration in `tox.ini`.
- Native matrix generation, invocation, and failure-artifact wiring in
  `.github/workflows/ci.yml`.
- Fixture build metadata under `tests/py-demo/`, removal of its custom `setup.py`,
  and narrowly necessary CMake integration/install rules.
- Replacement or removal of `tests/install-demo-module.sh` and small test-side
  build/configuration helpers that replace its remaining responsibilities.
- Test fixtures/options needed to parameterize native modes and enforce installed
  provenance; focused compiler-free tests of the new support code.
- Test documentation and this phase's specification and implementation plan.

Preserve:

- Every production file under `pybind11_stubgen/`.
- Native C++ fixture source/header contents and existing Python files under
  `tests/py-demo/demo/`, including module identities and exported behavior.
- Reference bytes and symlink aliases under `tests/stubs/` and `tests/errors/`.
- Snapshot comparison, normalization, update guards, process contracts,
  existing 300-second snapshot subprocess timeouts, and diagnostic retention.
- All 13 logical compatibility cases and both native checks for each case.
- The phase-two compiler-free coverage, four explicit unit environments, and
  their independence from native/optional dependencies and formatter downloads.
- Generator build backend/package discovery, the root development dependency
  group and lockfile, gemmi jobs, workflow triggers, and publication conditions
  and permissions. Native tests stop using the root development group; that
  group is not the new native dependency authority.

No production fixes, broad dependency upgrades, snapshot regeneration or
reorganization, new platform matrix, or persistent cross-environment native
wheel cache. No push, PR, remote workflow execution, or publication. Fixture
wheels are local test inputs, not a newly published distribution. Making a
standalone fixture sdist that includes sibling C++ sources is not a goal.

## Native environment and case model

Remove the NumPy suffix from native environment names. The default tox list
contains exactly these 11 build profiles:

- `py310-pb30`, `py311-pb30`, `py312-pb30`, `py313-pb30`.
- `py310-pb213`, `py311-pb213`, `py312-pb213`, `py313-pb213`.
- `py313-pb29`, `py313-pb211`, `py313-pb212`.

| Python | pybind11 series | Modes | Build profiles | Logical cases |
| --- | --- | --- | --- | --- |
| 3.10–3.12 | 2.13, 3.0 | Annotated | 6 | 6 |
| 3.13 | 2.13, 3.0 | Annotated, type-variable | 2 | 4 |
| 3.13 | 2.9, 2.11, 2.12 | Annotated | 3 | 3 |

The exact mode names remain `numpy-array-wrap-with-annotated` and
`numpy-array-use-type-var`. Keep the existing `v2.9`, `v2.11`, `v2.12`, `v2.13`,
and `v3.0` labels for reference selection. Those labels identify compatibility
series, not floating Git inputs after this migration.

Old native tox names need not remain as aliases; the user approved regrouping
and renaming. Document their replacements. The four `py310-unit` through
`py313-unit` environments remain explicitly selectable and outside the default
native list.

Tox configuration owns environment membership, interpreter selection, native
dependency pins, and default modes. Matrix-generation support consumes tox's
resolved configuration/default environment list rather than reimplementing
brace expansion or carrying another hard-coded matrix. Generated JSON contains
the environment name and interpreter information needed by CI. Reject malformed,
duplicate, or unsupported native profile data with an actionable error instead
of silently omitting it. Tests may have an independent explicit expected case
inventory: that is a regression oracle, not another execution configuration.

## Dependency policy and evaluation inputs

### pybind11 and CMake

The existing cached pybind11 checkouts are at the release tags below. All five
releases have published Python wheels containing their headers and CMake
configuration. Availability was checked during design; compatibility with the
new build route has not yet been demonstrated.

| Series label | pybind11 pin | CMake evaluation pin |
| --- | --- | --- |
| `v2.9` | `2.9.2` | `3.31.10` |
| `v2.11` | `2.11.2` | `3.28.3` |
| `v2.12` | `2.12.1` | `3.28.3` |
| `v2.13` | `2.13.6` | `4.2.3` |
| `v3.0` | `3.0.4` | `4.2.3` |

These CMake versions match the currently installed local tox tools. Choosing
3.31.10 for 2.9 deliberately reconciles the existing local 3.31-series setting
with CI's separate 3.28.3 choice; it must pass the same acceptance gate, not be
assumed interchangeable. Do not upgrade all families to one recent CMake merely
to simplify a table.

Install the pinned pybind11 distribution rather than cloning and installing
its CMake project. Select its CMake configuration explicitly and verify the
resolved version/location in build evidence, so an ambient installation cannot
silently supply different headers. Retain `cmeel==0.59.0` and
`cmeel-eigen==3.4.0.2`, with explicit discovery of that Eigen installation.

The initial new-backend/tool evaluation candidates are
`scikit-build-core==1.0.3` and `ninja==1.13.2`; their published Python requirements
permit every supported interpreter. These are newly needed explicit execution
pins, not a claim that the migration has been tested. Tox owns the execution
pins; fixture build metadata declares compatible backend requirements rather
than another interpreter/pybind11 version matrix.

### Runtime dependencies: reconcile declarations with actual tests

Inspection of all 13 existing environments found that their installed NumPy
versions do not satisfy the `numpy~=1.20` declaration in tox. The root lockfile
also records NumPy 1.26.4, whereas the native checks run with NumPy 2.x.

The existing installer runs `uv pip install --force-reinstall` on the fixture,
whose `setup.py` declares unbounded `install_requires=["numpy"]`. That second
installation is unconstrained by tox's original NumPy requirement. Retained tox
installation logs show NumPy being reinstalled at this stage. Therefore the
configured requirement alone is not a reliable description of native runtime
coverage; the mismatch is present before phase three.

The proposed policy is to pin the actual observed runtime versions, preserving
what the accepted native tests exercise rather than silently switching them to
NumPy 1.x or upgrading them further:

| Python | NumPy | SciPy |
| --- | --- | --- |
| 3.10 | `2.2.6` | `1.15.3` |
| 3.11 | `2.4.6` | `1.17.1` |
| 3.12–3.13 | `2.5.3` | `1.17.1` |

All existing environments for a given interpreter agree on these versions.
This NumPy declaration change requires the user's explicit written-spec review.
It changes declared native setup policy, not the observed runtime baseline.
Keep the current pytest and typing-extensions requirements; unrelated package
or root development-group changes are not included.

Install runtime dependencies through tox, then install the fixture without
resolving/reinstalling its dependencies. Verify the installed NumPy/SciPy
versions before and after fixture installation and test execution. A drift
check is required: matching snapshots alone must not hide another replacement.
Do not claim that matching top-level pins constitute a fully locked transitive
environment.

If any candidate cannot preserve the case inventory and existing expectations,
investigate and report the specific incompatibility. No silent fallback to a
floating branch, different dependency version, skipped case, or regenerated
reference is acceptable. Material design changes require user approval.

## Fixture build architecture

The current roles are distinct: cmeel supplies Eigen and its CMake prefix;
setuptools plus `tests/py-demo/setup.py` currently drive CMake and assemble the
fixture wheel. Replace the latter, not the former.

The new fixture path is:

1. Tox creates a profile-specific environment and installs its selected build
   tools, pybind11, Eigen provider, and runtime/test dependencies.
2. A small build invocation selects that interpreter and the installed
   dependency locations explicitly. It uses a build directory beneath that
   environment's temporary directory.
3. scikit-build-core configures/builds the existing bindings CMake project. Its
   existing `add_subdirectory` relationship builds `demo-lib` as an extension
   dependency. Remove the separate standalone demo-library build/install pass.
4. CMake install rules and backend wheel configuration package the existing
   `demo` Python files and native extension. Do not include the static library,
   Eigen headers, build trees, or unrelated fixture-development files.
5. Install the fixture non-editably into the same tox environment, without
   changing its preinstalled runtime dependencies.

Use the tox-provisioned build environment explicitly, without a second PEP 517
build-isolation environment resolving different pybind11/CMake/backend versions.
This is deliberate dependency control inside an isolated tox environment, not
an instruction to build against arbitrary system tools. Fixture build metadata
still declares its build backend requirements. Do not require pip inside tox.

Keep the `py-demo` distribution identity/version, the `demo` package/import
layout, extension identity, and NumPy runtime requirement. Limit CMake changes
to build integration, dependency selection, and installation: no C++ fixture
semantics or compiler-standard changes.

Separate native environments share no mutable CMake build or install tree.
Their two NumPy modes, where configured, reuse one installed extension without
an intervening build. No cross-environment compiled-wheel cache or locking
framework is introduced. Re-running tox must incorporate current fixture
sources, including the sibling demo-library headers/sources; frontend wheel
caching must not hide their changes. A repeat run may use correctly scoped
incremental compilation, but correctness does not depend on doing so.

Do not delete the source tree's shared `tests/py-demo/build` or old
`tmp/pybind11-*` directories as part of the new runner. They are no longer inputs.
Any cleanup is confined to the invoking environment's owned build paths. Do not
inherit ambient CMake search paths in a way that overrides the selected inputs.
Log the actual interpreter, tool versions, dependency locations, and build path.

## Pytest execution and installed provenance

Run one pytest session per native environment, parameterizing both native checks
across its selected modes. Keep the existing case-to-reference mapping and
comparison/update helpers. Both stubs and errors execute for all 13 logical
cases even though some error expectations are shared.

Use stable, mode-specific test IDs and the existing full case identity for
failure workspaces. Harness self-tests need run only once per environment, not
once per mode. Default execution must not stop after the first mode's ordinary
test failure; no shell-command sequencing that drops the second mode.

Retain `--pybind11-branch` for explicit reference-series selection. Retain
`--numpy-format` for single-mode debugging; a command-line selection overrides
the environment's default mode set rather than appending to it. Reject invalid
selections clearly. Plain compiler-free collection must not need native options,
import `demo`, or trigger dependency installation.

Installed-generator verification occurs inside the actual pytest process, not
only in a separate preflight interpreter. Preserve the phase-two source-testing
mode while sharing or extending its installed-origin enforcement for native
runs. Native fixtures also check that the imported demo/extension are installed
in the intended environment, not resolved from the fixture checkout or another
profile. Keep isolated Python invocation for generator subprocesses.

Local native tox builds and installs a generator wheel through tox's package
mechanism. CI supplies its already-built wheel through tox's `--installpkg`
interface. A supplied artifact must not be replaced by a checkout build or
editable install. Record the supplied wheel identity and inspect the resolved
installation path/commands as well as runtime provenance; site-packages origin
alone does not prove which artifact was installed.

## CI and local interfaces

The native CI matrix has 11 jobs, each selecting one tox environment from the
derived matrix. Bootstrap tox/tox-uv through the existing uv setup. Remove the
native job's separate CMake action, development-group sync, direct fixture
installer call, and independently maintained pytest command. Those choices now
come from the same tox environment used locally.

Continue downloading the generator wheel from the existing build job. Preserve
the native job's required publication gate, matrix failure independence, the
separate four-version compiler-free wheel job, gemmi jobs, and release controls.
Generating a matrix may add an output/step to an existing prerequisite job; it
must not compile fixtures or create a second native dependency matrix.

Failure artifact collection must find the new environment-scoped locations.
Retain tox command/build logs when failure occurs before pytest, as well as the
existing per-case pytest diagnostics. Do not upload whole virtual environments
or confuse build logs with snapshot differences. Missing pytest artifacts on an
early build failure do not make that build successful.

Document normal local use, a single grouped profile, filtering a native check,
a single NumPy mode, an installed-fixture rerun, and supplying a prebuilt generator
wheel. Update old environment names and explain the retained series labels.
Keep the compiler-free source/unit commands and their no-native-dependency
contract. Snapshot updates remain explicit, reviewed, and serial; concurrent
reference mutation is not supported even after builds become independent.

## Error handling and regression tests

Dependency resolution, configuration, compilation, installation, and pytest
failures propagate as nonzero results with their phase, command, and useful logs.
Do not catch an error and continue using an old installed fixture. Unknown matrix
entries and missing required interpreters/dependencies are errors, not skipped
coverage. Keep bounded build concurrency for local parallel verification.

Add focused compiler-free tests for support introduced by this phase, including:

- Matrix derivation and an independent exact inventory of 11 profiles/13 cases;
  rejection of invalid or duplicate profile data.
- Default mode selection, single-mode override, stable IDs, and execution of
  remaining modes after an ordinary failure.
- Profile-specific build/diagnostic paths and rejection of unsafe cleanup paths
  wherever cleanup support is introduced.
- Correct interpreter, dependency locations, and wheel-install arguments at
  process boundaries; nonzero results and diagnostic retention on failure.
- Installed-origin rejection, explicit source-mode behavior, and runtime
  dependency drift detection.

Use real support functions and temporary paths. Synthetic subprocesses or
process-local negative controls may test orchestration failures; do not replace
production parser/printer behavior with mocks or add text-only tests as a
substitute for actual tox/build execution. New support tests belong in the
compiler-free selection and require only pytest and the standard library beyond
the generator. Avoid additional package requirements merely to parse the matrix.

## Verification and local acceptance

Before implementation, capture the actual revision's current native baseline,
selected dependency versions, case inventory, reference-tree/alias fingerprints,
and Git index state. Run the existing 13 environments serially; a new baseline
failure is investigated rather than attributed to this migration without proof.

Then require all of the following on the implemented configuration:

1. **Compiler-free preservation:** source checks and installed unit/wheel runs on
   Python 3.10–3.13 pass, including the existing 155 tests and new support tests.
   Clean environments lack the demo, NumPy, SciPy, and native build tools where
   those are unnecessary. No formatter download or native setup occurs.
2. **Full native parity:** fresh profile environments build successfully and run
   the exact 13-case inventory across 11 profiles, with both native checks for
   every case and no skips/xfails/deselection masking missing coverage. Inspect
   collection/results, not only an aggregate test count.
3. **Actual fixture reuse:** evidence for each dual-mode environment shows one
   installed extension used by both modes and no intervening fixture build.
   The standalone demo-library build/install pass is gone.
4. **Isolation and freshness:** repeat native runs pass; a source-change probe in
   a disposable copy demonstrates that sibling fixture changes are rebuilt.
   Two distinct representative profiles also pass with bounded concurrency and
   disjoint build/diagnostic paths. Capture failures independently. This is not
   permission for parallel snapshot updates or an unbounded compiler load.
5. **Supplied-wheel route:** locally exercise the same tox external-wheel route
   CI will use across all 11 profiles. Verify artifact identity, installed
   imports, and the absence of a replacement generator source build. A wheel
   built from clean tracked sources avoids confusing the known dirty-build
   packaging observation with this migration's results.
6. **Dependencies and payload:** build evidence identifies the selected tools,
   pybind11 and Eigen locations/versions. Runtime pins remain unchanged through
   fixture installation and checks. Inspect fixture wheels for correct module
   placement and absence of incidental static libraries, headers, or build trees.
7. **Failure sensitivity:** negative controls establish wrong-origin rejection,
   dependency-drift detection, nonzero build/install/test propagation, surviving
   diagnostics, and continuation to the second mode after an ordinary failure.
   Restore the unmodified path and re-run green checks afterward.
8. **Preservation:** check-mode runs leave all reference bytes, symlink targets,
   and Git index entries unchanged. Production and fixture source invariants
   have empty diffs against the current baseline. Review the remaining changes
   against the explicit allowed scope, including unchanged release controls.
9. **Repository checks:** existing lock checks, applicable all-file pre-commit
   hooks, and whitespace checks pass. No reference updates or unrelated lockfile
   changes are accepted as a way to obtain a green result.

A normal-run performance observation may document reduced build work, but there
is no wall-clock target or coverage-percentage target. Do not count reduced
repetition of harness self-tests as lost native-case coverage or require old
aggregate totals to remain identical after grouping.

Keep the previously reported ordinary-Python positional-only parsing issue and
repeated dirty-tree generator packaging issue separate; neither is fixed by
this phase. If another production bug or dependency incompatibility appears,
record a minimal reproduction, expected/current behavior, affected inputs, and
verification limits. Stop for a scope decision if it blocks an agreed contract.

Only local acceptance is required here. Remote workflow execution, gemmi remote
acceptance, and actual artifact upload remain unverified until separately
authorized. After the user approves this written specification, prepare a
reviewable implementation plan; do not start implementation from this document's
conversation approvals alone.
