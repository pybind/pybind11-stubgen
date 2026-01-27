from __future__ import annotations

import typing

__all__: list[str] = [
    "backslashes_should_be_escaped",
    "issue_51_catastrophic_regex",
    "issue_73_utf8_doc_chars",
]

def backslashes_should_be_escaped() -> None:
    """
    \\brief A brief description of this function.

    A detailed description of this function.

    Here's some reStructuredText: :math:`x = [x, y, \\theta]^T`
    """

def issue_51_catastrophic_regex(
    arg0: typing.SupportsInt, arg1: typing.SupportsInt
) -> None:
    """
    Use-case:
        issue_51(os.get_handle_inheritable, os.set_handle_inheritable)
    """

def issue_73_utf8_doc_chars() -> None:
    """
    Construct a Ramsete unicycle controller.

    Tuning parameter (b > 0 rad²/m²) for which larger values make

    convergence more aggressive like a proportional term.
    Tuning parameter (0 rad⁻¹ < zeta < 1 rad⁻¹) for which larger
    values provide more damping in response.
    """

_cleanup: typing.Any  # value = <capsule object>
