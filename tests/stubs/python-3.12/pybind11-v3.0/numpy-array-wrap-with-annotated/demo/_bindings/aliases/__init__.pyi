from __future__ import annotations

import typing

import numpy
from numpy import random

import demo._bindings.enum
from demo._bindings.aliases.foreign_method_arg import Bar2 as foreign_type_alias
from demo._bindings.aliases.foreign_return import get_foo as foreign_class_alias

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
    "local_func_alias",
    "local_type_alias",
    "missing_self_arg",
    "random",
]

class Color:
    pass

class Dummy:
    linalg = numpy.linalg

def foreign_enum_default(
    color: typing.Any = demo._bindings.enum.ConsoleForegroundColor.Blue,
) -> None: ...
def func(arg0: typing.SupportsInt) -> int: ...

local_func_alias = func
local_type_alias = Color
