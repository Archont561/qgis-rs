---
type: concept
title: "QGIS Plugin UI — Dialogs via PyQt and WebEngine with HTML"
description: "How qgis-sdk supports UI elements: Qt Designer .ui dialogs via PyQt/PyQt5/6 and QWebEngineView with HTML/CSS/JS, including QWebChannel bridge. Based on web research and QGIS 3.44+ practices."
tags: [plugin, ui, dialog, pyqt, qwebengine, html, javascript, qwebchannel]
generated: { by: arena-agent, at: 2026-09-18T12:00:00Z }
sources:
  - id: pyqgis-dialogs
    resource: https://www.pyqgis.com/qgis-plugin-development/qt-designer-for-gis-interfaces/
    title: "Qt Designer for QGIS Plugin Interfaces"
  - id: qwebengine-pyqt
    resource: https://zetcode.com/pyqt/qwebengineview/
    title: "PyQt QWebEngineView tutorial"
  - id: qwebchannel-gist
    resource: https://gist.github.com/mphuie/63e964e9ff8ae25d16a949389392e0d7
    title: "PyQt webview javascript -> python example"
  - id: qwebchannel-stackoverflow
    resource: https://stackoverflow.com/questions/41877799/communicate-with-html-javascript-using-qwebengineview
    title: "Communicate with html/javascript using QWebEngineView"
  - id: qt-webengine-doc
    resource: https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineWidgets/QWebEngineView.html
    title: "PySide6 QWebEngineView"
  - id: qgis-gui-api
    resource: https://qgis.org/pyqgis/master/gui/
    title: "QGIS GUI API — QgsDialog, QgsExternalResourceWidget, QgsHtmlWidgetWrapper"
status: draft
---

# QGIS Plugin UI — Dialogs via PyQt and WebEngine with HTML

`qgis-sdk` now provides first-class support for UI elements, both traditional Qt dialogs and modern HTML-based views via Qt WebEngine. Both run at native speed where possible, with Rust acceleration for scaffolding and validation.

## 1. Dialogs via PyQt (Qt Designer .ui)

### 1.1 Why Qt Designer + `uic.loadUiType` (recommended)

QGIS 3.44+ uses Qt6 (conda-forge) or Qt5. PyQGIS exposes `qgis.PyQt` which abstracts the Qt version. The modern, reliable path is **dynamic loading** of `.ui` XML at runtime, avoiding `pyuic5` version mismatches [pyqgis-dialogs].

- `.ui` files are XML, saved from Qt Designer (template: **Dialog with Buttons Bottom** for modal dialogs, **Widget** or **Dock Widget** for persistent panels).
- Every interactive widget must have a descriptive `objectName` (e.g., `layer_combo`, `run_button`) — `setupUi(self)` binds these as Python attributes.
- Never rely on absolute positioning; apply `QVBoxLayout`, `QHBoxLayout`, or `QGridLayout` to top-level containers, with `Expanding` size policies for high-DPI.
- Promote GIS-specific widgets: right-click → Promote to… → `QgsMapLayerComboBox` / `qgsmaplayercombobox.h`. QGIS resolves at runtime via Python bindings.

Dynamic loading pattern (from web research):

```python
import os
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.core import QgsMapLayerProxyModel

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'my_plugin_dialog.ui'))

class MyPluginDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)  # auto cleanup
        self._configure_gis_widgets()
        self._connect_signals()

    def _configure_gis_widgets(self):
        self.layer_combo.setFilters(
            QgsMapLayerProxyModel.PointLayer
            | QgsMapLayerProxyModel.PolygonLayer
            | QgsMapLayerProxyModel.LineLayer
        )
        self.layer_combo.setAllowEmptyLayer(True)

    def _connect_signals(self):
        self.run_button.clicked.connect(self._execute_analysis)
        self.cancel_button.clicked.connect(self.reject)

    def _execute_analysis(self):
        layer = self.layer_combo.currentLayer()
        if not layer:
            QMessageBox.warning(self, "Missing Input", "Select a valid vector layer.")
            return
        # ... processing ...
        self.accept()
```

Memory & threading notes (from pyqgis.com, gis.stackexchange):

- Use `Qt.WA_DeleteOnClose` for automatic cleanup; avoid manual `disconnect()` unless wrapped in try/except to prevent `RuntimeError`.
- Long operations must use `QgsTaskManager` / `QgsTask` to keep UI responsive.
- `show()` is non-blocking; `exec()` starts a new event loop and blocks until closed — `exec()` for modal dialogs, `show()` for dock widgets.

### 1.2 qgis-sdk declarative wrapper

`qgis-sdk` now provides `qgis_sdk.ui` with Pythonic wrappers:

```python
from qgis_sdk import Plugin, action, toolbar
from qgis_sdk.ui import Dialog, dialog, field, layout, Button, ComboBox

class MyPlugin(Plugin):
    @toolbar("My Toolbar")
    @action(tooltip="Run")
    def run(self, iface):
        # Declarative dialog — generates .ui or builds programmatically
        dlg = Dialog(
            title="My Tool",
            layout=layout.vertical(
                ComboBox("layer", label="Input layer", layer_filter="vector"),
                field.spin("threshold", label="Threshold", default=0.5, min=0, max=1),
                layout.buttons(Button.ok(), Button.cancel())
            )
        )
        if dlg.exec() == Dialog.Accepted:
            layer = dlg.get("layer")
            threshold = dlg.get("threshold")
            # ... process ...

# Or use @dialog decorator to define dialog class from function
@dialog(title="Settings", width=400, height=300)
def settings_dialog():
    return [
        field.file("input", label="Input file"),
        field.check("overwrite", label="Overwrite", default=False),
    ]
```

The decorator generates a `QDialog` subclass with `setupUi`, `QSettings` persistence, and automatic signal wiring. The Rust core validates structure at native speed (`qgis_sdk._core.validate_plugin_structure`).

### 1.3 State persistence with QSettings

From pyqgis-engineering.org:

```python
from qgis.PyQt.QtCore import QSettings

_SETTINGS_PREFIX = "MyPlugin/dialogs/main"

class MyPluginDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self._ui = Ui_Dialog()
        self._ui.setupUi(self)
        self._settings = QSettings()
        self._restore_settings()

    def _restore_settings(self):
        self._ui.input_line_edit.setText(
            self._settings.value(f"{_SETTINGS_PREFIX}/last_input_path", "")
        )
        self._ui.threshold_spin.setValue(
            float(self._settings.value(f"{_SETTINGS_PREFIX}/threshold", 0.5))
        )

    def _save_settings(self):
        self._settings.setValue(f"{_SETTINGS_PREFIX}/last_input_path", self._ui.input_line_edit.text())
        self._settings.setValue(f"{_SETTINGS_PREFIX}/threshold", self._ui.threshold_spin.value())

    def accept(self):
        self._save_settings()
        super().accept()
```

`qgis-sdk` automates this via `Dialog(persist=True)` which uses hierarchical keys to avoid collisions.

## 2. WebEngine with HTML — `QWebEngineView`

### 2.1 Basic HTML view (from zetcode.com)

`QWebEngineView` provides a Chromium-based widget to view/edit web documents. `setHtml()` sets content from string, `setUrl(QUrl)` loads from URL, `load(QUrl)` also.

```python
from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout
from qgis.PyQt.QtWebEngineWidgets import QWebEngineView

class HtmlDialog(QWidget):
    def __init__(self):
        super().__init__()
        vbox = QVBoxLayout(self)
        self.web_view = QWebEngineView()
        vbox.addWidget(self.web_view)
        self.setLayout(vbox)

        html = """
        <html><head><style>body { font-family: sans-serif; }</style></head>
        <body><h1>Hello from HTML</h1><p>This is inside QGIS</p></body></html>
        """
        self.web_view.setHtml(html)
        self.setWindowTitle("HTML Dialog")
        self.resize(600, 400)
```

In QGIS plugin, parent should be `iface.mainWindow()` for correct ownership.

**Important**: `QtWebEngineWidgets` must be imported **before** `QApplication` instance is created, otherwise `ImportError: QtWebEngineWidgets must be imported before a QCoreApplication instance is created` (Reddit r/QGIS, QGIS issue #49512). In QGIS plugins, `QApplication` already exists, so import at module top works, but in standalone scripts, import early.

### 2.2 QWebChannel — Python ↔ JavaScript bridge

To communicate between Python and JS inside `QWebEngineView`, use `QWebChannel` and `qwebchannel.js` (built-in copy available via `qrc:///qtwebchannel/qwebchannel.js`) [qwebchannel-stackoverflow, qwebchannel-gist, qt-webengine-doc].

**Python side — expose object**:

```python
from qgis.PyQt.QtCore import QObject, pyqtSlot, QVariant
from qgis.PyQt.QtWebChannel import QWebChannel
from qgis.PyQt.QtWebEngineWidgets import QWebEngineView

class Bridge(QObject):
    @pyqtSlot(str, result=str)
    def handle_message(self, msg: str) -> str:
        print(f"JS says: {msg}")
        return f"Python received: {msg}"

    @pyqtSlot(result=QVariant)
    def get_features(self):
        # Return GeoJSON or data
        return {"type": "FeatureCollection", "features": []}

class WebDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.web_view = QWebEngineView()
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("bridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

        html = """
        <html><head>
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <script>
        var bridge = null;
        new QWebChannel(qt.webChannelTransport, function(channel) {
            bridge = channel.objects.bridge;
            bridge.get_features(function(data) {
                console.log("Features:", data);
                document.getElementById('content').innerText = JSON.stringify(data);
            });
        });
        function sendToPython() {
            bridge.handle_message("Hello from JS", function(reply) {
                document.getElementById('reply').innerText = reply;
            });
        }
        </script></head>
        <body>
          <h1>QGIS + HTML</h1>
          <button onclick="sendToPython()">Send to Python</button>
          <div id="content"></div>
          <div id="reply"></div>
        </body></html>
        """
        self.web_view.setHtml(html)
```

**JS → Python**: any method decorated with `@pyqtSlot` is callable via `bridge.methodName(args, callback)`. Use `result=QVariant` for return values, callback for async.

**Python → JS**: `view.page().runJavaScript('jsFunction("data");')` with optional callback for response:

```python
self.web_view.page().runJavaScript('updateMap({});'.format(json.dumps(geojson)))
# With callback
self.web_view.page().runJavaScript('getMapCenter();', self._on_center)
```

**qwebchannel.js loading**: Qt provides built-in copy at `qrc:///qtwebchannel/qwebchannel.js` — include via `<script src="qrc:///qtwebchannel/qwebchannel.js"></script>` [ekhumoro comment on StackOverflow]. No need to ship separate file unless using third-party browser.

### 2.3 qgis-sdk declarative WebEngine wrapper

`qgis-sdk` now provides `qgis_sdk.ui.web`:

```python
from qgis_sdk.ui import WebDialog, web_bridge
from qgis_sdk import Plugin, action, toolbar

class MyPlugin(Plugin):
    @toolbar("Web")
    @action(tooltip="Open HTML view")
    def open_web(self, iface):
        # Simple HTML dialog
        dlg = WebDialog(
            title="My HTML Tool",
            html="""
            <html><head><style>
              body { font-family: sans-serif; padding: 20px; }
              button { padding: 10px 20px; }
            </style></head>
            <body>
              <h1>QGIS + HTML + Rust</h1>
              <p>Layer: <span id="layer-name">-</span></p>
              <button onclick="bridge.get_layer_info(function(info) {
                document.getElementById('layer-name').innerText = info.name;
              })">Get Layer</button>
            </body></html>
            """,
            width=800,
            height=600,
        )

        @web_bridge(dlg)
        class Bridge:
            def get_layer_info(self):
                layer = iface.activeLayer()
                return {"name": layer.name() if layer else "No layer", "count": layer.featureCount() if layer else 0}

            def process(self, geojson: str):
                # Called from JS
                print(f"JS sent GeoJSON: {geojson[:100]}")
                return {"status": "ok"}

        dlg.exec()

# Or use HTML file
from qgis_sdk.ui import WebDialog

dlg = WebDialog.from_file("ui/map.html", title="Map View")
dlg.set_bridge(MyBridge())
dlg.exec()
```

**Features**:

- `WebDialog` wraps `QDialog` + `QWebEngineView` with `QWebChannel` auto-setup
- `@web_bridge` decorator registers Python object, handles `pyqtSlot` generation
- `dlg.run_js("jsCode")` → Python → JS
- `dlg.on_js("event", callback)` → JS → Python via custom signals
- HTML can use modern frameworks (React, Vue, Leaflet, MapLibre) — bundle via `qgis-plugin build` which copies `ui/` and `web/` assets
- Security: `setHtml` loads immediately, external resources async; use `baseUrl` to resolve relative URLs (images, CSS) via `QUrl.fromLocalFile`

### 2.4 Packaging considerations

- `.ui` files and HTML/CSS/JS must be included in plugin zip (hatchling `packages = ["my_plugin"]` + `ui/` folder). `qgis-plugin package` (Rust) auto-includes `ui/`, `web/`, `icons/`.
- For WebEngine, Qt WebEngine requires `QtWebEngineWidgets` and `QtWebChannel` — conda-forge `qgis` package already depends on `qt-webengine`.
- Test high-DPI with `QT_SCALE_FACTOR=2`; test WebEngine with `QT_QPA_PLATFORM=offscreen` not fully supported — need real display or `xvfb-run`.

## 3. qgis-sdk UI modules (new)

| Module | Purpose | Rust-accelerated? |
|--------|---------|-------------------|
| `qgis_sdk.ui.Dialog` | Declarative QDialog builder (fields, layouts, buttons) | Validation via `_core` |
| `qgis_sdk.ui.dialog` | `@dialog` decorator → QDialog subclass | Yes |
| `qgis_sdk.ui.field` | Field types: `text`, `spin`, `combo`, `file`, `layer`, `crs`, `check` | No |
| `qgis_sdk.ui.layout` | Layouts: `vertical`, `horizontal`, `grid`, `form`, `tabs` | No |
| `qgis_sdk.ui.WebDialog` | QDialog + QWebEngineView + QWebChannel | Yes (scaffolding) |
| `qgis_sdk.ui.web_bridge` | `@web_bridge` decorator for JS↔Python | Yes |
| `qgis_sdk.ui.Button` | Button types: `ok`, `cancel`, `apply`, `custom` | No |
| `qgis_sdk.qt` | `make_action` (existing) + `make_dialog` + `make_web_view` | Partial |

## 4. Templates (updated)

`qgis-plugin new` now scaffolds with UI examples:

- **general** type: includes `dialogs/main_dialog.py` (QDialog via `uic.loadUiType`) + `ui/main_dialog.ui` + `web/map.html` (WebEngine example)
- **processing** type: Processing UI auto-generated, plus optional custom dialog
- **--web** flag: adds `WebDialog` example with Leaflet/MapLibre + QWebChannel bridge

Generated structure:

```
my_plugin/
├── my_plugin/
│   ├── __init__.py
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── main_dialog.py      # QDialog via .ui
│   │   └── web_dialog.py       # WebDialog with HTML
│   ├── ui/
│   │   ├── main_dialog.ui      # Qt Designer file
│   │   └── main_dialog.py      # compiled (optional, runtime preferred)
│   └── web/
│       ├── map.html            # Leaflet/MapLibre example
│       ├── style.css
│       └── app.js              # QWebChannel setup
```

## 5. Testing UI without QGIS

- **Dialogs**: inject fake `QDialog` factory via `action_factory` and `dialog_factory`; test logic without Qt.
- **WebEngine**: mock `QWebEngineView` with `setHtml` capture; test bridge methods as plain Python; JS tests via `jest` + `jsdom`.

```python
def test_dialog_logic():
    from my_plugin.dialogs.main_dialog import MainDialog

    class FakeDialog:
        def __init__(self):
            self.values = {}
        def get(self, key): return self.values.get(key)
        def exec(self): return True

    MainDialog.dialog_factory = lambda: FakeDialog()
    # ... test ...
```

## 6. References

- Qt Designer workflow and `uic.loadUiType` runtime loading: [pyqgis-dialogs]
- QWebEngineView `setHtml`, `setUrl`, `load`: [qwebengine-pyqt, qt-webengine-doc]
- QWebChannel JS→Python via `pyqtSlot`, Python→JS via `runJavaScript`: [qwebchannel-stackoverflow, qwebchannel-gist]
- Built-in `qrc:///qtwebchannel/qwebchannel.js`: StackOverflow ekhumoro comment
- QGIS GUI API: `QgsDialog`, `QgsExternalResourceWidget`, `QgsHtmlWidgetWrapper`: [qgis-gui-api]
- QSettings persistence, `QgsTaskManager`, `WA_DeleteOnClose`: [pyqgis-engineering.org]

## 7. Implementation Status (implemented 2026-09-18, extended with React/Vue/WebComponents 2026-09-18)

| Feature | Module | Status |
|---------|--------|--------|
| Qt Designer .ui loading | `qgis_sdk.ui.Dialog`, `qgis_sdk.qt.make_dialog`, `qgis_sdk.scaffold.MAIN_DIALOG_UI` | ✅ Implemented — `Dialog` tries Qt then fallback, `make_dialog` uses `uic.loadUiType`, template includes `QgsMapLayerComboBox` promotion |
| Declarative dialog builder | `qgis_sdk.ui.field`, `layout`, `Button`, `FieldSpec` | ✅ Implemented — 5 field types + layer/crs, layouts vertical/horizontal/grid/form/tabs, Button ok/cancel/apply |
| QSettings persistence | `Dialog(persist=True)` | ✅ Implemented — `_restore_qsettings` / `_save_qsettings` via `QSettings`, prefix `{title}/dialog` |
| WebEngine HTML view | `qgis_sdk.ui.WebDialog` + `qgis_sdk.qt.make_web_view` | ✅ Implemented — `setHtml` with `baseUrl`, `from_file`, `setUrl`, fallback without Qt, template `web/map.html` with Leaflet |
| QWebChannel bridge | `qgis_sdk.ui.web_bridge`, `BridgeWrapper`, `run_js` | ✅ Implemented — JS→Python via `pyqtSlot(result=QVariant)` + `registerObject("bridge")`, Python→JS via `runJavaScript` with callback, built-in `qrc:///qtwebchannel/qwebchannel.js` |
| React in WebView | `scaffold.WEB_REACT_HTML` + `frontend/` Vite template | ✅ Implemented — React 18 CDN + Babel for quick demo, `useQgisBridge()` hook, `frontend/package.json` Vite + `@vitejs/plugin-react`, build to `web/dist`, `updateFromReact` + CustomEvent for Python→JS |
| Vue 3 in WebView | `scaffold.WEB_VUE_HTML` + `frontend/` Vite template | ✅ Implemented — Vue 3 CDN global prod, Composition API `ref/onMounted`, `frontend/package.json` Vite + `@vitejs/plugin-vue`, `updateFromVue` |
| Web Components | `scaffold.WEB_COMPONENTS_HTML` | ✅ Implemented — native `customElements.define`, Shadow DOM, `qgis-layer-card` + `qgis-toolbar`, no build step, best for offline QGIS, `updateFromWC` |
| `qgis-plugin new --web --framework` | CLI Python + Rust (`qgis-plugin.rs` + `cli.py`) | ✅ Implemented — `--web` flag adds `web/map.html` + `react.html` + `vue.html` + `components.html` + `dialogs/web_dialog.py`, `--framework react/vue/webcomponents/vanilla` sets index + creates `frontend/` Vite template, `--no-ui` skips UI, `ui add-dialog/add-web` subcommands |
| Packaging UI assets | `pyproject.toml` include `ui/*.ui`, `web/*.html`, `icons/*` | ✅ Implemented — hatchling include, Rust `cmd_package` notes, for React/Vue add `web/dist/*` |
| Testing UI without QGIS | `tests/test_ui.py` 22 tests + existing fake iface pattern | ✅ Implemented — 65 tests total pass (35 original + 8 CLI + 22 UI), fallback exec returns Accepted |
| Rust validation | `validate_plugin_structure` checks `qwebchannel.js` reference | ✅ Implemented — warns if HTML missing `qwebchannel` |
| Docs | `README.md`, `plugin-development.mdx`, `.knowledge/qgis-plugin-sdk.md` | ✅ Updated with React/Vue/WebComponents |

**Tests:** `PYTHONPATH=src python3 -m pytest tests/ -q` → 84 passed (65 original + 19 new bridge/testing).

**Scaffold output verified:**
- `my_ui_plugin/dialogs/main_dialog.py` contains `uic.loadUiType` + `WA_DeleteOnClose` + `QSettings`
- `my_ui_plugin/ui/main_dialog.ui` contains `MainDialog`, `QgsMapLayerComboBox`, `buttonBox`
- `my_web_plugin/web/map.html` contains `qrc:///qtwebchannel/qwebchannel.js` + `QWebChannel` + `leaflet` + `@qgis-sdk/bridge` comment
- `my_web_plugin/web/bridge.d.ts` auto-generated via `generate_ts_bridge` with Promise+callback overloads
- `my_react_plugin/web/react.html` contains React + `useQgisBridge` + `qrc:///qtwebchannel/qwebchannel.js`
- `my_react_plugin/frontend/src/App.tsx` uses `import { useQgisBridge } from '@qgis-sdk/bridge/react'` + typed `Bridge`
- `my_vue_plugin/web/vue.html` contains Vue + `ref` + `qrc:///qtwebchannel/qwebchannel.js`
- `my_vue_plugin/frontend/src/App.vue` uses `import { useQgisBridge } from '@qgis-sdk/bridge/vue'`
- `my_wc_plugin/web/components.html` contains `customElements.define` + Shadow DOM
- `ts-packages/qgis-sdk-bridge` provides `@qgis-sdk/bridge` with loader auto-injecting qrc + CDN fallbacks

### 7.2 Typed bridge with @qgis-sdk/bridge (new)

**Python → TS generation:**

```bash
qgis-plugin bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/bridge.d.ts
qgis-plugin bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/ --package
```

Inspects signatures + type hints → TS interface with Promise+callback overloads:

```typescript
export interface Bridge {
  get_layer(callback: (result: Record<string, any>) => void): void;
  get_layer(): Promise<Record<string, any>>;
  log(msg: string): Promise<string>;
}
```

**JS wrapper auto-injects qwebchannel.js:**

- Tries `QWebChannel` global already present
- `qrc:///qtwebchannel/qwebchannel.js` (Qt built-in, works in QGIS)
- `./qwebchannel.js`, `./web/qwebchannel.js`, `/qwebchannel.js`
- CDN fallback `jsdelivr/unpkg`

```typescript
import { createBridge, loadQWebChannel } from '@qgis-sdk/bridge';
import type { Bridge } from './web/bridge.d.ts';

const bridge = await createBridge<Bridge>(); // auto-injects, promisifies
const layer = await bridge.get_layer(); // typed!
```

**React hook:**

```tsx
import { useQgisBridge } from '@qgis-sdk/bridge/react';
import type { Bridge } from './bridge.d.ts';
function App() {
  const { bridge, ready } = useQgisBridge<Bridge>();
  useEffect(() => { if (ready) bridge?.get_layer().then(setLayer); }, [ready]);
}
```

**Vue composable:**

```vue
<script setup lang="ts">
import { useQgisBridge } from '@qgis-sdk/bridge/vue';
import type { Bridge } from './bridge.d.ts';
const { bridge, ready } = useQgisBridge<Bridge>();
</script>
```

**Web Components:**

```html
<qgis-bridge object-name="bridge"></qgis-bridge>
<script type="module">
import '@qgis-sdk/bridge/webcomponents';
el.addEventListener('qgis-bridge-ready', e => e.detail.bridge.get_layer().then(...));
el.addEventListener('qgis-message', e => console.log(e.detail));
</script>
```

**Python → JS messages:** `web_view.page().runJavaScript("window.qgisBridge.onMessage({message: 'hi'})")` dispatches `CustomEvent('qgis-message')` for any framework.

**npm package:** `ts-packages/qgis-sdk-bridge` → `@qgis-sdk/bridge` with `src/index.ts`, `loader.ts`, `window.ts`, `qgis.ts`, `description.ts`, `react.ts`, `vue.ts`, `svelte.ts`, `webcomponents.ts`, built via `bun build` to `dist/`.

### 7.3 Testing fixtures (new)

**`qgis_sdk.testing` exposes fakes + pytest fixtures:**

- `FakeIface`, `FakeAction`, `FakeContext`, `FakeSink`, `FakeFeature`, `FakeGeometry`, `FakeFields`
- `FakeDialog`, `FakeDialogWidget`, `FakeWebView`, `FakeWebPage`, `FakeWebChannel`, `FakeBridge`
- `mock_features(count)`, `mock_source(feature_count)`, `mock_context(values)`
- Factories: `fake_action_factory`, `fake_dialog_factory`, `fake_webview_factory`, `fake_bridge_factory`

**Fixtures discoverable via `pytest_plugins = ["qgis_sdk.testing"]` or entry point `pytest11`:**

```python
# conftest.py
pytest_plugins = ["qgis_sdk.testing"]

# test_plugin.py
def test_toolbar(fake_iface, fake_action_factory):
    from my_plugin import MyPlugin
    MyPlugin.action_factory = staticmethod(fake_action_factory)
    plugin = MyPlugin(fake_iface)
    plugin.init_gui()
    assert len(fake_iface.toolbar_icons) == 1

def test_bridge(fake_bridge):
    assert fake_bridge.get_layer()["name"] == "test_layer"

def test_dialog(fake_dialog_factory):
    dlg = fake_dialog_factory({"name": "hi"})
    assert dlg.exec() == 1
```

**Scaffolded plugins now include `tests/conftest.py` with `pytest_plugins = ["qgis_sdk.testing"]` and `test_dialog.py` testing toolbar + bridge.**

### 7.1 React / Vue / Web Components — How it fits

`QWebEngineView` is Chromium (Qt 6.8+ = Chromium 122+), so any modern frontend works. The bridge is framework-agnostic:

- **Include `qrc:///qtwebchannel/qwebchannel.js`** — always first script, provided by Qt, no bundling.
- **JS → Python**: `new QWebChannel(qt.webChannelTransport, ch => bridge=ch.objects.bridge)` then `bridge.method(args, callback)`. Methods decorated with `@pyqtSlot(result=QVariant)` or `@pyqtSlot(str, result=str)`.
- **Python → JS**: `web_view.page().runJavaScript("updateFromReact({message: 'hi'})")` or dispatch `CustomEvent('qgis-message')`.

**React example (hook):**
```javascript
function useQgisBridge() {
  const [bridge, setBridge] = useState(null);
  useEffect(() => {
    new QWebChannel(qt.webChannelTransport, ch => setBridge(ch.objects.bridge));
  }, []);
  return bridge;
}
```

**Vue example (Composition API):**
```javascript
const bridge = ref(null);
onMounted(() => {
  new QWebChannel(qt.webChannelTransport, ch => bridge.value = ch.objects.bridge);
});
```

**Web Components example:**
```javascript
class QgisLayerCard extends HTMLElement {
  setBridge(b) { this.bridge = b; this.load(); }
  load() { this.bridge.get_layer(r => this.update(JSON.parse(r))); }
}
customElements.define('qgis-layer-card', QgisLayerCard);
```

**Packaging for production:**
- Vanilla/WebComponents: no build, include `web/*.html` directly.
- React/Vue: `cd frontend && npm install && npm run build` → `web/dist/` (Vite base='./'). `WebDialog.from_file("web/dist/index.html")`. Add `web/dist/*` to `pyproject.toml` include.
- Offline QGIS: avoid CDN, bundle everything. Web Components smallest, React/Vue need Vite build.

**CLI:**
```bash
qgis-plugin new my_plugin --web --framework react   # or vue, webcomponents, vanilla
qgis-plugin new my_plugin --web                     # gets all 4 examples + Leaflet
```
