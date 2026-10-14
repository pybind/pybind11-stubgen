from collections.abc import Mapping
from pathlib import Path

from snapshot_helpers import NUMPY_FORMATS


def select_modes(explicit: str | None, defaults: str | None) -> tuple[str, ...]:
    modes = (explicit,) if explicit is not None else tuple((defaults or "").split())
    if not modes or any(mode not in NUMPY_FORMATS for mode in modes):
        raise ValueError(
            "Native tests require --numpy-format or valid STUBGEN_NUMPY_FORMATS"
        )
    if len(set(modes)) != len(modes):
        raise ValueError("Duplicate NumPy modes")
    return modes


def require_origin(name: str, origin: str | None, prefix: Path) -> Path:
    prefix = prefix.resolve()
    if origin is None or not Path(origin).resolve().is_relative_to(prefix):
        raise RuntimeError(f"{name} must be installed under {prefix}; found {origin}")
    return Path(origin).resolve()


def check_versions(expected: Mapping[str, str], actual: Mapping[str, str]) -> None:
    for name, version in expected.items():
        if actual.get(name) != version:
            raise RuntimeError(
                f"Dependency drift: {name}: expected {version}, found {actual.get(name)}"
            )


def runtime_pins(environ: Mapping[str, str]) -> dict[str, str]:
    result = {
        name: environ[key]
        for name, key in (
            ("numpy", "STUBGEN_NUMPY_VERSION"),
            ("scipy", "STUBGEN_SCIPY_VERSION"),
        )
        if key in environ
    }
    if len(result) == 1 or any(not version for version in result.values()):
        raise ValueError("Set both NumPy and SciPy pins, or neither for a direct rerun")
    return result
