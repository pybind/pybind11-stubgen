cmake_minimum_required(VERSION 3.12)
project(PyDemo LANGUAGES CXX VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/../../demo-lib ${CMAKE_BINARY_DIR}/demo-lib-build)
find_package(pybind11 CONFIG REQUIRED)


file(GLOB_RECURSE BINDINGS_SOURCES
        ./src/**.cpp
        ./src/**.h
)

pybind11_add_module(_bindings ${BINDINGS_SOURCES})

target_include_directories(_bindings PRIVATE ./src)
target_link_libraries(_bindings PRIVATE Demo::demo)
