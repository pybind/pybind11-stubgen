from __future__ import annotations

import sys as sys
import typing as typing

from demo.pure_python.functions_3_8_plus import args_mix
from demo.pure_python.functions_3_9_plus import generic_alias_annotation

__all__: list[str] = [
    "accept_frozenset",
    "args_mix",
    "builtin_function_as_default_arg",
    "function_as_default_arg",
    "generic_alias_annotation",
    "lambda_as_default_arg",
    "search",
    "static_method_as_default_arg",
    "sys",
    "typing",
]

class _Dummy:
    @staticmethod
    def foo(): ...

def accept_frozenset(arg: frozenset[int | float]) -> int | None: ...
def builtin_function_as_default_arg(func: type(len) = len): ...
def function_as_default_arg(func: type(search) = search): ...
def lambda_as_default_arg(callback=...): ...
def search(a: int, b: list[int]) -> int: ...
def static_method_as_default_arg(callback=_Dummy.foo): ...
