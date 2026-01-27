from __future__ import annotations

import collections.abc
import typing

__all__: list[str] = [
    "std_array",
    "std_map",
    "std_optional",
    "std_variant",
    "std_vector",
]

def std_array(
    arg0: typing.Annotated[collections.abc.Sequence[typing.SupportsInt], "FixedSize(3)"]
) -> typing.Annotated[list[int], "FixedSize(3)"]: ...
def std_map() -> dict[int, complex]: ...
def std_optional(arg0: typing.SupportsInt | None) -> None: ...
def std_variant(
    arg0: typing.SupportsInt
    | typing.SupportsFloat
    | tuple[typing.SupportsInt, typing.SupportsInt]
) -> None: ...
def std_vector() -> list[tuple[int, float]]: ...
