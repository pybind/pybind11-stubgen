import typing


class Token:
    pass


class Expression:
    pass


def args_mix(
    a: int,
    b: float = 0.5,
    /,
    c: str = "",
    *args: int,
    x: int = 1,
    y=int,
    **kwargs: typing.Dict[int, str],
): ...


def nested_current_module_annotations(
    tokens: list[Token], expr: typing.Optional[Expression] = None
) -> dict[str, Expression]: ...
