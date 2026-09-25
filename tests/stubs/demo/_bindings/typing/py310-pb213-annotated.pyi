from __future__ import annotations

import typing

import typing_extensions

__all__: list[str] = ["get_buffer", "get_sequence"]

def get_buffer(arg0: typing_extensions.Buffer) -> typing_extensions.Buffer: ...
def get_sequence(arg0: typing.Sequence) -> typing.Sequence: ...
