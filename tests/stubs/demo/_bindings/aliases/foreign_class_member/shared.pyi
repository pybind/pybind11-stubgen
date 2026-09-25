from __future__ import annotations

import typing

import demo._bindings.classes

__all__: list[str] = ["Bar1"]

class Bar1:
    foo: typing.ClassVar[
        demo._bindings.classes.Foo
    ]  # value = <demo._bindings.classes.Foo object>
