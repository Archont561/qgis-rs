"""
High-level Python wrappers around the Rust _core extension.

These provide a more Pythonic API while still running at native speed
because all heavy lifting is done in Rust.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

# Import from parent package without triggering circular import —
# __init__.py already tried _core and fell back to _fallback, so we
# import the symbols it exported.

try:
    from . import _core as core  # type: ignore
    from ._core import Project as RustProject  # type: ignore
    _HAS_CORE = True
except ImportError:
    from . import _fallback as core  # type: ignore
    from ._fallback import Project as RustProject  # type: ignore
    _HAS_CORE = False


class Project:
    """High-level wrapper for a QGIS project — native speed via Rust when available."""

    def __init__(self, inner: RustProject):
        self._inner = inner

    @classmethod
    def open(cls, path: Union[str, Path]) -> "Project":
        inner = RustProject.open(str(path))
        return cls(inner)

    @property
    def path(self) -> Path:
        return Path(self._inner.path)

    @property
    def format(self) -> str:
        return self._inner.format

    def info(self):
        return self._inner.info()

    def __repr__(self) -> str:
        return f"Project(path={self.path})"


def plan_tiles(bounds: str, zoom: str) -> tuple[int, list]:
    """
    Pure-Rust tile planning — no QGIS needed, native speed when _core is present.

    Returns (total_tiles, levels) where levels is list of
    (zoom, x_min, x_max, y_min, y_max, count).
    """
    return core.plan_tiles(bounds, zoom)
