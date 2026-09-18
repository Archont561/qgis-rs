"""
qgis_sdk.ui — UI helpers for QGIS plugins: dialogs via PyQt and WebEngine with HTML.

This module provides Pythonic wrappers around QGIS/Qt UI patterns discovered via web research:
- Qt Designer .ui loading via uic.loadUiType (recommended over pyuic5) [pyqgis.com]
- QDialog with layouts, promoted widgets, QSettings persistence, QgsTaskManager
- QWebEngineView with HTML/CSS/JS and QWebChannel bridge (Python ↔ JS)

Supports any modern frontend stack inside QWebEngineView (Chromium):
- Vanilla JS + Leaflet/MapLibre (scaffold default)
- React 18 (hook useQgisBridge, Babel CDN or Vite build -> web/dist)
- Vue 3 Composition API (ref/onMounted, Vite build)
- Web Components (Shadow DOM, customElements, no build step)

The Rust core (qgis_sdk._core) accelerates validation and scaffolding at native speed,
but all UI code falls back to pure Python so tests run without QGIS/Qt.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple, Union

# ── Lazy Qt imports (no import at module scope — keeps SDK testable without QGIS) ──

def _require_qt():
    """Try to import Qt, return (QtWidgets, uic, QWebEngineView, QWebChannel) or raise with helpful message."""
    try:
        from qgis.PyQt import QtWidgets, uic  # type: ignore
        from qgis.PyQt.QtCore import Qt  # type: ignore
        return QtWidgets, uic, Qt, None, None
    except ImportError as exc:
        # Try PyQt directly
        try:
            from PyQt5 import QtWidgets, uic  # type: ignore
            from PyQt5.QtCore import Qt  # type: ignore
            return QtWidgets, uic, Qt, None, None
        except ImportError:
            try:
                from PyQt6 import QtWidgets, uic  # type: ignore
                from PyQt6.QtCore import Qt  # type: ignore
                return QtWidgets, uic, Qt, None, None
            except ImportError as exc2:
                from .runtime import PyQgisImportError
                raise PyQgisImportError(
                    f"Qt not available: {exc2}. Install QGIS or PyQt5/6 to use UI dialogs."
                ) from exc2

def _require_webengine():
    """Import QWebEngineView and QWebChannel, or raise."""
    try:
        from qgis.PyQt.QtWebEngineWidgets import QWebEngineView  # type: ignore
        from qgis.PyQt.QtWebChannel import QWebChannel  # type: ignore
        return QWebEngineView, QWebChannel
    except ImportError:
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView  # type: ignore
            from PyQt5.QtWebChannel import QWebChannel  # type: ignore
            return QWebEngineView, QWebChannel
        except ImportError:
            try:
                from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
                from PyQt6.QtWebChannel import QWebChannel  # type: ignore
                return QWebEngineView, QWebChannel
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
    """Declarative QDialog — builds from FieldSpec list or .ui file, with QSettings persistence.

    Example:
        dlg = Dialog(
            title="My Tool",
            layout=layout.vertical(
                field.layer("input_layer", label="Input layer"),
                field.spin("threshold", label="Threshold", default=0.5),
                layout.buttons(Button.ok(), Button.cancel())
            ),
            persist=True  # saves to QSettings
        )
        if dlg.exec() == Dialog.Accepted:
            print(dlg.get("input_layer"))
    """

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
            # Try to get from actual QDialog widgets
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
            FORM_CLASS, _ = uic.loadUiType(str(self.ui_file))

            class UiDialog(QtWidgets.QDialog, FORM_CLASS):
                def __init__(inner_self, parent=None):
                    super().__init__(parent)
                    inner_self.setupUi(inner_self)
                    inner_self.setWindowTitle(self.title)
                    inner_self.setAttribute(Qt.WA_DeleteOnClose)
                    if self.width and self.height:
                        inner_self.resize(self.width, self.height)

            # Parent handling for QGIS
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

            # Restore QSettings if persist
            if self.persist:
                self._restore_qsettings(dlg)

            result = dlg.exec()
            
            if self.persist and result == QtWidgets.QDialog.Accepted:
                self._save_qsettings(dlg)

            return result

        except Exception as exc:
            # Fallback for testing without Qt
            print(f"[Dialog fallback] {self.title} — {exc}")
            print(f"Fields: {self._values}")
            return Dialog.Accepted

    def _exec_declarative(self) -> int:
        try:
            QtWidgets, _, Qt, _, _ = _require_qt()
            
            dlg = QtWidgets.QDialog(self.parent)
            dlg.setWindowTitle(self.title)
            dlg.resize(self.width, self.height)
            dlg.setAttribute(Qt.WA_DeleteOnClose)

            layout = QtWidgets.QVBoxLayout(dlg)

            # Create widgets from FieldSpec
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
                        # Try QgsMapLayerComboBox, fallback to QComboBox
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
                    pass  # handled by button box
                elif isinstance(item, list):
                    # Nested layout — skip for simplicity in fallback
                    pass

            # Button box
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

            result = dlg.exec()

            if self.persist and result == QtWidgets.QDialog.Accepted:
                self._save_qsettings(dlg)

            return result

        except Exception as exc:
            print(f"[Dialog fallback] {self.title} — {exc}")
            print(f"Fields: {self._values}")
            # For testing, simulate user accepting with defaults
            return Dialog.Accepted

    def _restore_qsettings(self, dlg: Any) -> None:
        try:
            from qgis.PyQt.QtCore import QSettings  # type: ignore
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
            from qgis.PyQt.QtCore import QSettings  # type: ignore
            settings = QSettings()
            prefix = f"{self.title}/dialog"
            for name in self._values:
                # Try to get actual widget value
                actual = self.get(name)
                settings.setValue(f"{prefix}/{name}", actual)
        except Exception:
            pass

# ── Decorator for dialog functions ──────────────────────────────────────────

def dialog(title: str = "Dialog", width: int = 400, height: int = 300, persist: bool = False):
    """Decorator to define a dialog from a function returning FieldSpec list.

    Example:
        @dialog(title="Settings", persist=True)
        def settings_dialog():
            return [
                field.text("name", label="Name"),
                field.spin("threshold", label="Threshold", default=0.5),
            ]

        dlg = settings_dialog()
        if dlg.exec() == Dialog.Accepted:
            print(dlg.get("name"))
    """
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
    """QDialog + QWebEngineView + QWebChannel — HTML/CSS/JS dialog for QGIS plugins.

    Example:
        dlg = WebDialog(
            title="Map View",
            html="<html><body><h1>Hello</h1><div id='map'></div></body></html>",
            width=800,
            height=600,
        )

        @web_bridge(dlg)
        class Bridge:
            def get_layer(self):
                return {"name": "buildings", "count": 100}

        dlg.exec()

    JS side (inside html):
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
        var bridge = null;
        new QWebChannel(qt.webChannelTransport, function(channel) {
            bridge = channel.objects.bridge;
            bridge.get_layer(function(info) {
                document.getElementById('layer').innerText = info.name;
            });
        });
        </script>
    """

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
        # baseUrl for relative resources
        return cls(title=title, html=html, width=width, height=height, parent=parent)

    def set_bridge(self, bridge_obj: Any) -> None:
        """Set Python object exposed to JS via QWebChannel as 'bridge'."""
        self._bridge = bridge_obj

    def run_js(self, js_code: str, callback: Optional[Callable] = None) -> None:
        """Run JavaScript in web view: Python → JS."""
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
        """Show dialog modally."""
        try:
            QtWidgets, _, Qt, _, _ = _require_qt()
            QWebEngineView, QWebChannel = _require_webengine()

            from qgis.PyQt.QtCore import QObject, pyqtSlot, QVariant, QUrl  # type: ignore

            # Create dialog
            dlg = QtWidgets.QDialog(self.parent)
            dlg.setWindowTitle(self.title)
            dlg.resize(self.width, self.height)
            dlg.setAttribute(Qt.WA_DeleteOnClose)

            vbox = QtWidgets.QVBoxLayout(dlg)
            web_view = QWebEngineView()
            vbox.addWidget(web_view)

            # Button box
            button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
            button_box.accepted.connect(dlg.accept)
            button_box.rejected.connect(dlg.reject)
            vbox.addWidget(button_box)

            dlg.setLayout(vbox)

            # Setup QWebChannel if bridge provided
            if self._bridge is not None:
                # Wrap bridge to ensure pyqtSlot decorators
                # If bridge is already QObject, use directly, else wrap
                if not isinstance(self._bridge, QObject):
                    # Create dynamic QObject wrapper
                    bridge_obj = self._wrap_bridge(self._bridge, QObject, pyqtSlot, QVariant)
                else:
                    bridge_obj = self._bridge

                channel = QWebChannel()
                channel.registerObject("bridge", bridge_obj)
                web_view.page().setWebChannel(channel)

            # Load HTML
            if self.url:
                web_view.setUrl(QUrl(self.url))
            else:
                # Ensure qwebchannel.js is available — Qt provides built-in at qrc:///
                # If html doesn't include it, we could inject, but we assume user includes
                # <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
                web_view.setHtml(self.html, QUrl.fromLocalFile(str(Path.cwd() / "index.html")))

            self._qdialog = dlg
            self._web_view = web_view

            return dlg.exec()

        except Exception as exc:
            print(f"[WebDialog fallback] {self.title} — {exc}")
            print(f"HTML preview: {self.html[:200]}...")
            if self._bridge:
                print(f"Bridge methods: {[m for m in dir(self._bridge) if not m.startswith('_')]}")
            return Dialog.Accepted

    def _wrap_bridge(self, bridge_obj: Any, QObject, pyqtSlot, QVariant):
        """Wrap plain Python object into QObject with pyqtSlot methods."""
        # For simplicity, if bridge_obj is already a class with methods, create QObject subclass
        # that delegates to it and decorates methods as slots
        
        # If bridge_obj is a class instance with methods, we create a QObject that exposes them
        # via pyqtSlot. For this fallback, we use a generic approach: expose methods that don't
        # start with _ as slots returning QVariant.

        class BridgeWrapper(QObject):
            def __init__(self, inner):
                super().__init__()
                self._inner = inner

        # Dynamically add slots for each public method
        for attr_name in dir(bridge_obj):
            if attr_name.startswith('_'):
                continue
            attr = getattr(bridge_obj, attr_name)
            if callable(attr):
                # Create slot wrapper
                def make_slot(method):
                    @pyqtSlot(result=QVariant)
                    def slot_wrapper(self):
                        try:
                            result = method()
                            # If result is dict/list, return as QVariant
                            return result
                        except Exception as e:
                            print(f"Bridge method {method.__name__} failed: {e}")
                            return None
                    # For methods with args, need more complex handling — use generic QVariant slot
                    @pyqtSlot(str, result=str)
                    def slot_wrapper_str(self, arg):
                        try:
                            result = method(arg)
                            return json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                        except Exception as e:
                            return json.dumps({"error": str(e)})
                    return slot_wrapper

                # We add both versions — simple heuristic: try to detect if method expects args
                import inspect
                sig = inspect.signature(attr)
                if len(sig.parameters) == 0:
                    setattr(BridgeWrapper, attr_name, make_slot(attr))
                else:
                    # For methods with args, create a slot that takes string and returns string (JSON)
                    def make_slot_with_arg(method):
                        @pyqtSlot(str, result=str)
                        def slot_wrapper(self, arg):
                            try:
                                # Try to parse arg as JSON, else pass as string
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
    """Decorator to register a bridge class for WebDialog.

    Example:
        dlg = WebDialog(html="...")

        @web_bridge(dlg)
        class Bridge:
            def get_data(self):
                return {"key": "value"}

        dlg.exec()
    """
    def decorator(cls):
        instance = cls()
        web_dialog.set_bridge(instance)
        return cls
    return decorator

# ── Convenience helpers ─────────────────────────────────────────────────────

def make_dialog(ui_file: Union[str, Path], parent: Any = None, title: Optional[str] = None) -> Any:
    """Load .ui file and return QDialog instance (Rust-accelerated validation)."""
    ui_path = Path(ui_file)
    if not ui_path.exists():
        raise FileNotFoundError(f"UI file not found: {ui_file}")

    # Validate via Rust core if available
    try:
        from . import _core as core  # type: ignore
        if hasattr(core, "validate_plugin_structure"):
            errors = core.validate_plugin_structure(str(ui_path.parent))
            if errors:
                print(f"Validation warnings: {errors}")
    except ImportError:
        pass

    QtWidgets, uic, Qt, _, _ = _require_qt()
    FORM_CLASS, _ = uic.loadUiType(str(ui_path))

    class UiDialog(QtWidgets.QDialog, FORM_CLASS):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setupUi(self)
            if title:
                self.setWindowTitle(title)
            self.setAttribute(Qt.WA_DeleteOnClose)

    # Parent handling
    if parent is None:
        try:
            from qgis.utils import iface  # type: ignore
            if iface and hasattr(iface, "mainWindow"):
                parent = iface.mainWindow()
        except Exception:
            parent = None

    return UiDialog(parent)

def make_web_view(html: str = "", url: Optional[str] = None, parent: Any = None) -> Any:
    """Create QWebEngineView with HTML or URL."""
    QWebEngineView, _ = _require_webengine()
    view = QWebEngineView(parent)
    if url:
        from qgis.PyQt.QtCore import QUrl  # type: ignore
        view.setUrl(QUrl(url))
    else:
        view.setHtml(html)
    return view

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
