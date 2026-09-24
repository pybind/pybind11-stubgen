[![pypi](https://img.shields.io/pypi/v/pybind11-stubgen.svg?logo=PyPI&logoColor=white)](https://pypi.org/project/pybind11-stubgen/)

About
-----

Static analysis tools and IDE usually struggle to understand python binary extensions.
`pybind11-stubgen` generates [stubs](https://peps.python.org/pep-0561/) for python extensions to make them less opaque.

While the CLI tool includes tweaks to target modules compiled specifically
with [pybind11](https://github.com/pybind/pybind11) but it should work well with modules built with other libraries.

```bash
# Install
pip install pybind11-stubgen

# Generate stubs for numpy
pybind11-stubgen numpy
```

Usage
-----

```
pybind11-stubgen [-h]
                 [-o OUTPUT_DIR]
                 [--root-suffix ROOT_SUFFIX]
                 [--ignore-invalid-expressions REGEX]
                 [--ignore-invalid-identifiers REGEX]
                 [--ignore-unresolved-names REGEX]
                 [--ignore-all-errors]
                 [--enum-class-locations REGEX:LOC]
                 [--numpy-array-wrap-with-annotated|
                  --numpy-array-use-type-var|
                  --numpy-array-remove-parameters]
                 [--print-invalid-expressions-as-is]
                 [--print-value-comments]
                 [--print-safe-value-reprs REGEX]
                 [--exit-code]
                 [--stub-extension EXT]
                 MODULE_NAME [MODULE_NAMES ...]
```

Contributing
------------

See [the testing guide](tests/README.md) for prerequisites, running checks,
updating reference snapshots, and adding regression fixtures. Normal test runs
do not update or stage reference files.

To enable repository hooks locally:

```sh
uv sync
uv run pre-commit install
```
