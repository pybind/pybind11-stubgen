from __future__ import annotations

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
    def __iter__(self) -> typing.Iterator: ...
    def __len__(self) -> int: ...
    def __repr__(self) -> str:
        """
        Return the canonical string representation of this map.
        """
    def __setitem__(self, arg0: str, arg1: complex) -> None: ...
    def items(self) -> typing.ItemsView[MapStringComplex]: ...
    def keys(self) -> typing.KeysView[MapStringComplex]: ...
    def values(self) -> typing.ValuesView[MapStringComplex]: ...

class VectorPairStringDouble:
    __hash__: typing.ClassVar[None] = None
    def __bool__(self) -> bool:
        """
        Check whether the list is nonempty
        """
    def __contains__(self, x: tuple[str, float]) -> bool:
        """
        Return true the container contains ``x``
        """
    @typing.overload
    def __delitem__(self, arg0: int) -> None:
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
    def __getitem__(self, arg0: int) -> tuple[str, float]: ...
    @typing.overload
    def __init__(self) -> None: ...
    @typing.overload
    def __init__(self, arg0: VectorPairStringDouble) -> None:
        """
        Copy constructor
        """
    @typing.overload
    def __init__(self, arg0: typing.Iterable) -> None: ...
    def __iter__(self) -> typing.Iterator: ...
    def __len__(self) -> int: ...
    def __ne__(self, arg0: VectorPairStringDouble) -> bool: ...
    @typing.overload
    def __setitem__(self, arg0: int, arg1: tuple[str, float]) -> None: ...
    @typing.overload
    def __setitem__(self, arg0: slice, arg1: VectorPairStringDouble) -> None:
        """
        Assign list elements using a slice object
        """
    def append(self, x: tuple[str, float]) -> None:
        """
        Add an item to the end of the list
        """
    def clear(self) -> None:
        """
        Clear the contents
        """
    def count(self, x: tuple[str, float]) -> int:
        """
        Return the number of times ``x`` appears in the list
        """
    @typing.overload
    def extend(self, L: VectorPairStringDouble) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    @typing.overload
    def extend(self, L: typing.Iterable) -> None:
        """
        Extend the list by appending all the items in the given list
        """
    def insert(self, i: int, x: tuple[str, float]) -> None:
        """
        Insert an item at a given position.
        """
    @typing.overload
    def pop(self) -> tuple[str, float]:
        """
        Remove and return the last item
        """
    @typing.overload
    def pop(self, i: int) -> tuple[str, float]:
        """
        Remove and return the item at index ``i``
        """
    def remove(self, x: tuple[str, float]) -> None:
        """
        Remove the first item from the list whose value is x. It is an error if there is no such item.
        """

def get_complex_map() -> MapStringComplex: ...
def get_vector_of_pairs() -> VectorPairStringDouble: ...
