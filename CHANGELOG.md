Changelog
=========

Version 3.0.0 (Sep 24, 2026)
----------------------------
Maintainership has passed from @sizmailov to @ax3l, @skarndev, and @virtuald,
and the repository has been transferred to the pybind11 organization.
Many thanks to @sizmailov for creating pybind11-stubgen and maintaining it over the years!

Breaking changes:
- ❗️ Require Python 3.10 or newer; drop support for Python 3.7–3.9 (#284, #285) by @ax3l and @gentlegiantJGC
- ❗️ Disable `# value = ...` comments by default; use `--print-value-comments` to restore them (#251) by @dyollb and @ax3l

Changes:
- ✨ Support generating stubs for multiple modules in a single CLI invocation (#292) by @birgerbr
- ✨ Add basic support for PEP 695 function type parameters in docstring signatures on Python 3.12+;
  class type parameters, variadics, and constraints are not supported (#291) by @gentlegiantJGC
- ✨ Preserve docstrings for static properties exposed as fields, with Python 3.12+ and pybind11 2.10.1+ (#308) by @markuspi
- 🐛 Order classes by dependencies rather than alphabetically, so base classes and class-body references
  appear before their dependents, including nested classes (#238)
  by @ax3l, @juelg, @daltairwalter, @skarndev, and @sizmailov
- 🐛 Fix nested qualified names in pybind11 docstring signatures (#280) by @ax3l, @gentlegiantJGC, @sarlinpe, and @skarndev
- 🐛 Strip current-module prefixes from nested type annotations and correctly parse runtime generic annotations (#301) by @ax3l
- 🐛 Resolve hidden builtin types, such as `mappingproxy`, to their importable names in `types` (#278) by @skarndev and @ax3l
- 🐛 Filter internal members of pybind11 native enums (#303) by @ax3l
- 🐛 Avoid `RuntimeError: dictionary changed size during iteration` when attribute access modifies a class dictionary (#310) by @htruscott
- 🐛 Make ordering of aliased and non-aliased imports deterministic (#293) by @cjwatson
- 🐛 Remove unstable memory addresses from additional object representations, including `WeakKeyDictionary` (#295) by @ax3l
- 🐛 Remove leading newlines from docstrings to avoid extra blank lines in generated stubs (#274) by @gentlegiantJGC

Development:
- 🔧 Move package metadata from `setup.py` to `pyproject.toml` (#281) by @gentlegiantJGC
- 🔧 Add pybind11 3.0 test coverage and update expected stubs for pybind11 3.0.3 (#289, #296) by @gentlegiantJGC and @ax3l
- 🔧 Add local test-stub regeneration via tox and fix demo builds on Clang/macOS (#287) by @skarndev and @ax3l
- 🔧 Modernize CI and publishing, migrate development tooling to uv and Ruff, and automate pre-commit updates (#279, #283, #290, #307, #314)
  by @virtuald, @gentlegiantJGC, @skarndev, and @ax3l


Version 2.5.5 (Aug 10, 2025)
--------------------------
Changes:
- 🐛 Fix the type annotation for `__all__` (#261) by @sarlinpe
- 🐛 Handle boolean numpy arrays (#260) by @sarlinpe
- 🐛 Fix `qualname` prefix in pybind11 3.0.0 (#259) by @gentlegiantJGC

Version 2.5.4 (May 14, 2025)
--------------------------
Changes:
- ✨ Add `argv` to `main()` to simplify use as a library (#252) by @gentlegiantJGC
- 🐛 Improve package detection (#253) by @gentlegiantJGC

Version 2.5.3 (Feb 24, 2025)
--------------------------
Changes:
- ✨ Ignore technical dunder Python 3.13 fields (`__static_attributes__` and `__firstlineno__`): (#243) by @nim65s
- 🔧 CI: Drop Python 3.7, add Python 3.13 (#243) by @nim65s


Version 2.5.2 (Feb 24, 2025)
--------------------------
Yanked to CI failure, released as 2.5.3


Version 2.5.1 (Mar 26, 2024)
--------------------------
Changes:
- 🐛 Fixed: Missed numpy unsigned int types (#219) by @Yc7521


Version 2.5 (Mar 3, 2024)
--------------------------
Changes:
- 🐛 Fixed: Don't render pybind11 `KeysView`, `ValuesView`, `ItemsView` class definitions (#211)
- 🐛 Fixed: Escape backslashes in stub output (#208)


Version 2.4.2 (Nov 27, 2023)
--------------------------
Changes:
- 🔁 Revert #196 due to poor review


Version 2.4.1 (Nov 25, 2023)
--------------------------
Changes:
- ✨ Automatically replace invalid enum expressions with corresponding valid expression & import (#196)  contributed by @ringohoffman
- 🐛 Fixed: do not remove `self` parameter annotation when types do not match (#195) contributed by @ringohoffman


Version 2.4 (Nov 21, 2023)
--------------------------
Changes:
- ✨ Added `--numpy-array-use-type-var` flag which reformats the pybind11-generated `numpy.ndarray[numpy.float32[m, 1]]`
annotation as `numpy.ndarray[tuple[M, Literal[1]], numpy.dtype[numpy.float32]]` contributed by @ringohoffman (#188)


Version 2.3.7 (Nov 18, 2023)
--------------------------
Changes:
- 🐛 fix: Handle top-level list-like annotations as types (#183)


Version 2.3.6 (Oct 24, 2023)
--------------------------
Changes:
- 🐛 fix: Missing `py::dtype` translation (#179)


Version 2.3.5 (Oct 23, 2023)
--------------------------
Changes:
- 🐛 fix: Wrong import for lowercase `buffer` (#175), issue (#173)


Version 2.3.4 (Oct 23, 2023)
--------------------------
Changes:
- 🐛 fix: Misleading warning that referred to ignored errors (#171)


Version 2.3.3 (Oct 22, 2023)
--------------------------
Changes:
- 🐛 fix: The `typing.Annotated` does not exist in python < 3.9, use `typing_extensions` (#168)


Version 2.3.2 (Oct 21, 2023)
--------------------------
Changes:
- 🐛 fix: Missing function name in error message (#165)


Version 2.3.1 (Oct 21, 2023)
--------------------------
Changes:
- 🐛 fix: Crash on `None`-valued docstring of property getter (#161)


Version 2.3 (Sep 27, 2023)
--------------------------
Changes:
- 🐛 fix: Inconsistent `--enum-class-locations` behaviour (#158)


Version 2.2.2 (Sep 26, 2023)
--------------------------
Changes:
- 🐛 fix: Missing `-?` in eum representation regex


Version 2.2.1 (Sep 23, 2023)
--------------------------
Changes:
- 📝 Update `--print-invalid-expressions-as-is` description


Version 2.2 (Sep 20, 2023)
--------------------------
Changes:

- 🐛 Fix: Python literals as default arg rendered as `...` (#147)
- ✨ Add `--print-safe-value-reprs=REGEX` CLI option to override the print-safe flag
     of Value (for custom default value representations provided via `pybind11::arg_v()`)  (#147)
- ✨ Add `--enum-class-locations=REGEX:LOC` CLI option to rewrite enum values as valid
     Python expressions with correct imports. (#147)

⚠️ This release detects more invalid expressions in bindings code.
  Previously Enum-like representations (e.g. `<MyEnum.Zero: 0>`) were always treated
  as non-printable values and were rendered as `...`.
  The invalid expressions should be acknowledged by `--enum-class-locations` or `--ignore-invalid-expressions`.


Version 2.1 (Sep 6, 2023)
--------------------------
Changes:

- ✨ Add `--stub-extension` CLI option (#142)


Version 2.0.2 (Sep 4, 2023)
--------------------------
Changes:

- 🐛 Fix: missing `isinstance` check (#138)

Version 2.0.1 (Sep 2, 2023)
--------------------------
Changes:

- 🐛 Fix: missing subdirectories for top-level submodules (#136)


Version 2.0 (Sep 1, 2023)
--------------------------
Changes:

- 🐛 Explicitly set encoding of stubs to utf-8 (#133)
- 🐛 Fix value representation for collections with print-unsafe elements (#132)


Version 2.0.dev1 (Sep 1, 2023)
--------------------------
Changes:

- 🐛 Fix missing remap of `numpy.ndarray.flags` (#128)
- ✨ Process `scipy.sparse.*` types the same as `numpy.ndarray` with `--numpy-array-wrap-with-annotated` (#128)
- ✨ Support dynamic array size with `--numpy-array-wrap-with-annotated` (#128)
- ❗️ Renamed CLI argument `--numpy-array-wrap-with-annotated-fixed-size` to `--numpy-array-wrap-with-annotated` (#128)


Version 1.2 (Aug 31, 2023)
--------------------------
Changes:

- 🐛 Fix compatibility with Python 3.7..3.9 (#124)
- 🐛 Fix incorrect list of base classes (#123)
- ✨ Replace `typing` collections with builtin types (e.g. `typing.List` -> `list`) according
  to [PEP 585](https://peps.python.org/pep-0585/)  (#122)
- ✨ Add missing translations of pybind types: `function` -> `Callable`, `object`/`handle` -> `typing.Any` (#121)
- ✨ Support function-valued default arguments (#119)
- 🐛 Fix missing properties docstrings (#118)


Version 1.1 (Aug 30, 2023)
--------------------------
Changes:

- Added `--dry-run` CLI option to skip writing stubs stage (#114 )


Version 1.0-dev (Aug 29, 2023)
------------------------------
⚠️ Project was rewritten from scratch for `1.x`. This allowed me to address some long-standing issues, but I might
accidentally brake behaviour you relied on.

Changes:

- Updated CLI interface, some options were removed, please see `pybind11-stubgen --help` for details
- Replaced regex-based signature parsing with more robust procedure which enables to produce partially degraded
  signatures
- Added type parsing/replacing, including deeply annotated types
- Support implicit imports required for static analysis
- Add introspection of pure python functions
- Support python 3.10+ only (temporarily)
- Improved structure of test binary pybind module
