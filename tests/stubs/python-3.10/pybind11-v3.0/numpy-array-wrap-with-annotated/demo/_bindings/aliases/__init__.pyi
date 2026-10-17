from __future__ import annotations

import collections.abc
import typing

import demo._bindings.enum
import numpy
from demo._bindings.aliases.foreign_method_arg import Bar2 as foreign_type_alias
from demo._bindings.aliases.foreign_return import get_foo as foreign_class_alias
from numpy import random

from . import (
    foreign_arg,
    foreign_attr,
    foreign_class_member,
    foreign_method_arg,
    foreign_method_return,
    foreign_return,
    missing_self_arg,
)

__all__: list[str] = [
    "Color",
    "Dummy",
    "List",
    "Sequence",
    "foreign_arg",
    "foreign_attr",
    "foreign_class_alias",
    "foreign_class_member",
    "foreign_enum_default",
    "foreign_method_arg",
    "foreign_method_return",
    "foreign_return",
    "foreign_type_alias",
    "func",
    "get_list",
    "get_lists",
    "get_sequence",
    "get_sequences",
    "local_func_alias",
    "local_type_alias",
    "missing_self_arg",
    "random",
]

class Sequence:
    def __init__(self, arg0: typing.SupportsInt | typing.SupportsIndex) -> None: ...

class List:
    def __init__(self) -> None: ...

class Dummy:
    linalg = numpy.linalg

class Color:
    pass

def foreign_enum_default(
    color: typing.Any = demo._bindings.enum.ConsoleForegroundColor.Blue,
) -> None: ...
def func(arg0: typing.SupportsInt | typing.SupportsIndex) -> int: ...
def get_list(arg0: List) -> List: ...
def get_lists(arg0: collections.abc.Sequence[List]) -> list[List]: ...
def get_sequence(arg0: Sequence) -> Sequence: ...
def get_sequences(arg0: collections.abc.Sequence[Sequence]) -> list[Sequence]: ...

local_type_alias = Color
local_func_alias = func
