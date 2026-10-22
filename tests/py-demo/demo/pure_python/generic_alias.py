import typing

list_int_type: typing.TypeAlias = list[int]
dict_str_int_type: typing.TypeAlias = dict[str, int]
union_int_str_type: typing.TypeAlias = int | str
typing_union_int_str_type: typing.TypeAlias = typing.Union[int, str]
RecursiveDict: typing.TypeAlias = dict[str, "RecursiveDict"]


class Test:
    list_int_type: typing.TypeAlias = list[int]
    dict_str_int_type: typing.TypeAlias = dict[str, int]
    union_int_str_type: typing.TypeAlias = int | str
    typing_union_int_str_type: typing.TypeAlias = typing.Union[int, str]
    RecursiveDict: typing.TypeAlias = dict[str, "RecursiveDict"]
