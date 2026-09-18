"""Qt helpers, imported lazily so the SDK works without Qt installed.

Includes helpers for QDialog via .ui files and QWebEngineView.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .plugin import ActionSpec

__all__ = ["make_action", "make_dialog", "make_web_view"]


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


def make_dialog(ui_file: Union[str, Path], parent: Any = None, title: str | None = None) -> Any:
    """Load .ui file and return QDialog instance.

    Uses uic.loadUiType (recommended over pyuic5) — runtime loading.
    Sets WA_DeleteOnClose to avoid QGIS crashes.
    """
    ui_path = Path(ui_file)
    if not ui_path.exists():
        raise FileNotFoundError(f"UI file not found: {ui_file}")

    from qgis.PyQt import QtWidgets, uic  # type: ignore
    from qgis.PyQt.QtCore import Qt  # type: ignore

    FORM_CLASS, _ = uic.loadUiType(str(ui_path))

    class UiDialog(QtWidgets.QDialog, FORM_CLASS):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setupUi(self)
            if title:
                self.setWindowTitle(title)
            self.setAttribute(Qt.WA_DeleteOnClose)

    if parent is None:
        try:
            from qgis.utils import iface  # type: ignore
            if iface and hasattr(iface, "mainWindow"):
                parent = iface.mainWindow()
        except Exception:
            parent = None

    return UiDialog(parent)


def make_web_view(html: str = "", url: str | None = None, parent: Any = None) -> Any:
    """Create QWebEngineView with HTML or URL.

    IMPORTANT: QWebEngineView must be imported BEFORE QApplication
    (QGIS issue #49512, Reddit r/QGIS).

    For QWebChannel bridge, see qgis_sdk.ui.WebDialog.
    """
    try:
        from qgis.PyQt.QtWebEngineWidgets import QWebEngineView  # type: ignore
    except ImportError:
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView  # type: ignore
        except ImportError:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore

    view = QWebEngineView(parent)
    if url:
        try:
            from qgis.PyQt.QtCore import QUrl  # type: ignore
        except ImportError:
            try:
                from PyQt5.QtCore import QUrl  # type: ignore
            except ImportError:
                from PyQt6.QtCore import QUrl  # type: ignore
        view.setUrl(QUrl(url))
    else:
        view.setHtml(html)
    return view
