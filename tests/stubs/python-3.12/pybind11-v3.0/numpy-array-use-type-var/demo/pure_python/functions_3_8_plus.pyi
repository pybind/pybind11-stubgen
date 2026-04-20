from __future__ import annotations

import typing as typing

__all__: list[str] = [
    "Expression",
    "Token",
    "args_mix",
    "nested_current_module_annotations",
    "typing",
]

class Token:
    pass

class Expression:
    pass

def args_mix(
    a: int,
    b: float = 0.5,
    c: str = "",
    *args: int,
    x: int = 1,
    y=int,
    **kwargs: dict[int, str],
): ...
def nested_current_module_annotations(
    tokens: list[Token], expr: Expression | None = None
) -> dict[str, Expression]: ...
