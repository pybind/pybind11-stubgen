from __future__ import annotations

import demo._bindings.aliases
import demo._bindings.classes

__all__: list[str] = ["get_foo", "get_sequence"]

def get_foo() -> demo._bindings.classes.Foo: ...
def get_sequence() -> demo._bindings.aliases.Sequence: ...
