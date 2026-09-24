from __future__ import annotations

import collections.abc
import typing

__all__: list[str] = [
    "Foo",
    "U",
    "accept_annotated_callable",
    "accept_callable",
    "accept_frozenset",
    "accept_py_handle",
    "accept_py_object",
    "accept_set",
    "add",
    "default_custom_arg",
    "default_int_arg",
    "default_list_arg",
    "default_optional_arg",
    "func_w_anon_args",
    "func_w_named_pos_args",
    "generic",
    "mul",
    "nested_types",
    "pass_callback",
    "passthrough1",
    "passthrough2",
    "passthrough3",
    "passthrough_backwards",
    "pos_kw_only_mix",
    "pos_kw_only_variadic_mix",
]

class Foo:
    def __init__(self, arg0: typing.SupportsInt | typing.SupportsIndex) -> None: ...

def accept_annotated_callable(
    arg0: collections.abc.Callable[
        [
            typing.SupportsInt | typing.SupportsIndex,
            typing.SupportsInt | typing.SupportsIndex,
        ],
        int,
    ],
) -> typing.Any: ...
def accept_callable(arg0: collections.abc.Callable) -> typing.Any: ...
def accept_frozenset(arg0: frozenset) -> None: ...
def accept_py_handle(arg0: typing.Any) -> str: ...
def accept_py_object(arg0: typing.Any) -> str: ...
def accept_set(arg0: set) -> None: ...
def add(
    arg0: typing.SupportsInt | typing.SupportsIndex,
    arg1: typing.SupportsInt | typing.SupportsIndex,
) -> int: ...
def default_custom_arg(foo: Foo = Foo(5)) -> None: ...
def default_int_arg(n: typing.SupportsInt | typing.SupportsIndex = 5) -> None: ...
def default_list_arg(l: list = [1, 2, 6, 18]) -> None: ...
def default_optional_arg(
    n: typing.SupportsInt | typing.SupportsIndex | None = None,
) -> None: ...
def func_w_anon_args(
    arg0: typing.SupportsInt | typing.SupportsIndex,
    arg1: typing.SupportsInt | typing.SupportsIndex,
    arg2: typing.SupportsInt | typing.SupportsIndex,
) -> None: ...
def func_w_named_pos_args(
    x: typing.SupportsInt | typing.SupportsIndex,
    y: typing.SupportsInt | typing.SupportsIndex,
    z: typing.SupportsInt | typing.SupportsIndex,
) -> None: ...
def generic(*args, **kwargs) -> None: ...
@typing.overload
def mul(
    x: typing.SupportsInt | typing.SupportsIndex,
    y: typing.SupportsInt | typing.SupportsIndex,
) -> int:
    """
    Multiply x and y (int)
    """

@typing.overload
def mul(
    p: typing.SupportsFloat | typing.SupportsIndex,
    q: typing.SupportsFloat | typing.SupportsIndex,
) -> float:
    """
    Multiply p and q (double)
    """

def nested_types(arg0: collections.abc.Sequence[Foo] | Foo) -> list[Foo] | Foo: ...
def pass_callback(arg0: collections.abc.Callable[[Foo], Foo]) -> Foo: ...
def passthrough1(*args, **kwargs):
    """
    passthrough1[T](obj: T) -> T
    """

@typing.overload
def passthrough2() -> None:
    """
    2. passthrough2[T](obj: T) -> T
    """

@typing.overload
def passthrough3() -> tuple[None, None]:
    """
    2. passthrough3[T](obj: T) -> tuple[T, None]
    3. passthrough3[T1, T2](obj1: T1, obj2: T2) -> tuple[T1, T2]
    """

def passthrough_backwards(obj: U) -> U: ...
def pos_kw_only_mix(
    i: typing.SupportsInt | typing.SupportsIndex,
    /,
    j: typing.SupportsInt | typing.SupportsIndex,
    *,
    k: typing.SupportsInt | typing.SupportsIndex,
) -> tuple[int, int, int]: ...
def pos_kw_only_variadic_mix(
    i: typing.SupportsInt | typing.SupportsIndex,
    /,
    j: typing.SupportsInt | typing.SupportsIndex,
    *args,
    k: typing.SupportsInt | typing.SupportsIndex,
    **kwargs,
) -> tuple[int, int, int]: ...

U: typing.TypeVar  # value = ~U
