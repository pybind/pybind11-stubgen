from __future__ import annotations

import datetime

import numpy
from numpy import random

__all__: list[str] = [
    "Dummy",
    "Foo",
    "add_day",
    "foolist",
    "foovar",
    "list_with_none",
    "none",
    "random",
    "t_10ms",
    "t_20ns",
    "t_30s",
]

class Dummy:
    linalg = numpy.linalg

class Foo:
    pass

def add_day(arg0: datetime.datetime) -> datetime.datetime: ...

foolist: list  # value = [<demo._bindings.values.Foo object>, <demo._bindings.values.Foo object>]
foovar: Foo  # value = <demo._bindings.values.Foo object>
list_with_none: list = [None, 2, {}]
none = None
t_10ms: datetime.timedelta  # value = datetime.timedelta(microseconds=10000)
t_20ns: datetime.timedelta  # value = datetime.timedelta(0)
t_30s: datetime.timedelta  # value = datetime.timedelta(seconds=30)
