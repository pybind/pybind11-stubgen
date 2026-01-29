from __future__ import annotations

import collections.abc

__all__: list[str] = ["get_buffer", "get_sequence"]

def get_buffer(arg0: collections.abc.Buffer) -> collections.abc.Buffer: ...
def get_sequence(arg0: collections.abc.Sequence) -> collections.abc.Sequence: ...
