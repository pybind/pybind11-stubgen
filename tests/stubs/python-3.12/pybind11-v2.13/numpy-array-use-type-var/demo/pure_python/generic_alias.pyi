from __future__ import annotations

import typing as typing

__all__: list[str] = [
    "RecursiveDict",
    "Test",
    "dict_str_int_type",
    "list_int_type",
    "typing",
    "typing_union_int_str_type",
    "union_int_str_type",
]

class Test:
    RecursiveDict: typing.TypeAlias = dict[str, RecursiveDict]
    dict_str_int_type: typing.TypeAlias = dict[str, int]
    list_int_type: typing.TypeAlias = list[int]
    typing_union_int_str_type: typing.TypeAlias = int | str
    union_int_str_type: typing.TypeAlias = int | str

RecursiveDict: typing.TypeAlias = dict[str, RecursiveDict]
dict_str_int_type: typing.TypeAlias = dict[str, int]
list_int_type: typing.TypeAlias = list[int]
typing_union_int_str_type: typing.TypeAlias = int | str
union_int_str_type: typing.TypeAlias = int | str
