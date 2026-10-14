cmake_minimum_required(VERSION 3.12)
project(PyDemo LANGUAGES CXX VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Eigen3 3.4.0 EXACT CONFIG REQUIRED)
add_subdirectory(${CMAKE_CURRENT_LIST_DIR}/../../demo-lib ${CMAKE_BINARY_DIR}/demo-lib-build)
if(NOT DEFINED STUBGEN_PYBIND11_VERSION)
    message(FATAL_ERROR "Build the fixture through tox to select pybind11 explicitly")
endif()
find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 ${STUBGEN_PYBIND11_VERSION} EXACT CONFIG REQUIRED)
message(STATUS "Fixture Python: ${Python_EXECUTABLE}")
message(STATUS "Fixture pybind11: ${pybind11_VERSION} at ${pybind11_DIR}")
message(STATUS "Fixture Eigen3: ${Eigen3_VERSION} at ${Eigen3_DIR}")


file(GLOB_RECURSE BINDINGS_SOURCES
        ./src/**.cpp
        ./src/**.h
)

pybind11_add_module(_bindings ${BINDINGS_SOURCES})

target_include_directories(_bindings PRIVATE ./src)
target_link_libraries(_bindings PRIVATE Demo::demo)

install(TARGETS _bindings
    LIBRARY DESTINATION demo COMPONENT python
    RUNTIME DESTINATION demo COMPONENT python
)
