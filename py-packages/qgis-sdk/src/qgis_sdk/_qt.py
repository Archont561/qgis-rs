"""qgis_sdk._qt — single funnel for all Qt imports, PyQt6 + PySide6 shims.

This module is the ONLY place that may import from qgis.PyQt, PyQt6, PySide6, PyQt5.
Everything else in the SDK must import from here.

Handles:
- binding detection: qgis (SIP/PyQt), pyqt6, pyside6, pyqt5, none
- pyqtSignal/pyqtSlot vs Signal/Slot unification
- QEventLoop.exec_() → exec() (gone in PyQt6/PySide6)
- Qt.WindowModal → Qt.WindowModality.WindowModal (Qt6 scoped enums)
- uic.loadUiType vs QUiLoader
- QWebEngineView import-before-QApplication guard

Usage:
    from qgis_sdk._qt import QtWidgets, QtCore, Qt, QUrl, QEventLoop, run_loop, Signal, Slot
    from qgis_sdk._qt import make_action, make_dialog, make_web_view
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, Union

# ── binding detection ────────────────────────────────────────────────────────

_BINDING: Optional[str] = None
_QT_MODULES: dict[str, Any] = {}

def _detect_binding() -> str:
    global _BINDING
    if _BINDING is not None:
        return _BINDING

    # 1. qgis.PyQt (SIP, preferred inside QGIS)
    try:
        import qgis.PyQt  # noqa: F401
        _BINDING = "qgis"
        return _BINDING
    except ImportError:
        pass

    # 2. PyQt6
    try:
        import PyQt6  # noqa: F401
        _BINDING = "pyqt6"
        return _BINDING
    except ImportError:
        pass

    # 3. PySide6
    try:
        import PySide6  # noqa: F401
        _BINDING = "pyside6"
        return _BINDING
    except ImportError:
        pass

    # 4. PyQt5 fallback
    try:
        import PyQt5  # noqa: F401
        _BINDING = "pyqt5"
        return _BINDING
    except ImportError:
        pass

    _BINDING = "none"
    return _BINDING

def get_binding() -> str:
    return _detect_binding()

def is_pyqt() -> bool:
    return get_binding() in ("qgis", "pyqt6", "pyqt5")

def is_pyside() -> bool:
    return get_binding() == "pyside6"

def is_qt6() -> bool:
    return get_binding() in ("pyqt6", "pyside6", "qgis")  # qgis 3.44+ is Qt6

# ── lazy Qt module importers ─────────────────────────────────────────────────

def _import_qgis_qt():
    """Try qgis.PyQt modules."""
    try:
        from qgis.PyQt import QtWidgets, QtCore, QtGui, QtNetwork  # type: ignore
        from qgis.PyQt.QtCore import Qt  # type: ignore
        try:
            from qgis.PyQt.QtWebEngineWidgets import QWebEngineView  # type: ignore
        except ImportError:
            QWebEngineView = None
        try:
            from qgis.PyQt.QtWebChannel import QWebChannel  # type: ignore
        except ImportError:
            QWebChannel = None
        try:
            from qgis.PyQt import uic  # type: ignore
        except ImportError:
            uic = None
        return {
            "QtWidgets": QtWidgets,
            "QtCore": QtCore,
            "QtGui": QtGui,
            "QtNetwork": QtNetwork,
            "Qt": Qt,
            "QWebEngineView": QWebEngineView,
            "QWebChannel": QWebChannel,
            "uic": uic,
            "binding": "qgis",
        }
    except ImportError:
        return None

def _import_pyqt6():
    try:
        from PyQt6 import QtWidgets, QtCore, QtGui, QtNetwork  # type: ignore
        from PyQt6.QtCore import Qt  # type: ignore
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
        except ImportError:
            QWebEngineView = None
        try:
            from PyQt6.QtWebChannel import QWebChannel  # type: ignore
        except ImportError:
            QWebChannel = None
        try:
            from PyQt6 import uic  # type: ignore
        except ImportError:
            uic = None
        return {
            "QtWidgets": QtWidgets,
            "QtCore": QtCore,
            "QtGui": QtGui,
            "QtNetwork": QtNetwork,
            "Qt": Qt,
            "QWebEngineView": QWebEngineView,
            "QWebChannel": QWebChannel,
            "uic": uic,
            "binding": "pyqt6",
        }
    except ImportError:
        return None

def _import_pyside6():
    try:
        from PySide6 import QtWidgets, QtCore, QtGui, QtNetwork  # type: ignore
        from PySide6.QtCore import Qt  # type: ignore
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
        except ImportError:
            QWebEngineView = None
        try:
            from PySide6.QtWebChannel import QWebChannel  # type: ignore
        except ImportError:
            QWebChannel = None
        # PySide6 uses QUiLoader instead of uic
        try:
            from PySide6.QtUiTools import QUiLoader  # type: ignore
            uic = None
        except ImportError:
            QUiLoader = None
            uic = None
        return {
            "QtWidgets": QtWidgets,
            "QtCore": QtCore,
            "QtGui": QtGui,
            "QtNetwork": QtNetwork,
            "Qt": Qt,
            "QWebEngineView": QWebEngineView,
            "QWebChannel": QWebChannel,
            "uic": uic,
            "binding": "pyside6",
        }
    except ImportError:
        return None

def _import_pyqt5():
    try:
        from PyQt5 import QtWidgets, QtCore, QtGui, QtNetwork  # type: ignore
        from PyQt5.QtCore import Qt  # type: ignore
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView  # type: ignore
        except ImportError:
            QWebEngineView = None
        try:
            from PyQt5.QtWebChannel import QWebChannel  # type: ignore
        except ImportError:
            QWebChannel = None
        try:
            from PyQt5 import uic  # type: ignore
        except ImportError:
            uic = None
        return {
            "QtWidgets": QtWidgets,
            "QtCore": QtCore,
            "QtGui": QtGui,
            "QtNetwork": QtNetwork,
            "Qt": Qt,
            "QWebEngineView": QWebEngineView,
            "QWebChannel": QWebChannel,
            "uic": uic,
            "binding": "pyqt5",
        }
    except ImportError:
        return None

def _get_qt_modules():
    global _QT_MODULES
    if _QT_MODULES:
        return _QT_MODULES

    binding = _detect_binding()

    loader = {
        "qgis": _import_qgis_qt,
        "pyqt6": _import_pyqt6,
        "pyside6": _import_pyside6,
        "pyqt5": _import_pyqt5,
    }.get(binding)

    if loader:
        mods = loader()
        if mods:
            _QT_MODULES = mods
            return _QT_MODULES

    # Try all in order as fallback
    for fn in (_import_qgis_qt, _import_pyqt6, _import_pyside6, _import_pyqt5):
        mods = fn()
        if mods:
            _QT_MODULES = mods
            _BINDING = mods["binding"]
            return _QT_MODULES

    _QT_MODULES = {}
    return _QT_MODULES

# ── public lazy accessors ────────────────────────────────────────────────────

def _require_qt() -> Tuple[Any, Any, Any, Any, Any]:
    """Return (QtWidgets, uic, Qt, QWebEngineView, QWebChannel) or raise."""
    mods = _get_qt_modules()
    if not mods or "QtWidgets" not in mods:
        raise ImportError(
            "Qt not available. Install PyQt6 (pip install PyQt6) or PySide6 (pip install PySide6) "
            "or run inside QGIS. Tried qgis.PyQt, PyQt6, PySide6, PyQt5."
        )
    return (
        mods.get("QtWidgets"),
        mods.get("uic"),
        mods.get("Qt"),
        mods.get("QWebEngineView"),
        mods.get("QWebChannel"),
    )

def _require_webengine() -> Tuple[Any, Any]:
    mods = _get_qt_modules()
    if not mods:
        raise ImportError("Qt not available")
    QWebEngineView = mods.get("QWebEngineView")
    QWebChannel = mods.get("QWebChannel")
    if QWebEngineView is None or QWebChannel is None:
        raise ImportError(
            "QWebEngine not available. Install PyQt6-WebEngine or PySide6 with WebEngine support."
        )
    return QWebEngineView, QWebChannel

# ── Signal/Slot unification ──────────────────────────────────────────────────

def _get_signal_slot():
    mods = _get_qt_modules()
    if not mods:
        return None, None

    QtCore = mods.get("QtCore")
    if QtCore is None:
        return None, None

    binding = mods.get("binding", get_binding())

    if binding in ("qgis", "pyqt6", "pyqt5"):
        # PyQt: pyqtSignal, pyqtSlot
        try:
            Signal = QtCore.pyqtSignal
            Slot = QtCore.pyqtSlot
            return Signal, Slot
        except AttributeError:
            pass
    elif binding == "pyside6":
        try:
            Signal = QtCore.Signal
            Slot = QtCore.Slot
            return Signal, Slot
        except AttributeError:
            pass

    return None, None

# Lazy properties for common classes
def _lazy_import(class_path: str):
    """Import a Qt class by path like 'QtWidgets.QAction'."""
    mods = _get_qt_modules()
    if not mods:
        return None
    parts = class_path.split(".")
    if len(parts) != 2:
        return None
    mod_name, cls_name = parts
    mod = mods.get(mod_name)
    if mod is None:
        return None
    return getattr(mod, cls_name, None)

# ── Qt6 compatibility helpers ────────────────────────────────────────────────

def run_loop(loop, timeout_ms: Optional[int] = None) -> Any:
    """Run QEventLoop with timeout, handling exec_() vs exec() difference.

    PyQt6/PySide6 removed exec_(), use exec(). PyQt5 has both.
    """
    if loop is None:
        return None

    mods = _get_qt_modules()
    QtCore = mods.get("QtCore") if mods else None

    if timeout_ms is not None and QtCore is not None:
        try:
            QtCore.QTimer.singleShot(timeout_ms, loop.quit)
        except Exception:
            pass

    # Qt6: exec(), Qt5: exec_() or exec()
    if hasattr(loop, "exec"):
        try:
            return loop.exec()
        except TypeError:
            # Some bindings need exec_ for compat
            if hasattr(loop, "exec_"):
                return loop.exec_()
            raise
    elif hasattr(loop, "exec_"):
        return loop.exec_()
    else:
        raise AttributeError("QEventLoop has neither exec() nor exec_()")

def get_window_modality(window_modal: bool = True) -> Any:
    """Get WindowModal enum value handling Qt5 vs Qt6 scoped enums."""
    mods = _get_qt_modules()
    if not mods:
        return None
    Qt = mods.get("Qt")
    QtCore = mods.get("QtCore")
    if Qt is None:
        return None

    # Qt6: Qt.WindowModality.WindowModal
    # Qt5: Qt.WindowModal
    try:
        if hasattr(Qt, "WindowModality"):
            return Qt.WindowModality.WindowModal
        else:
            return Qt.WindowModal
    except AttributeError:
        # Fallback try QtCore
        if QtCore and hasattr(QtCore, "Qt"):
            try:
                if hasattr(QtCore.Qt, "WindowModality"):
                    return QtCore.Qt.WindowModality.WindowModal
                return QtCore.Qt.WindowModal
            except AttributeError:
                pass
        return None

def get_delete_on_close() -> Any:
    """Get WA_DeleteOnClose handling Qt5 vs Qt6."""
    mods = _get_qt_modules()
    if not mods:
        return None
    Qt = mods.get("Qt")
    QtCore = mods.get("QtCore")
    if Qt is None:
        return None

    try:
        if hasattr(Qt, "WidgetAttribute"):
            return Qt.WidgetAttribute.WA_DeleteOnClose
        return Qt.WA_DeleteOnClose
    except AttributeError:
        if QtCore:
            try:
                if hasattr(QtCore.Qt, "WidgetAttribute"):
                    return QtCore.Qt.WidgetAttribute.WA_DeleteOnClose
                return QtCore.Qt.WA_DeleteOnClose
            except AttributeError:
                pass
        return None

# ── High-level helpers (moved from qt.py) ────────────────────────────────────

def _plugin_dir() -> str:
    return os.environ.get("QGIS_SDK_PLUGIN_DIR", os.path.dirname(__file__))

def _resolve_icon(icon: str | None) -> Any:
    if not icon:
        return None
    mods = _get_qt_modules()
    QtGui = mods.get("QtGui") if mods else None
    if QtGui is None:
        return None
    try:
        QIcon = QtGui.QIcon
    except AttributeError:
        return None

    path = icon if os.path.isabs(icon) else os.path.join(_plugin_dir(), icon)
    return QIcon(path) if os.path.exists(path) else None

def make_action(spec: Any, callback: Callable[[], None], parent: Any = None) -> Any:
    """Create QAction for spec that calls callback when triggered."""
    mods = _get_qt_modules()
    if not mods:
        raise ImportError("Qt not available for make_action")
    QtWidgets = mods.get("QtWidgets")
    if QtWidgets is None:
        raise ImportError("QtWidgets not available")

    try:
        QAction = QtWidgets.QAction
    except AttributeError:
        # Try QtGui for older bindings
        QtGui = mods.get("QtGui")
        QAction = getattr(QtGui, "QAction", None) if QtGui else None
        if QAction is None:
            raise ImportError("QAction not available")

    icon = _resolve_icon(getattr(spec, "icon", None))
    tooltip = getattr(spec, "tooltip", "") or getattr(spec, "func_name", "action")
    func_name = getattr(spec, "func_name", "action")

    widget = QAction(icon, tooltip, parent) if icon else QAction(tooltip, parent)
    widget.setObjectName(f"qgis_sdk_{func_name}")
    widget.triggered.connect(lambda _checked=False: callback())
    return widget

def make_dialog(ui_file: Union[str, Path], parent: Any = None, title: str | None = None) -> Any:
    """Load .ui file and return QDialog instance."""
    ui_path = Path(ui_file)
    if not ui_path.exists():
        raise FileNotFoundError(f"UI file not found: {ui_file}")

    mods = _get_qt_modules()
    if not mods:
        raise ImportError("Qt not available for make_dialog")
    QtWidgets = mods.get("QtWidgets")
    uic = mods.get("uic")
    Qt = mods.get("Qt")
    if QtWidgets is None:
        raise ImportError("QtWidgets not available")

    # PySide6 uses QUiLoader
    binding = mods.get("binding", get_binding())
    if binding == "pyside6":
        try:
            from PySide6.QtUiTools import QUiLoader  # type: ignore
            from PySide6.QtCore import QFile  # type: ignore
            loader = QUiLoader()
            file = QFile(str(ui_path))
            file.open(QFile.ReadOnly)
            dialog = loader.load(file, parent)
            file.close()
            if dialog and title:
                dialog.setWindowTitle(title)
            if dialog:
                wa = get_delete_on_close()
                if wa is not None:
                    dialog.setAttribute(wa)
            return dialog
        except Exception as e:
            raise ImportError(f"Failed to load .ui with QUiLoader: {e}")

    if uic is None:
        raise ImportError("uic not available for make_dialog")

    FORM_CLASS, _ = uic.loadUiType(str(ui_path))

    class UiDialog(QtWidgets.QDialog, FORM_CLASS):  # type: ignore
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setupUi(self)
            if title:
                self.setWindowTitle(title)
            wa = get_delete_on_close()
            if wa is not None:
                self.setAttribute(wa)

    if parent is None:
        try:
            from qgis.utils import iface  # type: ignore
            if iface and hasattr(iface, "mainWindow"):
                parent = iface.mainWindow()
        except Exception:
            parent = None

    return UiDialog(parent)

def make_web_view(html: str = "", url: str | None = None, parent: Any = None) -> Any:
    """Create QWebEngineView with HTML or URL."""
    mods = _get_qt_modules()
    if not mods:
        raise ImportError("Qt not available for make_web_view")
    QWebEngineView = mods.get("QWebEngineView")
    if QWebEngineView is None:
        raise ImportError("QWebEngineView not available")

    view = QWebEngineView(parent)
    if url:
        # QUrl handling
        QtCore = mods.get("QtCore")
        if QtCore and hasattr(QtCore, "QUrl"):
            QUrl = QtCore.QUrl
        else:
            # Try Qt
            Qt = mods.get("Qt")
            QUrl = getattr(Qt, "QUrl", None) if Qt else None
            if QUrl is None:
                # Fallback import
                try:
                    from qgis.PyQt.QtCore import QUrl  # type: ignore
                except ImportError:
                    try:
                        from PyQt6.QtCore import QUrl  # type: ignore
                    except ImportError:
                        try:
                            from PySide6.QtCore import QUrl  # type: ignore
                        except ImportError:
                            from PyQt5.QtCore import QUrl  # type: ignore
        view.setUrl(QUrl(url))
    else:
        view.setHtml(html)
    return view

# ── Convenience re-exports for common classes (lazy) ─────────────────────────

def __getattr__(name: str) -> Any:
    """Lazy import of Qt classes for `from qgis_sdk._qt import QAction` etc."""
    # Map of common names to their module
    mapping = {
        "QtWidgets": "QtWidgets",
        "QtCore": "QtCore",
        "QtGui": "QtGui",
        "QtNetwork": "QtNetwork",
        "Qt": "Qt",
        "QWebEngineView": "QWebEngineView",
        "QWebChannel": "QWebChannel",
        "uic": "uic",
        "QAction": "QtWidgets.QAction",
        "QDialog": "QtWidgets.QDialog",
        "QIcon": "QtGui.QIcon",
        "QSettings": "QtCore.QSettings",
        "QMessageBox": "QtWidgets.QMessageBox",
        "QProgressDialog": "QtWidgets.QProgressDialog",
        "QUrl": "QtCore.QUrl",
        "QEventLoop": "QtCore.QEventLoop",
        "QTimer": "QtCore.QTimer",
        "QNetworkRequest": "QtNetwork.QNetworkRequest",
        "QNetworkAccessManager": "QtNetwork.QNetworkAccessManager",
        "QNetworkReply": "QtNetwork.QNetworkReply",
        "QObject": "QtCore.QObject",
        "QVariant": "QtCore.QVariant",
        "QDialogButtonBox": "QtWidgets.QDialogButtonBox",
        "QVBoxLayout": "QtWidgets.QVBoxLayout",
        "QHBoxLayout": "QtWidgets.QHBoxLayout",
        "QFormLayout": "QtWidgets.QFormLayout",
        "QLabel": "QtWidgets.QLabel",
        "QLineEdit": "QtWidgets.QLineEdit",
        "QDoubleSpinBox": "QtWidgets.QDoubleSpinBox",
        "QCheckBox": "QtWidgets.QCheckBox",
        "QComboBox": "QtWidgets.QComboBox",
        "QPushButton": "QtWidgets.QPushButton",
    }

    if name in ("Signal", "Slot", "pyqtSignal", "pyqtSlot"):
        sig, slot = _get_signal_slot()
        if name in ("Signal", "pyqtSignal"):
            if sig is None:
                raise AttributeError(f"Signal not available (binding={get_binding()})")
            return sig
        else:
            if slot is None:
                raise AttributeError(f"Slot not available (binding={get_binding()})")
            return slot

    if name in mapping:
        target = mapping[name]
        if "." in target:
            result = _lazy_import(target)
            if result is not None:
                return result
        else:
            mods = _get_qt_modules()
            if mods and target in mods:
                val = mods[target]
                if val is not None:
                    return val

    # Fallback for QtCore classes
    mods = _get_qt_modules()
    if mods:
        for mod_key in ("QtWidgets", "QtCore", "QtGui", "QtNetwork"):
            mod = mods.get(mod_key)
            if mod and hasattr(mod, name):
                return getattr(mod, name)
        Qt = mods.get("Qt")
        if Qt and hasattr(Qt, name):
            return getattr(Qt, name)

    raise AttributeError(f"module 'qgis_sdk._qt' has no attribute '{name}' (binding={get_binding()})")

__all__ = [
    "get_binding",
    "is_pyqt",
    "is_pyside",
    "is_qt6",
    "run_loop",
    "get_window_modality",
    "get_delete_on_close",
    "make_action",
    "make_dialog",
    "make_web_view",
    "Signal",
    "Slot",
    "pyqtSignal",
    "pyqtSlot",
]
