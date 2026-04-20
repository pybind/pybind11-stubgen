from __future__ import annotations

import typing

__all__: list[str] = [
    "Enum",
    "Unbound",
    "accept_unbound_enum",
    "accept_unbound_enum_defaulted",
    "accept_unbound_type",
    "accept_unbound_type_defaulted",
    "get_unbound_type",
]

class Unbound:
    pass

class Enum:
    pass

def accept_unbound_enum(arg0: ...) -> int: ...
def accept_unbound_enum_defaulted(x: Enum = ...) -> int: ...
def accept_unbound_type(
    arg0: tuple[..., typing.SupportsInt | typing.SupportsIndex],
) -> int: ...
def accept_unbound_type_defaulted(x: Unbound = ...) -> int: ...
def get_unbound_type() -> ...: ...
