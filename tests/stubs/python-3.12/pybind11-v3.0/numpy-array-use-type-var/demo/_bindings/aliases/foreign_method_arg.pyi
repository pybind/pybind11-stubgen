from __future__ import annotations

import demo._bindings.classes

__all__: list[str] = ["Bar2"]

class Bar2:
    def set_foo(self, arg0: demo._bindings.classes.Foo) -> int: ...
