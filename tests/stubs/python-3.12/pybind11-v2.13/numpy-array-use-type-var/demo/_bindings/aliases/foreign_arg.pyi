from __future__ import annotations

import demo._bindings.aliases
import demo._bindings.classes

__all__: list[str] = ["set_foo", "set_sequence"]

def set_foo(arg0: demo._bindings.classes.Foo) -> int: ...
def set_sequence(arg0: demo._bindings.aliases.Sequence) -> None: ...
