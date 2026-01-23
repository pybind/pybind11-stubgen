from __future__ import annotations

import typing

__all__: list[str] = [
    "Blue",
    "ConsoleForegroundColor",
    "Green",
    "Magenta",
    "None_",
    "Yellow",
    "accept_defaulted_enum",
]

class ConsoleForegroundColor:
    """
    Members:

      Green

      Yellow

      Blue

      Magenta

      None_
    """

    Blue: typing.ClassVar[
        ConsoleForegroundColor
    ]  # value = <ConsoleForegroundColor.Blue: 34>
    """
    Blue color
    """
    Green: typing.ClassVar[
        ConsoleForegroundColor
    ]  # value = <ConsoleForegroundColor.Green: 32>
    """
    Green color
    """
    Magenta: typing.ClassVar[
        ConsoleForegroundColor
    ]  # value = <ConsoleForegroundColor.Magenta: 35>
    """
    Magenta color
    """
    None_: typing.ClassVar[
        ConsoleForegroundColor
    ]  # value = <ConsoleForegroundColor.None_: -1>
    """
    No color
    """
    Yellow: typing.ClassVar[
        ConsoleForegroundColor
    ]  # value = <ConsoleForegroundColor.Yellow: 33>
    """
    Yellow color
    """
    __members__: typing.ClassVar[
        dict[str, ConsoleForegroundColor]
    ]  # value = {'Green': <ConsoleForegroundColor.Green: 32>, 'Yellow': <ConsoleForegroundColor.Yellow: 33>, 'Blue': <ConsoleForegroundColor.Blue: 34>, 'Magenta': <ConsoleForegroundColor.Magenta: 35>, 'None_': <ConsoleForegroundColor.None_: -1>}
    def __eq__(self, other: typing.Any) -> bool: ...
    def __getstate__(self) -> int: ...
    def __hash__(self) -> int: ...
    def __index__(self) -> int: ...
    def __init__(self, value: int) -> None: ...
    def __int__(self) -> int: ...
    def __ne__(self, other: typing.Any) -> bool: ...
    def __repr__(self) -> str: ...
    def __setstate__(self, state: int) -> None: ...
    def __str__(self) -> str: ...
    @property
    def name(self) -> str: ...
    @property
    def value(self) -> int: ...

def accept_defaulted_enum(
    color: ConsoleForegroundColor = ConsoleForegroundColor.None_,
) -> None: ...

Blue: ConsoleForegroundColor  # value = <ConsoleForegroundColor.Blue: 34>
Green: ConsoleForegroundColor  # value = <ConsoleForegroundColor.Green: 32>
Magenta: ConsoleForegroundColor  # value = <ConsoleForegroundColor.Magenta: 35>
None_: ConsoleForegroundColor  # value = <ConsoleForegroundColor.None_: -1>
Yellow: ConsoleForegroundColor  # value = <ConsoleForegroundColor.Yellow: 33>
