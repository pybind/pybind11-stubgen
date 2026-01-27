from __future__ import annotations

import typing

import numpy

__all__: list[str] = [
    "accept_ndarray_float64",
    "accept_ndarray_int",
    "get_ndarray_float64",
    "get_ndarray_int",
    "return_dtype",
]

def accept_ndarray_float64(
    arg0: typing.Annotated[numpy.typing.ArrayLike, numpy.float64]
) -> None: ...
def accept_ndarray_int(
    arg0: typing.Annotated[numpy.typing.ArrayLike, numpy.int32]
) -> None: ...
def get_ndarray_float64() -> numpy.typing.NDArray[numpy.float64]: ...
def get_ndarray_int() -> numpy.typing.NDArray[numpy.int32]: ...
def return_dtype() -> numpy.dtype[typing.Any]: ...
