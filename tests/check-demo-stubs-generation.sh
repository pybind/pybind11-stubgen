#!/bin/bash

set -e

resolve_path() {
  local path="$1"

  while [ -L "$path" ]; do
    path="$(readlink "$path")"
  done

  if [ -d "$path" ]; then
    (cd "$path" && pwd -P)
  else
    (cd "$(dirname "$path")" && echo "$(pwd -P)/$(basename "$path")")
  fi
}

function parse_args() {

  CLEAR='\033[0m'
  RED='\033[0;31m'

  function usage() {
    if [ -n "$1" ]; then
      echo -e "${RED}👉 $1${CLEAR}\n";
    fi
    echo "Usage: $0 --stubs-sub-dir STUBS_SUB_DIR [--numpy-array-wrap-with-annotated] [--numpy-array-use-type-var]"
    echo "  --stubs-sub-dir                         stubs output dir relative to this script directory"
    echo "  --numpy-array-wrap-with-annotated       use --numpy-array-wrap-with-annotated to generate numpy array stubs"
    echo "  --numpy-array-use-type-var              use --numpy-array-use-type-var to generate numpy array stubs"
    exit 1
  }

  # parse params
  while [[ "$#" > 0 ]]; do case $1 in
    --stubs-sub-dir) STUBS_SUB_DIR="$2";shift;shift;;
    --numpy-array-use-type-var) NUMPY_FORMAT="$1";shift;;
    --numpy-array-wrap-with-annotated) NUMPY_FORMAT="$1";shift;;
    *) usage "Unknown parameter passed: $1"; shift; shift;;
  esac; done

  # verify params
  if [ -z "$STUBS_SUB_DIR" ]; then usage "STUBS_SUB_DIR is not set"; fi;
  if [ -z "$NUMPY_FORMAT" ]; then usage "NUMPY_FORMAT is not set"; fi;

  TESTS_ROOT="$(resolve_path "$(dirname "$0")")"
  STUBS_DIR=$(resolve_path "${TESTS_ROOT}/${STUBS_SUB_DIR}")
}

remove_stubs() {
    rm -rf "${STUBS_DIR}/*" ;
}

get_ruff_version() {
  awk '
    $1 == "-" && $2 == "repo:" && $3 == "https://github.com/astral-sh/ruff-pre-commit" {
      found = 1
      next
    }
    found && $1 == "rev:" {
      sub(/^v/, "", $2)
      print $2
      exit
    }
  ' "${TESTS_ROOT}/../.pre-commit-config.yaml"
}

run_stubgen() {
  pybind11-stubgen \
      demo \
      --output-dir=${STUBS_DIR} \
      ${NUMPY_FORMAT} \
      --ignore-invalid-expressions="\(anonymous namespace\)::(Enum|Unbound)|<demo\._bindings\.flawed_bindings\..*" \
      --enum-class-locations="ConsoleForegroundColor:demo._bindings.enum" \
      --print-value-comments \
      --print-safe-value-reprs="Foo\(\d+\)" \
      --exit-code
}

format_stubs() {
  (
    cd "${STUBS_DIR}" ;
    PYTHON_TARGET=$(python -c "import sys; print(f'py{sys.version_info.major}{sys.version_info.minor}')")
    RUFF_VERSION=$(get_ruff_version)
    if [ -z "${RUFF_VERSION}" ]; then
      echo "Failed to resolve Ruff version from .pre-commit-config.yaml"
      exit 1
    fi
    uvx --from "ruff==${RUFF_VERSION}" ruff format --target-version "${PYTHON_TARGET}" .
    uvx --from "ruff==${RUFF_VERSION}" ruff check --select I,RUF022 --fix --target-version "${PYTHON_TARGET}" .
  )
}

check_stubs() {
  git add --all "${STUBS_DIR}" ;
  (
    set -o pipefail ;
    git diff --exit-code HEAD -- "${STUBS_DIR}" | tee "${STUBS_DIR}.patch" ;
  )
}

main () {
  parse_args "$@"
  remove_stubs
  run_stubgen
  format_stubs
  check_stubs
}

main "$@"
