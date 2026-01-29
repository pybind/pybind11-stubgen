from __future__ import annotations

import typing

import numpy
import numpy.typing
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

def accept_matrix_int(
    arg0: typing.Annotated[numpy.typing.ArrayLike, numpy.int32, "[3, 3]"],
) -> None: ...
def accept_vector_float64(
    arg0: typing.Annotated[numpy.typing.ArrayLike, numpy.float64, "[3, 1]"],
) -> None: ...
def dense_matrix_c(
    arg0: typing.Annotated[numpy.typing.ArrayLike, numpy.float32, "[m, n]"],
) -> typing.Annotated[numpy.typing.NDArray[numpy.float32], "[m, n]"]: ...
def dense_matrix_r(
    arg0: typing.Annotated[numpy.typing.ArrayLike, numpy.float32, "[m, n]"],
) -> typing.Annotated[numpy.typing.NDArray[numpy.float32], "[m, n]"]: ...
def fixed_mutator_a(
    arg0: typing.Annotated[
        numpy.typing.NDArray[numpy.float32], "[5, 6]", "flags.writeable"
    ],
) -> None: ...
def fixed_mutator_c(
    arg0: typing.Annotated[
        numpy.typing.NDArray[numpy.float32],
        "[5, 6]",
        "flags.writeable",
        "flags.f_contiguous",
    ],
) -> None: ...
def fixed_mutator_r(
    arg0: typing.Annotated[
        numpy.typing.NDArray[numpy.float32],
        "[5, 6]",
        "flags.writeable",
        "flags.c_contiguous",
    ],
) -> None: ...
def four_col_matrix_r(
    arg0: typing.Annotated[numpy.typing.ArrayLike, numpy.float32, "[m, 4]"],
) -> typing.Annotated[numpy.typing.NDArray[numpy.float32], "[m, 4]"]: ...
def four_row_matrix_r(
    arg0: typing.Annotated[numpy.typing.ArrayLike, numpy.float32, "[4, n]"],
) -> typing.Annotated[numpy.typing.NDArray[numpy.float32], "[4, n]"]: ...
def get_matrix_int() -> (
    typing.Annotated[numpy.typing.NDArray[numpy.int32], "[3, 3]"]
): ...
def get_vector_float64() -> (
    typing.Annotated[numpy.typing.NDArray[numpy.float64], "[3, 1]"]
): ...
def sparse_matrix_c(
    arg0: typing.Annotated[scipy.sparse.csc_matrix, numpy.float32],
) -> typing.Annotated[scipy.sparse.csc_matrix, numpy.float32]: ...
def sparse_matrix_r(
    arg0: typing.Annotated[scipy.sparse.csr_matrix, numpy.float32],
) -> typing.Annotated[scipy.sparse.csr_matrix, numpy.float32]: ...
