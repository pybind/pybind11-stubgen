[![pypi](https://img.shields.io/pypi/v/pybind11-stubgen.svg?logo=PyPI&logoColor=white)](https://pypi.org/project/pybind11-stubgen/)

About
----

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
                 [--print-safe-value-reprs REGEX]
                 [--exit-code]
                 [--stub-extension EXT]
                 MODULE_NAME
```

Contributing
-----
During development it may be necessary to update the reference stubs under `tests/stubs`.
This can be done locally via a convenience tox configuration.
All the Python interpreters that tests are run against need to be available in your environment.
For example, you can install them via uv as such:
```shell
uv python install 3.10 3.11 3.12 3.13
```
To regenerate the reference stubs run:
```shell
uv run tox
```

