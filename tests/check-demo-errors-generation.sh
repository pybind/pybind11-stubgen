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

TESTS_ROOT="$(resolve_path "$(dirname "$0")")"
DEMO_ERRORS_FILE="${TESTS_ROOT}/demo.errors.stderr.txt"
STUBS_DIR="/tmp/out" # Stubs should never be actually written

remove_demo_errors() {
    rm -rf "${DEMO_ERRORS_FILE}";
}

check_error_messages() {
  (
    set -o pipefail ;
    git diff --exit-code HEAD -- "${DEMO_ERRORS_FILE}";
  )
}
run_stubgen() {
  (
    set +e ;
    pybind11-stubgen \
      demo \
      --output-dir=${STUBS_DIR} \
      --exit-code \
      2> "${DEMO_ERRORS_FILE}" \
    || exit 0
    ) || (
     echo "'pybind11-stubgen demo --exit-code' did not exit with code 1"
     exit 1
    )
}

remove_randomness_in_errors (){
  if sed --version >/dev/null 2>&1; then
    # GNU sed (Linux)
    sed -i 's/0x[0-9a-f]\+/0x1234abcd5678/gi' "$DEMO_ERRORS_FILE"
  else
    # BSD sed (macOS)
    sed -i '' 's/0x[0-9a-f]\+/0x1234abcd5678/gi' "$DEMO_ERRORS_FILE"
  fi
}

main () {
  remove_demo_errors
  run_stubgen
  remove_randomness_in_errors
  check_error_messages
}

main "$@"
