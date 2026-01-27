from __future__ import annotations

import sys
import typing

if sys.version_info[:2] >= (3, 8):
    from .functions_3_8_plus import args_mix

if sys.version_info[:2] >= (3, 9):
    from .functions_3_9_plus import generic_alias_annotation


class _Dummy:
    @staticmethod
    def foo():
        return 42


def search(a: int, b: list[int]) -> int: ...


def builtin_function_as_default_arg(func: type(len) = len): ...


def function_as_default_arg(func: type(search) = search): ...


def lambda_as_default_arg(callback=lambda val: 0): ...


def static_method_as_default_arg(callback=_Dummy.foo): ...


def accept_frozenset(arg: typing.FrozenSet[int | float]) -> int | None:
    pass
