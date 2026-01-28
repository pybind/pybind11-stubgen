import typing


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
