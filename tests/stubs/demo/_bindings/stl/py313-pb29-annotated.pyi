from __future__ import annotations

import typing

__all__: list[str] = [
    "std_array",
    "std_map",
    "std_optional",
    "std_variant",
    "std_vector",
]

def std_array(arg0: list[int[3]]) -> list[int[3]]: ...
def std_map() -> dict[int, complex]: ...
def std_optional(arg0: int | None) -> None: ...
def std_variant(arg0: int | float | tuple[int, int]) -> None: ...
def std_vector() -> list[tuple[int, float]]: ...
