from __future__ import annotations

import typing

import numpy
import scipy.sparse

__all__: list[str] = [
    "accept_matrix_int",
    "accept_vector_float64",
    "dense_matrix_c",
    "dense_matrix_r",
    "fixed_mutator_a",
    "fixed_mutator_c",
    "fixed_mutator_r",
    "four_col_matrix_r",
    "four_row_matrix_r",
    "get_matrix_int",
    "get_vector_float64",
    "sparse_matrix_c",
    "sparse_matrix_r",
]
M = typing.TypeVar("M", bound=int)
N = typing.TypeVar("N", bound=int)

def accept_matrix_int(
    arg0: numpy.ndarray[
        tuple[typing.Literal[3], typing.Literal[3]], numpy.dtype[numpy.int32]
    ]
) -> None: ...
def accept_vector_float64(
    arg0: numpy.ndarray[
        tuple[typing.Literal[3], typing.Literal[1]], numpy.dtype[numpy.float64]
    ]
) -> None: ...
def dense_matrix_c(
    arg0: numpy.ndarray[tuple[M, N], numpy.dtype[numpy.float32]]
) -> numpy.ndarray[tuple[M, N], numpy.dtype[numpy.float32]]: ...
def dense_matrix_r(
    arg0: numpy.ndarray[tuple[M, N], numpy.dtype[numpy.float32]]
) -> numpy.ndarray[tuple[M, N], numpy.dtype[numpy.float32]]: ...
def fixed_mutator_a(
    arg0: numpy.ndarray[
        tuple[typing.Literal[5], typing.Literal[6]], numpy.dtype[numpy.float32]
    ]
) -> None: ...
def fixed_mutator_c(
    arg0: numpy.ndarray[
        tuple[typing.Literal[5], typing.Literal[6]], numpy.dtype[numpy.float32]
    ]
) -> None: ...
def fixed_mutator_r(
    arg0: numpy.ndarray[
        tuple[typing.Literal[5], typing.Literal[6]], numpy.dtype[numpy.float32]
    ]
) -> None: ...
def four_col_matrix_r(
    arg0: numpy.ndarray[tuple[M, typing.Literal[4]], numpy.dtype[numpy.float32]]
) -> numpy.ndarray[tuple[M, typing.Literal[4]], numpy.dtype[numpy.float32]]: ...
def four_row_matrix_r(
    arg0: numpy.ndarray[tuple[typing.Literal[4], N], numpy.dtype[numpy.float32]]
) -> numpy.ndarray[tuple[typing.Literal[4], N], numpy.dtype[numpy.float32]]: ...
def get_matrix_int() -> numpy.ndarray[
    tuple[typing.Literal[3], typing.Literal[3]], numpy.dtype[numpy.int32]
]: ...
def get_vector_float64() -> numpy.ndarray[
    tuple[typing.Literal[3], typing.Literal[1]], numpy.dtype[numpy.float64]
]: ...
def sparse_matrix_c(arg0: scipy.sparse.csc_matrix) -> scipy.sparse.csc_matrix: ...
def sparse_matrix_r(arg0: scipy.sparse.csr_matrix) -> scipy.sparse.csr_matrix: ...
