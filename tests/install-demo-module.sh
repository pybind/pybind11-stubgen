#!/bin/bash

set -e

PYTHON_EXECUTABLE=$(python -c 'import sys; print(sys.executable)')

function parse_args() {

  CLEAR='\033[0m'
  RED='\033[0;31m'

  function usage() {
    if [ -n "$1" ]; then
      echo -e "${RED}👉 $1${CLEAR}\n";
    fi
    echo "Usage: $0 --pybind11-branch PYBIND11_BRANCH"
    echo "  --pybind11-branch     name of pybind11 branch"
    exit 1
  }

  # parse params
  while [[ "$#" > 0 ]]; do case $1 in
    --pybind11-branch) PYBIND11_BRANCH="$2"; shift;shift;;
    *) usage "Unknown parameter passed: $1"; shift; shift;;
  esac; done

  # verify params
  if [ -z "$PYBIND11_BRANCH" ]; then usage "PYBIND11_BRANCH is not set"; fi;

  TESTS_ROOT="$(readlink -m "$(dirname "$0")")"
  PROJECT_ROOT="${TESTS_ROOT}/.."
  TEMP_DIR="${PROJECT_ROOT}/tmp/pybind11-${PYBIND11_BRANCH}"
  INSTALL_PREFIX="${TEMP_DIR}/install"
  BUILD_ROOT="${TEMP_DIR}/build"
  EXTERNAL_DIR="${TEMP_DIR}/external"
}


clone_pybind11() {
  mkdir -p "${EXTERNAL_DIR}"
  if [ ! -d "${EXTERNAL_DIR}/pybind11" ]; then
    git clone \
        --depth 1 \
        --branch "${PYBIND11_BRANCH}" \
        --single-branch \
        https://github.com/pybind/pybind11.git \
        "${EXTERNAL_DIR}/pybind11"
  fi
}

install_pybind11() {
  export CMAKE_PREFIX_PATH="$(cmeel cmake)"
  cmake \
        -S "${EXTERNAL_DIR}/pybind11" \
        -B "${BUILD_ROOT}/pybind11"\
        -DPYTHON_EXECUTABLE=${PYTHON_EXECUTABLE}
  cmake --install "${BUILD_ROOT}/pybind11" \
        --prefix "${INSTALL_PREFIX}"
}

install_demo() {
  cmake \
    -S "${TESTS_ROOT}/demo-lib" \
    -B "${BUILD_ROOT}/demo" \
    -DCMAKE_CXX_STANDARD=17
  cmake --build "${BUILD_ROOT}/demo"
  cmake --install "${BUILD_ROOT}/demo" \
        --prefix "${INSTALL_PREFIX}"
}

install_pydemo() {
  (
    export CMAKE_PREFIX_PATH="$(readlink -m "${INSTALL_PREFIX}"):$(cmeel cmake)";
    export CMAKE_ARGS="-DCMAKE_CXX_STANDARD=17";
    pip install --force-reinstall "${TESTS_ROOT}/py-demo"
  )
}

main () {
  parse_args "$@"
  clone_pybind11
  install_pybind11
  install_demo
  install_pydemo
}

main "$@"
