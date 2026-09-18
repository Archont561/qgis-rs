"""
qgis_sdk.ui — UI helpers for QGIS plugins: dialogs via PyQt and WebEngine with HTML.

This module now uses qgis_sdk._qt as the single Qt funnel (PyQt6/PySide6 support).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple, Union

from ._qt import (
    get_binding,
    get_delete_on_close,
    get_window_modality,
    _get_qt_modules,
    _require_qt as _qt_require_qt,
    _require_webengine as _qt_require_webengine,
    make_dialog as _qt_make_dialog,
    make_web_view as _qt_make_web_view,
)

# ── Lazy Qt imports via _qt funnel ───────────────────────────────────────────

def _require_qt():
    """Try to import Qt via _qt funnel, return (QtWidgets, uic, Qt, QWebEngineView, QWebChannel)."""
    try:
        return _qt_require_qt()
    except ImportError as exc:
        from .runtime import PyQgisImportError
        raise PyQgisImportError(
            f"Qt not available: {exc}. Install QGIS or PyQt6/PySide6."
        ) from exc

def _require_webengine():
    try:
        return _qt_require_webengine()
    except ImportError as exc:
        from .runtime import PyQgisImportError
        raise PyQgisImportError(
            f"QtWebEngine not available: {exc}. Install qt-webengine or PyQtWebEngine."
        ) from exc

# ── Declarative field definitions ───────────────────────────────────────────

@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str = ""
    default: Any = None
    field_type: str = "text"  # text, spin, combo, file, layer, crs, check, etc.
    options: Tuple[str, ...] = ()
    min: Optional[float] = None
    max: Optional[float] = None
    layer_filter: Optional[str] = None  # vector, raster, etc.

class field:
    """Declarative field builders for Dialog."""

    @staticmethod
    def text(name: str, label: str = "", default: str = "") -> FieldSpec:
        return FieldSpec(name=name, label=label or name, default=default, field_type="text")

    @staticmethod
    def spin(name: str, label: str = "", default: float = 0.0, min: float = 0.0, max: float = 100.0) -> FieldSpec:
        return FieldSpec(name=name, label=label or name, default=default, field_type="spin", min=min, max=max)

    @staticmethod
    def check(name: str, label: str = "", default: bool = False) -> FieldSpec:
        return FieldSpec(name=name, label=label or name, default=default, field_type="check")

    @staticmethod
    def combo(name: str, label: str = "", options: List[str] = (), default: str = "") -> FieldSpec:
        return FieldSpec(name=name, label=label or name, default=default, field_type="combo", options=tuple(options))

    @staticmethod
    def file(name: str, label: str = "", default: str = "", filter: str = "") -> FieldSpec:
        return FieldSpec(name=name, label=label or name, default=default, field_type="file", options=(filter,))

    @staticmethod
    def layer(name: str, label: str = "", layer_filter: str = "vector", default: str = "") -> FieldSpec:
        return FieldSpec(name=name, label=label or name, default=default, field_type="layer", layer_filter=layer_filter)

    @staticmethod
    def crs(name: str, label: str = "", default: str = "EPSG:4326") -> FieldSpec:
        return FieldSpec(name=name, label=label or name, default=default, field_type="crs")

class Button:
    @staticmethod
    def ok() -> str: return "ok"
    @staticmethod
    def cancel() -> str: return "cancel"
    @staticmethod
    def apply() -> str: return "apply"
    @staticmethod
    def custom(text: str) -> str: return text

class layout:
    @staticmethod
    def vertical(*items) -> List[Any]: return list(items)
    @staticmethod
    def horizontal(*items) -> List[Any]: return list(items)
    @staticmethod
    def grid(*items) -> List[Any]: return list(items)
    @staticmethod
    def form(*items) -> List[Any]: return list(items)
    @staticmethod
    def tabs(*items) -> List[Any]: return list(items)
    @staticmethod
    def buttons(*buttons) -> List[str]: return list(buttons)

# ── Dialog (declarative + .ui loading) ───────────────────────────────────────

class Dialog:
    """Declarative QDialog — builds from FieldSpec list or .ui file, with QSettings persistence."""

    Accepted = 1
    Rejected = 0

    def __init__(
        self,
        title: str = "Dialog",
        layout: Optional[List[Any]] = None,
        ui_file: Optional[Union[str, Path]] = None,
        width: int = 400,
        height: int = 300,
        persist: bool = False,
        parent: Any = None,
    ):
        self.title = title
        self.layout_spec = layout or []
        self.ui_file = Path(ui_file) if ui_file else None
        self.width = width
        self.height = height
        self.persist = persist
        self.parent = parent
        self._values: dict[str, Any] = {}
        self._qdialog: Any = None

        # Extract defaults
        for item in self._flatten_layout(self.layout_spec):
            if isinstance(item, FieldSpec):
                self._values[item.name] = item.default

    def _flatten_layout(self, items: List[Any]) -> List[Any]:
        flat = []
        for item in items:
            if isinstance(item, list):
                flat.extend(self._flatten_layout(item))
            else:
                flat.append(item)
        return flat

    def get(self, name: str) -> Any:
        """Get field value."""
        if self._qdialog is not None:
            try:
                widget = getattr(self._qdialog, f"{name}_field", None) or getattr(self._qdialog, name, None)
                if widget is not None:
                    if hasattr(widget, "text"):
                        return widget.text()
                    if hasattr(widget, "value"):
                        return widget.value()
                    if hasattr(widget, "isChecked"):
                        return widget.isChecked()
                    if hasattr(widget, "currentText"):
                        return widget.currentText()
                    if hasattr(widget, "currentLayer"):
                        return widget.currentLayer()
            except Exception:
                pass
        return self._values.get(name)

    def set(self, name: str, value: Any) -> None:
        self._values[name] = value

    def exec(self) -> int:
        """Show dialog modally — tries Qt, falls back to console prompt for testing."""
        if self.ui_file and self.ui_file.exists():
            return self._exec_from_ui()
        else:
            return self._exec_declarative()

    def _exec_from_ui(self) -> int:
        try:
            QtWidgets, uic, Qt, _, _ = _require_qt()
            mods = _get_qt_modules()
            binding = mods.get("binding", get_binding())

            if binding == "pyside6":
                # Use QUiLoader path via _qt.make_dialog
                dlg = _qt_make_dialog(str(self.ui_file), parent=self.parent, title=self.title)
                self._qdialog = dlg
                if self.persist:
                    self._restore_qsettings(dlg)
                result = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
                if self.persist and result == QtWidgets.QDialog.Accepted:
                    self._save_qsettings(dlg)
                return result
            else:
                FORM_CLASS, _ = uic.loadUiType(str(self.ui_file))

                class UiDialog(QtWidgets.QDialog, FORM_CLASS):  # type: ignore
                    def __init__(inner_self, parent=None):
                        super().__init__(parent)
                        inner_self.setupUi(inner_self)
                        inner_self.setWindowTitle(self.title)
                        wa = get_delete_on_close()
                        if wa is not None:
                            inner_self.setAttribute(wa)
                        if self.width and self.height:
                            inner_self.resize(self.width, self.height)

                parent = self.parent
                if parent is None:
                    try:
                        from qgis.utils import iface  # type: ignore
                        if iface and hasattr(iface, "mainWindow"):
                            parent = iface.mainWindow()
                    except Exception:
                        parent = None

                dlg = UiDialog(parent)
                self._qdialog = dlg

                if self.persist:
                    self._restore_qsettings(dlg)

                result = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()
                
                if self.persist and result == QtWidgets.QDialog.Accepted:
                    self._save_qsettings(dlg)

                return result

        except Exception as exc:
            print(f"[Dialog fallback] {self.title} — {exc}")
            print(f"Fields: {self._values}")
            return Dialog.Accepted

    def _exec_declarative(self) -> int:
        try:
            QtWidgets, _, Qt, _, _ = _require_qt()
            
            dlg = QtWidgets.QDialog(self.parent)
            dlg.setWindowTitle(self.title)
            dlg.resize(self.width, self.height)
            wa = get_delete_on_close()
            if wa is not None:
                dlg.setAttribute(wa)

            layout = QtWidgets.QVBoxLayout(dlg)

            for item in self._flatten_layout(self.layout_spec):
                if isinstance(item, FieldSpec):
                    row = QtWidgets.QHBoxLayout()
                    label = QtWidgets.QLabel(item.label or item.name)
                    row.addWidget(label)

                    if item.field_type == "text":
                        widget = QtWidgets.QLineEdit()
                        widget.setText(str(item.default or ""))
                        widget.setObjectName(f"{item.name}_field")
                        row.addWidget(widget)
                    elif item.field_type == "spin":
                        widget = QtWidgets.QDoubleSpinBox()
                        if item.min is not None:
                            widget.setMinimum(item.min)
                        if item.max is not None:
                            widget.setMaximum(item.max)
                        widget.setValue(float(item.default or 0))
                        widget.setObjectName(f"{item.name}_field")
                        row.addWidget(widget)
                    elif item.field_type == "check":
                        widget = QtWidgets.QCheckBox()
                        widget.setChecked(bool(item.default))
                        widget.setObjectName(f"{item.name}_field")
                        row.addWidget(widget)
                    elif item.field_type == "combo":
                        widget = QtWidgets.QComboBox()
                        widget.addItems(list(item.options))
                        if item.default:
                            widget.setCurrentText(str(item.default))
                        widget.setObjectName(f"{item.name}_field")
                        row.addWidget(widget)
                    elif item.field_type == "file":
                        widget = QtWidgets.QLineEdit()
                        widget.setText(str(item.default or ""))
                        widget.setObjectName(f"{item.name}_field")
                        row.addWidget(widget)
                        btn = QtWidgets.QPushButton("Browse...")
                        row.addWidget(btn)
                    elif item.field_type == "layer":
                        try:
                            from qgis.gui import QgsMapLayerComboBox  # type: ignore
                            widget = QgsMapLayerComboBox()
                        except ImportError:
                            widget = QtWidgets.QComboBox()
                            widget.addItem("No layer (QGIS not available)")
                        widget.setObjectName(f"{item.name}_field")
                        row.addWidget(widget)
                    else:
                        widget = QtWidgets.QLineEdit(str(item.default or ""))
                        widget.setObjectName(f"{item.name}_field")
                        row.addWidget(widget)

                    layout.addLayout(row)
                elif isinstance(item, str) and item in ("ok", "cancel", "apply"):
                    pass
                elif isinstance(item, list):
                    pass

            button_box = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
            )
            button_box.accepted.connect(dlg.accept)
            button_box.rejected.connect(dlg.reject)
            layout.addWidget(button_box)

            dlg.setLayout(layout)
            self._qdialog = dlg

            if self.persist:
                self._restore_qsettings(dlg)

            result = dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()

            if self.persist and result == QtWidgets.QDialog.Accepted:
                self._save_qsettings(dlg)

            return result

        except Exception as exc:
            print(f"[Dialog fallback] {self.title} — {exc}")
            print(f"Fields: {self._values}")
            return Dialog.Accepted

    def _restore_qsettings(self, dlg: Any) -> None:
        try:
            mods = _get_qt_modules()
            QtCore = mods.get("QtCore") if mods else None
            QSettings = getattr(QtCore, "QSettings", None) if QtCore else None
            if QSettings is None:
                return
            settings = QSettings()
            prefix = f"{self.title}/dialog"
            for name in self._values:
                key = f"{prefix}/{name}"
                val = settings.value(key)
                if val is not None:
                    self._values[name] = val
        except Exception:
            pass

    def _save_qsettings(self, dlg: Any) -> None:
        try:
            mods = _get_qt_modules()
            QtCore = mods.get("QtCore") if mods else None
            QSettings = getattr(QtCore, "QSettings", None) if QtCore else None
            if QSettings is None:
                return
            settings = QSettings()
            prefix = f"{self.title}/dialog"
            for name in self._values:
                actual = self.get(name)
                settings.setValue(f"{prefix}/{name}", actual)
        except Exception:
            pass

# ── Decorator for dialog functions ──────────────────────────────────────────

def dialog(title: str = "Dialog", width: int = 400, height: int = 300, persist: bool = False):
    def decorator(func: Callable[[], List[Any]]):
        def wrapper(*args, **kwargs) -> Dialog:
            layout_spec = func(*args, **kwargs)
            return Dialog(title=title, layout=layout_spec, width=width, height=height, persist=persist)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator

# ── WebEngine with HTML ─────────────────────────────────────────────────────

class WebDialog:
    """QDialog + QWebEngineView + QWebChannel — HTML/CSS/JS dialog for QGIS plugins."""

    def __init__(
        self,
        title: str = "Web Dialog",
        html: str = "<html><body><h1>QGIS + HTML</h1></body></html>",
        url: Optional[str] = None,
        width: int = 800,
        height: int = 600,
        parent: Any = None,
    ):
        self.title = title
        self.html = html
        self.url = url
        self.width = width
        self.height = height
        self.parent = parent
        self._bridge: Any = None
        self._qdialog: Any = None
        self._web_view: Any = None

    @classmethod
    def from_file(cls, html_file: Union[str, Path], title: str = "Web Dialog", width: int = 800, height: int = 600, parent: Any = None) -> "WebDialog":
        path = Path(html_file)
        if not path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_file}")
        html = path.read_text(encoding="utf-8")
        return cls(title=title, html=html, width=width, height=height, parent=parent)

    def set_bridge(self, bridge_obj: Any) -> None:
        self._bridge = bridge_obj

    def run_js(self, js_code: str, callback: Optional[Callable] = None) -> None:
        if self._web_view is not None:
            try:
                if callback:
                    self._web_view.page().runJavaScript(js_code, callback)
                else:
                    self._web_view.page().runJavaScript(js_code)
            except Exception as exc:
                print(f"[WebDialog] run_js failed: {exc}")
        else:
            print(f"[WebDialog fallback] Would run JS: {js_code[:100]}")

    def exec(self) -> int:
        try:
            QtWidgets, _, Qt, _, _ = _require_qt()
            QWebEngineView, QWebChannel = _require_webengine()

            mods = _get_qt_modules()
            QtCore = mods.get("QtCore") if mods else None
            if QtCore is None:
                raise ImportError("QtCore not available")

            # Get QObject, Slot, QVariant via _qt funnel
            try:
                QObject = QtCore.QObject
                QVariant = QtCore.QVariant
                # Signal/Slot
                if hasattr(QtCore, "pyqtSlot"):
                    pyqtSlot = QtCore.pyqtSlot
                elif hasattr(QtCore, "Slot"):
                    pyqtSlot = QtCore.Slot
                else:
                    pyqtSlot = lambda *a, **k: (lambda f: f)
            except AttributeError:
                from qgis.PyQt.QtCore import QObject, pyqtSlot, QVariant  # type: ignore
                # fallback, will fail if not available but we try

            # Try to get QUrl
            try:
                QUrl = QtCore.QUrl
            except AttributeError:
                QUrl = None
                if QUrl is None:
                    try:
                        from qgis.PyQt.QtCore import QUrl as QUrlFallback  # type: ignore
                        QUrl = QUrlFallback
                    except ImportError:
                        pass

            dlg = QtWidgets.QDialog(self.parent)
            dlg.setWindowTitle(self.title)
            dlg.resize(self.width, self.height)
            wa = get_delete_on_close()
            if wa is not None:
                dlg.setAttribute(wa)

            vbox = QtWidgets.QVBoxLayout(dlg)
            web_view = QWebEngineView()
            vbox.addWidget(web_view)

            button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
            button_box.accepted.connect(dlg.accept)
            button_box.rejected.connect(dlg.reject)
            vbox.addWidget(button_box)

            dlg.setLayout(vbox)

            if self._bridge is not None:
                if not isinstance(self._bridge, QObject):
                    bridge_obj = self._wrap_bridge(self._bridge, QObject, pyqtSlot, QVariant)
                else:
                    bridge_obj = self._bridge

                channel = QWebChannel()
                channel.registerObject("bridge", bridge_obj)
                web_view.page().setWebChannel(channel)

            if self.url and QUrl is not None:
                web_view.setUrl(QUrl(self.url))
            else:
                if QUrl is not None:
                    web_view.setHtml(self.html, QUrl.fromLocalFile(str(Path.cwd() / "index.html")))
                else:
                    web_view.setHtml(self.html)

            self._qdialog = dlg
            self._web_view = web_view

            return dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()

        except Exception as exc:
            print(f"[WebDialog fallback] {self.title} — {exc}")
            print(f"HTML preview: {self.html[:200]}...")
            if self._bridge:
                print(f"Bridge methods: {[m for m in dir(self._bridge) if not m.startswith('_')]}")
            return Dialog.Accepted

    def _wrap_bridge(self, bridge_obj: Any, QObject, pyqtSlot, QVariant):
        class BridgeWrapper(QObject):
            def __init__(self, inner):
                super().__init__()
                self._inner = inner

        for attr_name in dir(bridge_obj):
            if attr_name.startswith('_'):
                continue
            attr = getattr(bridge_obj, attr_name)
            if callable(attr):
                import inspect
                sig = inspect.signature(attr)
                if len(sig.parameters) == 0:
                    def make_slot(method):
                        @pyqtSlot(result=QVariant)
                        def slot_wrapper(self):
                            try:
                                result = method()
                                return result
                            except Exception as e:
                                print(f"Bridge method {method.__name__} failed: {e}")
                                return None
                        return slot_wrapper
                    setattr(BridgeWrapper, attr_name, make_slot(attr))
                else:
                    def make_slot_with_arg(method):
                        @pyqtSlot(str, result=str)
                        def slot_wrapper(self, arg):
                            try:
                                try:
                                    parsed = json.loads(arg)
                                    result = method(parsed)
                                except Exception:
                                    result = method(arg)
                                if isinstance(result, (dict, list)):
                                    return json.dumps(result)
                                return str(result)
                            except Exception as e:
                                return json.dumps({"error": str(e)})
                        return slot_wrapper
                    setattr(BridgeWrapper, attr_name, make_slot_with_arg(attr))

        return BridgeWrapper(bridge_obj)

# ── web_bridge decorator ────────────────────────────────────────────────────

def web_bridge(web_dialog: WebDialog):
    def decorator(cls):
        instance = cls()
        web_dialog.set_bridge(instance)
        return cls
    return decorator

# ── Convenience helpers ─────────────────────────────────────────────────────

def make_dialog(ui_file: Union[str, Path], parent: Any = None, title: Optional[str] = None) -> Any:
    """Load .ui file and return QDialog instance (uses _qt funnel)."""
    return _qt_make_dialog(ui_file, parent=parent, title=title)

def make_web_view(html: str = "", url: Optional[str] = None, parent: Any = None) -> Any:
    """Create QWebEngineView with HTML or URL (uses _qt funnel)."""
    return _qt_make_web_view(html, url=url, parent=parent)

__all__ = [
    "Dialog",
    "WebDialog",
    "dialog",
    "web_bridge",
    "field",
    "layout",
    "Button",
    "FieldSpec",
    "make_dialog",
    "make_web_view",
]
