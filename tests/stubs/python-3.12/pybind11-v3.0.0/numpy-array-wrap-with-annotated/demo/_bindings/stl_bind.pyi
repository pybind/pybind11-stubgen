from __future__ import annotations

import collections.abc
import typing

__all__: list[str] = [
    "MapStringComplex",
    "VectorPairStringDouble",
    "get_complex_map",
    "get_vector_of_pairs",
]

class MapStringComplex:
    def __bool__(self) -> bool:
        """
        Check whether the map is nonempty
        """
    @typing.overload
    def __contains__(self, arg0: str) -> bool: ...
    @typing.overload
    def __contains__(self, arg0: typing.Any) -> bool: ...
    def __delitem__(self, arg0: str) -> None: ...
    def __getitem__(self, arg0: str) -> complex: ...
    def __init__(self) -> None: ...
    def __iter__(self) -> collections.abc.Iterator[str]: ...
    def __len__(self) -> int: ...
    def __repr__(self) -> str:
        """
        Return the canonical string representation of this map.
        """
    def __setitem__(self, arg0: str, arg1: complex) -> None: ...
    def items(self) -> typing.ItemsView: ...
    def keys(self) -> typing.KeysView: ...
    def values(self) -> typing.ValuesView: ...

class VectorPairStringDouble:
    __hash__: typing.ClassVar[None] = None
    def __bool__(self) -> bool:
        """
        Check whether the list is nonempty
        """
    def __contains__(self, x: tuple[str, typing.SupportsFloat]) -> bool:
        """
        Return true the container contains ``x``
        """
    @typing.overload
    def __delitem__(self, arg0: typing.SupportsInt) -> None:
        """
        Delete the list elements at index ``i``
        """
    @typing.overload
    def __delitem__(self, arg0: slice) -> None:
        """
        Delete list elements using a slice object
        """
    def __eq__(self, arg0: VectorPairStringDouble) -> bool: ...
    @typing.overload
    def __getitem__(self, s: slice) -> VectorPairStringDouble:
        """
        Retrieve list elements using a slice object
        """
    @typing.overload
    def __getitem__(self, arg0: typing.SupportsInt) -> tuple[str, float]: ...
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: VectorPairStringDouble) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, arg0: collections.abc.Iterable) -> None: ...
    def __iter__(self) -> collections.abc.Iterator[tuple[str, float]]: ...
    def __len__(self) -> int: ...
    def __ne__(self, arg0: VectorPairStringDouble) -> bool: ...
    @typing.overload
    def __setitem__(
        self, arg0: typing.SupportsInt, arg1: tuple[str, typing.SupportsFloat]
    ) -> None: ...
    @typing.overload
    def __setitem__(self, arg0: slice, arg1: VectorPairStringDouble) -> None:
        """
        Assign list elements using a slice object
        """
    def append(self, x: tuple[str, typing.SupportsFloat]) -> None:
        """
        Add an item to the end of the list
        """
    def clear(self) -> None:
        """
        Clear the contents
        """
    def count(self, x: tuple[str, typing.SupportsFloat]) -> int:
        """
        Return the number of times ``x`` appears in the list
        """
    @typing.overload
    def extend(self, L: VectorPairStringDouble) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    @typing.overload
    def extend(self, L: collections.abc.Iterable) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    def insert(
        self, i: typing.SupportsInt, x: tuple[str, typing.SupportsFloat]
    ) -> None:
        """
        Insert an item at a given position.
        """
    @typing.overload
    def pop(self) -> tuple[str, float]:
        """
        Remove and return the last item
        """
    @typing.overload
    def pop(self, i: typing.SupportsInt) -> tuple[str, float]:
        """
        Remove and return the item at index ``i``
        """
    def remove(self, x: tuple[str, typing.SupportsFloat]) -> None:
        """
        Remove the first item from the list whose value is x. It is an error if there is no such item.
        """

def get_complex_map() -> MapStringComplex: ...
def get_vector_of_pairs() -> VectorPairStringDouble: ...
