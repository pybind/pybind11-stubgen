from __future__ import annotations

import typing

__all__: list[str] = ["Dummy"]

class Dummy:
    @staticmethod
    def static_method(arg0: typing.SupportsInt) -> int: ...
    def regular_method(self, arg0: typing.SupportsInt) -> int: ...
