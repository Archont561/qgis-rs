"""Qt helpers, imported lazily so the SDK works without Qt installed."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .plugin import ActionSpec

__all__ = ["make_action"]


def _icon(icon: str | None, parent: Any = None) -> Any:
    """Resolve a plugin-relative icon path to a ``QIcon`` (or ``None``)."""
    if not icon:
        return None
    from qgis.PyQt.QtGui import QIcon  # lazy: needs Qt

    path = icon if os.path.isabs(icon) else os.path.join(_plugin_dir(), icon)
    return QIcon(path) if os.path.exists(path) else None


def _plugin_dir() -> str:
    """Directory of the plugin package that is being loaded, if any."""
    return os.environ.get("QGIS_SDK_PLUGIN_DIR", os.path.dirname(__file__))


def make_action(spec: ActionSpec, callback: Callable[[], None], parent: Any = None) -> Any:
    """Create a ``QAction`` for ``spec`` that calls ``callback`` when triggered."""
    from qgis.PyQt.QtWidgets import QAction  # lazy: needs Qt

    widget = QAction(_icon(spec.icon), spec.tooltip or spec.func_name, parent)
    widget.setObjectName(f"qgis_sdk_{spec.func_name}")
    widget.triggered.connect(lambda _checked=False: callback())
    return widget
