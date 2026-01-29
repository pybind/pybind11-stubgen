from __future__ import annotations

__all__: list[str] = ["generic_alias_annotation"]

def generic_alias_annotation(a: list[tuple[int]], b: dict[int, str]) -> list[float]: ...
