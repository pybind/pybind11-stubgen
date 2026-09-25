__all__ = ["ADerived", "ZBase", "typed"]


class ZBase:
    pass


class ADerived(ZBase):
    pass


def typed(value: int, *, enabled: bool = True) -> str:
    """Convert."""
    return str(value)
