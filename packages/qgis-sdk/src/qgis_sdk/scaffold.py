"""
Pure-Python scaffolding for QGIS plugins — fallback when Rust not available.
Rust version in src_rs/lib.rs does same at native speed.

Now includes UI templates:
- dialogs/main_dialog.py + ui/main_dialog.ui (Qt Designer)
- web/map.html + dialogs/web_dialog.py when with_web=True
- web/react.html (React 18), web/vue.html (Vue 3), web/components.html (Web Components)
- frontend/ Vite templates when web_framework=react/vue
- web/bridge.d.ts auto-generated from Python Bridge + @qgis-sdk/bridge usage
- services/network.py + services/tasks.py — QgsNetworkAccessManager + QgsTaskManager wrappers
"""

from __future__ import annotations

from pathlib import Path


def to_pascal_case(s: str) -> str:
    return "".join(
        part.capitalize()
        for part in s.replace("-", "_").replace(" ", "_").split("_")
        if part
    )


# ── Templates ───────────────────────────────────────────────────────────────

MAIN_DIALOG_UI = """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainDialog</class>
 <widget class="QDialog" name="MainDialog">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>480</width>
    <height>320</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>Main Dialog</string>
  </property>
  <layout class="QVBoxLayout" name="verticalLayout">
   <item>
    <layout class="QFormLayout" name="formLayout">
     <item row="0" column="0">
      <widget class="QLabel" name="label_layer">
       <property name="text">
        <string>Input layer</string>
       </property>
      </widget>
     </item>
     <item row="0" column="1">
      <widget class="QgsMapLayerComboBox" name="input_layer">
       <property name="filters">
        <enum>QgsMapLayerProxyModel::VectorLayer</enum>
       </property>
      </widget>
     </item>
     <item row="1" column="0">
      <widget class="QLabel" name="label_threshold">
       <property name="text">
        <string>Threshold</string>
       </property>
      </widget>
     </item>
     <item row="1" column="1">
      <widget class="QDoubleSpinBox" name="threshold">
       <property name="minimum">
        <double>0.0</double>
       </property>
       <property name="maximum">
        <double>100.0</double>
       </property>
       <property name="value">
        <double>0.5</double>
       </property>
      </widget>
     </item>
     <item row="2" column="0">
      <widget class="QLabel" name="label_name">
       <property name="text">
        <string>Name</string>
       </property>
      </widget>
     </item>
     <item row="2" column="1">
      <widget class="QLineEdit" name="name_field"/>
     </item>
    </layout>
   </item>
   <item>
    <widget class="QDialogButtonBox" name="buttonBox">
     <property name="orientation">
      <enum>Qt::Horizontal</enum>
     </property>
     <property name="standardButtons">
      <set>QDialogButtonBox::Cancel|QDialogButtonBox::Ok</set>
     </property>
    </widget>
   </item>
  </layout>
 </widget>
 <customwidgets>
  <customwidget>
   <class>QgsMapLayerComboBox</class>
   <extends>QComboBox</extends>
   <header>qgsmaplayercombobox.h</header>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections>
  <connection>
   <sender>buttonBox</sender>
   <signal>accepted()</signal>
   <receiver>MainDialog</receiver>
   <slot>accept()</slot>
  </connection>
  <connection>
   <sender>buttonBox</sender>
   <signal>rejected()</signal>
   <receiver>MainDialog</receiver>
   <slot>reject()</slot>
  </connection>
 </connections>
</ui>
"""

DIALOGS_MAIN_DIALOG_PY = '''"""
Main dialog — Qt Designer .ui loading pattern (recommended by pyqgis.com).

- Uses uic.loadUiType at runtime (no pyuic5 step)
- WA_DeleteOnClose to avoid QGIS crashes
- QSettings persistence
"""

import os
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import QSettings, Qt

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "..", "ui", "main_dialog.ui")
)

class MainDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowTitle("Main Dialog")
        self._restore_settings()
        self.buttonBox.accepted.connect(self._on_accepted)

    def _restore_settings(self):
        s = QSettings()
        self.name_field.setText(s.value("{name}/main_dialog/name", "", type=str))
        self.threshold.setValue(s.value("{name}/main_dialog/threshold", 0.5, type=float))

    def _on_accepted(self):
        s = QSettings()
        s.setValue("{name}/main_dialog/name", self.name_field.text())
        s.setValue("{name}/main_dialog/threshold", self.threshold.value())

    def get_values(self):
        return {
            "input_layer": self.input_layer.currentLayer() if hasattr(self.input_layer, "currentLayer") else None,
            "threshold": self.threshold.value(),
            "name": self.name_field.text(),
        }

try:
    from qgis_sdk.ui import Dialog, field, layout, Button, dialog

    @dialog(title="Main Dialog", persist=True)
    def make_declarative_dialog():
        return [
            field.layer("input_layer", label="Input layer"),
            field.spin("threshold", label="Threshold", default=0.5, min=0.0, max=100.0),
            field.text("name", label="Name"),
        ]
except ImportError:
    make_declarative_dialog = None
'''

DIALOGS_WEB_DIALOG_PY = '''"""
Web dialog — QWebEngineView + QWebChannel bridge (Python ↔ JS).

Supports any frontend: vanilla, React, Vue, Web Components.
Uses @qgis-sdk/bridge for typed, auto-injected qwebchannel.js.

Python side: define typed Bridge, register via channel.registerObject("bridge", Bridge())
JS side: npm install @qgis-sdk/bridge, then:

    import { createBridge } from '@qgis-sdk/bridge';
    import type { Bridge } from './web/bridge.d.ts';
    const bridge = await createBridge<Bridge>();

Or legacy: <script src="qrc:///qtwebchannel/qwebchannel.js"></script> + new QWebChannel(...)

Generate types: qgis-plugin bridge generate --bridge {name}.dialogs.web_dialog:Bridge --output web/bridge.d.ts
"""

from pathlib import Path
from qgis_sdk.ui import WebDialog

HTML_FILE = Path(__file__).parent.parent / "web" / "map.html"

class MapBridge:
    """Example bridge — methods become TS via qgis-plugin bridge generate."""
    def get_layer(self) -> dict:
        import json
        return {"name": "buildings", "count": 100}

    def get_extent(self) -> dict:
        return {"xmin": -180, "ymin": -90, "xmax": 180, "ymax": 90}

    def log(self, msg: str) -> str:
        print(f"[JS] {msg}")
        return "ok"

    def process(self, data: str) -> dict:
        import json
        try:
            parsed = json.loads(data)
            return {"status": "ok", "action": parsed.get("action", "unknown")}
        except Exception:
            return {"status": "ok", "data": data}

def show_web_dialog(parent=None, html_file=None):
    # html_file can be map.html, react.html, vue.html, components.html, or dist/index.html
    target = Path(html_file) if html_file else HTML_FILE
    dlg = WebDialog.from_file(target, title="Map View", width=900, height=700, parent=parent)
    dlg.set_bridge(MapBridge())
    return dlg.exec()

try:
    from qgis_sdk.ui import web_bridge
    web_dlg = WebDialog.from_file(HTML_FILE, title="Map View", width=900, height=700)

    @web_bridge(web_dlg)
    class Bridge:
        def get_layer(self) -> dict:
            return {"name": "buildings", "count": 100}
        def get_extent(self) -> dict:
            return {"xmin": -180, "ymin": -90, "xmax": 180, "ymax": 90}
        def log(self, msg: str) -> str:
            print(f"[JS] {msg}")
            return "ok"

except ImportError:
    web_dlg = None
    Bridge = None
'''

SERVICES_NETWORK_PY = '''"""
Network service — requests-like wrapper around QgsNetworkAccessManager.

Uses qgis_sdk.network which respects QGIS proxy, cache, and auth infrastructure.
Falls back to urllib for testing without QGIS.
API mirrors Python requests: get/post/put/patch/delete, Session, params, json, etc.

Example:
    from .services.network import fetch_geojson, download_file, get_session

    # requests-like
    import qgis_sdk.network as requests
    resp = requests.get("https://example.com/data.geojson", params={"limit": 10})
    resp.raise_for_status()
    data = resp.json()

    data = fetch_geojson("https://example.com/data.geojson", auth_cfg="my_auth_id")
    path = download_file("https://example.com/file.zip", "/tmp/file.zip")

    # Session keeps auth_cfg, headers, timeout
    session = get_session(auth_cfg="my_auth", headers={"User-Agent": "MyPlugin/1.0"})
    resp = session.get("https://example.com/secure")
"""

from pathlib import Path
from typing import Union, Dict, Any

try:
    from qgis_sdk.network import (
        NetworkManager,
        NetworkAccessManager,
        Session,
        fetch_json,
        download,
        RequestException,
        get as http_get,
    )

    def get_session(auth_cfg: str | None = None, headers: Dict[str, str] | None = None) -> Session:
        """Create Session that respects QGIS proxy/cache/auth — requests-like."""
        return Session(auth_cfg=auth_cfg, headers=headers or {"User-Agent": "MyPlugin/1.0"})

    def fetch_geojson(url: str, params: Dict[str, Any] | None = None, auth_cfg: str | None = None) -> dict:
        """Fetch GeoJSON with QGIS auth support — requests-like params."""
        # requests-like: get with params
        resp = http_get(url, params=params, auth_cfg=auth_cfg)
        resp.raise_for_status()
        return resp.json()

    def fetch_with_auth(url: str, auth_cfg: str) -> tuple:
        """Fetch with auth, returns (response, content) — QGIS cookbook pattern."""
        http = NetworkAccessManager(auth_cfg=auth_cfg, timeout=15000)
        try:
            response, content = http.request(url)
            return response, content
        except RequestException as e:
            print(f"Network error: {e}")
            raise

    def download_file(url: str, dest: Union[str, Path], progress_callback=None, params=None) -> Path:
        """Download file with progress, respects QGIS proxy/auth — requests-like params."""
        return download(url, dest, progress_callback=progress_callback, params=params)

    # requests-like shortcuts
    def get(url: str, params=None, **kwargs):
        return http_get(url, params=params, **kwargs)

except ImportError:
    def fetch_geojson(url: str, params=None, auth_cfg: str | None = None) -> dict:
        import urllib.request, json
        from urllib.parse import urlencode

        full_url = url
        if params:
            full_url = f"{url}?{urlencode(params, doseq=True)}"
        with urllib.request.urlopen(full_url) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def download_file(url: str, dest: Union[str, Path], progress_callback=None, params=None) -> Path:
        import urllib.request

        dest = Path(dest)
        urllib.request.urlretrieve(url, dest)
        return dest

    def fetch_with_auth(url: str, auth_cfg: str) -> tuple:
        return fetch_geojson(url), b""

    def get_session(auth_cfg=None, headers=None):
        return None

    def get(url: str, params=None, **kwargs):
        return fetch_geojson(url, params=params)
'''

SERVICES_TASKS_PY = '''"""
Tasks service — Celery-like wrapper around QgsTaskManager and QgsTask.

Uses qgis_sdk.tasks which uses QgsApplication.taskManager() when QGIS available,
falls back to ThreadPoolExecutor for testing without QGIS.
API mirrors Celery: @task, delay(), apply_async(), get(), ready(), etc.

Example:
    from .services.tasks import run_heavy_task, my_background_task, add

    # Celery-like — sync direct call
    result = add(4, 4)  # 8

    # Async via delay — returns AsyncResult
    async_result = add.delay(4, 4)
    print(async_result.get())  # 8
    print(async_result.ready(), async_result.state)

    # Task with progress
    def on_finished(exception, result):
        if exception is None:
            iface.messageBar().pushMessage(f"Task completed: {result}")

    run_heavy_task(wait_time=2, on_finished=on_finished)

    # Signature / chain
    sig = add.s(2, 2)
    result = sig.delay()
    chain = (add.s(2, 2) | add.s(3))  # 2+2=4, 4+3=7
    result = chain()

    # Processing alg in background
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    run_processing_task("qgis:buffer", {"INPUT": layer, "DISTANCE": 10, "OUTPUT": "memory:"}, context, feedback)
"""

from typing import Callable, Dict, Any

try:
    from qgis_sdk.tasks import TaskManager, Task, task, shared_task, run_task, ProcessingAlgRunnerTask, chain, group
    from qgis.core import QgsApplication, QgsTask

    @task("Add", bind=False)
    def add(x, y=0):
        """Simple task — celery-like, no bind."""
        return x + y

    def run_heavy_task(wait_time: int = 2, on_finished: Callable | None = None):
        """Run heavy work in background without freezing UI — celery-like."""

        @task(f"Heavy work {wait_time}s", bind=True, can_cancel=True)
        def do_work(self, wait_time):
            from time import sleep
            for i in range(100):
                sleep(wait_time / 100.0)
                self.set_progress(i)
                if self.is_canceled():
                    return None
            return {"result": 42, "message": f"Completed after {wait_time}s"}

        # Celery-like delay
        async_result = do_work.apply_async(args=(wait_time,), on_finished=on_finished)
        return async_result

    @task("My background task", bind=True, can_cancel=True)
    def my_background_task(self, value: int = 10):
        """Example task using decorator — celery-like with bind=True."""
        from time import sleep
        for i in range(100):
            sleep(0.01)
            self.set_progress(i)
            if self.is_canceled():
                return None
        return value * 2

    # Example: using delay
    # result = my_background_task.delay(42)
    # print(result.get())

    def run_processing_task(alg_id: str, params: Dict[str, Any], context: Any, feedback: Any, on_executed: Callable | None = None):
        """Run processing algorithm in background — with celery-like delay."""
        try:
            from qgis.core import QgsApplication
            alg = QgsApplication.processingRegistry().algorithmById(alg_id)
            if alg is None:
                raise ValueError(f"Algorithm not found: {alg_id}")

            task_obj = ProcessingAlgRunnerTask(alg, params, context, feedback)

            def task_finished(successful, results):
                if successful:
                    print(f"Processing task completed: {results}")
                else:
                    print("Processing task failed")
                if on_executed:
                    on_executed(successful, results)

            task_obj.qgis_task.executed.connect(task_finished)
            QgsApplication.taskManager().addTask(task_obj.qgis_task)
            return task_obj
        except ImportError:
            print(f"[Fallback] Would run {alg_id} with {params}")
            if on_executed:
                on_executed(True, params)
            return None

except ImportError:
    def run_heavy_task(wait_time: int = 2, on_finished: Callable | None = None):
        print(f"[Fallback] Would run heavy task {wait_time}s")
        if on_finished:
            on_finished(None, {"result": 42})
        return None

    def add(x, y=0):
        return x + y

    def my_background_task(self=None, value: int = 10):
        return value * 2

    def run_processing_task(alg_id: str, params: Dict[str, Any], context: Any, feedback: Any, on_executed: Callable | None = None):
        print(f"[Fallback] Would run {alg_id}")
        if on_executed:
            on_executed(True, params)
        return None
'''

WEB_MAP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>QGIS Web View</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
  html, body { height: 100%; margin: 0; padding: 0; font-family: sans-serif; }
  #map { height: 85%; }
  #info { padding: 8px; background: #f5f5f5; }
  button { margin: 4px; padding: 6px 12px; }
  code { background: #eee; padding: 2px 4px; border-radius: 3px; }
</style>
</head>
<body>
<div id="info">
  <strong id="layer-name">Loading...</strong>
  <button onclick="sendToPython()">Send to Python</button>
  <button onclick="requestExtent()">Get Extent</button>
  <small>Using <code>qrc:///qtwebchannel/qwebchannel.js</code> — or <code>npm install @qgis-sdk/bridge</code> for typed Promise API</small>
</div>
<div id="map"></div>
<script type="module">
  var bridge = null;
  var map = L.map('map').setView([51.505, -0.09], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
  new QWebChannel(qt.webChannelTransport, function(channel) {
    bridge = channel.objects.bridge;
    if (bridge) {
      bridge.get_layer(function(result) {
        try {
          var data = typeof result === 'string' ? JSON.parse(result) : result;
          document.getElementById('layer-name').innerText = "Layer: " + data.name + " (" + data.count + " features)";
        } catch(e) {
          document.getElementById('layer-name').innerText = "Layer: " + result;
        }
      });
    }
  });
  window.sendToPython = function() {
    if (bridge && bridge.log) bridge.log("Hello from JS at " + new Date().toISOString(), function(reply){ console.log(reply); });
  }
  window.requestExtent = function() {
    if (bridge && bridge.get_extent) {
      bridge.get_extent(function(extent) {
        try { var e = typeof extent === 'string' ? JSON.parse(extent) : extent; map.fitBounds([[e.ymin, e.xmin], [e.ymax, e.xmax]]); } catch(err){}
      });
    }
  }
  window.addEventListener('qgis-message', (e) => {
    const info = e.detail;
    if (info.center) map.setView(info.center, info.zoom || 13);
    if (info.message) document.getElementById('layer-name').innerText = info.message;
  });
  window.updateFromPython = function(data) {
    const info = typeof data === 'string' ? JSON.parse(data) : data;
    window.dispatchEvent(new CustomEvent('qgis-message', { detail: info }));
  }
</script>
</body>
</html>
"""

WEB_REACT_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>QGIS + React</title>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<style>
  html, body { margin:0; padding:0; font-family: sans-serif; height:100%; }
  #root { height:100%; display:flex; flex-direction:column; }
  .header { padding:12px; background:#f5f5f5; border-bottom:1px solid #ddd; }
  .content { flex:1; padding:16px; overflow:auto; }
  button { margin:4px; padding:8px 16px; background:#0078d4; color:white; border:none; border-radius:4px; cursor:pointer; }
  .layer-card { border:1px solid #ddd; border-radius:8px; padding:12px; margin:8px 0; }
  code { background:#eee; padding:2px 4px; border-radius:3px; }
</style>
</head>
<body>
<div id="root"></div>
<script type="text/babel">
const { useState, useEffect } = React;
function useQgisBridge() {
  const [bridge, setBridge] = useState(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    new QWebChannel(qt.webChannelTransport, (channel) => {
      setBridge(channel.objects.bridge);
      setReady(true);
    });
    const handler = (e) => console.log('from Python', e.detail);
    window.addEventListener('qgis-message', handler);
    return () => window.removeEventListener('qgis-message', handler);
  }, []);
  return { bridge, ready };
}
function App() {
  const { bridge, ready } = useQgisBridge();
  const [layer, setLayer] = useState(null);
  const [count, setCount] = useState(0);
  const loadLayer = () => {
    if (!bridge) return;
    bridge.get_layer((result) => {
      try { const data = typeof result === 'string' ? JSON.parse(result) : result; setLayer(data); }
      catch(e) { setLayer({name: result}); }
    });
  };
  useEffect(() => { if (ready) loadLayer(); }, [ready]);
  const sendToPython = () => {
    if (bridge && bridge.log) {
      bridge.log(`Hello from React at ${new Date().toISOString()}`, (reply) => { console.log(reply); setCount(c=>c+1); });
    }
  };
  if (!ready) return <div className="header">Connecting to QGIS... (tip: <code>npm install @qgis-sdk/bridge</code> for typed <code>useQgisBridge&lt;Bridge&gt;</code>)</div>;
  return (
    <>
      <div className="header"><h2 style={{margin:0}}>QGIS + React</h2><small>Bridge: {ready ? "connected" : "connecting"} | Calls: {count} | <code>bridge.d.ts</code> generated via <code>qgis-plugin bridge generate</code></small></div>
      <div className="content">
        <div className="layer-card"><h3>Layer Info</h3><p><strong>Name:</strong> {layer ? layer.name : "Loading..."}</p><p><strong>Features:</strong> {layer ? layer.count : "-"}</p><button onClick={loadLayer}>Reload</button><button onClick={sendToPython}>Send to Python</button></div>
      </div>
    </>
  );
}
window.updateFromReact = (data) => { window.dispatchEvent(new CustomEvent('qgis-message', {detail: typeof data === 'string' ? JSON.parse(data) : data})); };
window.qgisBridge = window.qgisBridge || {};
window.qgisBridge.onMessage = window.updateFromReact;
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
</script>
</body>
</html>
"""

WEB_VUE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>QGIS + Vue</title>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
<style>
  html, body { margin:0; padding:0; font-family: sans-serif; height:100%; }
  #app { height:100%; display:flex; flex-direction:column; }
  .header { padding:12px; background:#f5f5f5; border-bottom:1px solid #ddd; }
  .content { flex:1; padding:16px; overflow:auto; }
  button { margin:4px; padding:8px 16px; background:#42b883; color:white; border:none; border-radius:4px; cursor:pointer; }
  .card { border:1px solid #ddd; border-radius:8px; padding:12px; margin:8px 0; }
  code { background:#eee; padding:2px 4px; border-radius:3px; }
</style>
</head>
<body>
<div id="app">
  <div class="header"><h2 style="margin:0">QGIS + Vue 3</h2><small>Bridge: {{ ready ? 'connected' : 'connecting' }} | Calls: {{ callCount }}</small></div>
  <div class="content">
    <div class="card"><h3>Layer Info</h3><p><strong>Name:</strong> {{ layer ? layer.name : 'Loading...' }}</p><p><strong>Features:</strong> {{ layer ? layer.count : '-' }}</p><button @click="loadLayer">Reload</button><button @click="sendToPython">Send to Python</button></div>
    <div class="card"><p v-if="message"><strong>From Python:</strong> {{ message }}</p></div>
  </div>
</div>
<script>
const { createApp, ref, onMounted } = Vue;
createApp({
  setup() {
    const bridge = ref(null); const ready = ref(false); const layer = ref(null); const callCount = ref(0); const message = ref('');
    const loadLayer = () => {
      if (!bridge.value) return;
      bridge.value.get_layer((result) => {
        try { layer.value = typeof result === 'string' ? JSON.parse(result) : result; }
        catch(e) { layer.value = {name: result}; }
      });
    };
    const sendToPython = () => {
      if (bridge.value && bridge.value.log) bridge.value.log(`Hello from Vue`, (reply) => { callCount.value++; });
    };
    onMounted(() => {
      new QWebChannel(qt.webChannelTransport, (channel) => { bridge.value = channel.objects.bridge; ready.value = true; loadLayer(); });
      window.updateFromVue = (data) => { const info = typeof data === 'string' ? JSON.parse(data) : data; message.value = info.message || JSON.stringify(info); window.dispatchEvent(new CustomEvent('qgis-message', {detail: info})); };
      window.qgisBridge = window.qgisBridge || {};
      window.qgisBridge.onMessage = window.updateFromVue;
      window.addEventListener('qgis-message', (e) => { message.value = e.detail.message || JSON.stringify(e.detail); });
    });
    return { bridge, ready, layer, callCount, message, loadLayer, sendToPython };
  }
}).mount('#app');
</script>
</body>
</html>
"""

WEB_COMPONENTS_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>QGIS + Web Components</title>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
  html, body { margin:0; padding:0; font-family: sans-serif; height:100%; }
  .header { padding:12px; background:#f5f5f5; border-bottom:1px solid #ddd; }
  .content { padding:16px; }
  button { margin:4px; padding:8px 16px; background:#6f42c1; color:white; border:none; border-radius:4px; cursor:pointer; }
  code { background:#eee; padding:2px 4px; border-radius:3px; }
</style>
</head>
<body>
<div class="header"><h2 style="margin:0">QGIS + Web Components</h2><small id="status">Connecting...</small></div>
<div class="content">
  <qgis-layer-card id="layerCard"></qgis-layer-card>
  <qgis-toolbar id="toolbar"></qgis-toolbar>
</div>
<script>
class QgisLayerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: 'open'});
    this.shadowRoot.innerHTML = `<style>.card{border:1px solid #ddd;border-radius:8px;padding:12px;}button{margin:4px;padding:6px 12px;background:#0078d4;color:white;border:none;border-radius:4px;}</style><div class="card"><h3>Layer Info</h3><p>Name: <span id="name">Loading...</span></p><p>Count: <span id="count">-</span></p><button id="reload">Reload</button><button id="send">Send to Python</button></div>`;
  }
  connectedCallback() {
    this.shadowRoot.getElementById('reload').addEventListener('click', () => this.load());
    this.shadowRoot.getElementById('send').addEventListener('click', () => this.send());
  }
  setBridge(b){ this.bridge=b; this.load(); }
  load(){ if(!this.bridge) return; this.bridge.get_layer((r)=>{ try{ const d=typeof r==='string'?JSON.parse(r):r; this.update(d);} catch(e){ this.shadowRoot.getElementById('name').textContent=r; } }); }
  send(){ if(this.bridge && this.bridge.log) this.bridge.log(`Hello from WC`, (reply)=>console.log(reply)); }
  update(d){ this.shadowRoot.getElementById('name').textContent=d.name||'-'; this.shadowRoot.getElementById('count').textContent=d.count||'-'; }
}
customElements.define('qgis-layer-card', QgisLayerCard);
class QgisToolbar extends HTMLElement {
  constructor(){ super(); this.attachShadow({mode:'open'}); this.shadowRoot.innerHTML=`<style>.toolbar{display:flex;gap:8px;padding:8px;background:#f0f0f0;border-radius:4px;}</style><div class="toolbar"><button id="buffer">Buffer</button><button id="clip">Clip</button><button id="extent">Get Extent</button></div>`; }
  connectedCallback(){ this.shadowRoot.getElementById('buffer').addEventListener('click', ()=>this.dispatch('buffer')); this.shadowRoot.getElementById('clip').addEventListener('click', ()=>this.dispatch('clip')); this.shadowRoot.getElementById('extent').addEventListener('click', ()=>this.dispatch('extent')); }
  setBridge(b){ this.bridge=b; }
  dispatch(a){ if(this.bridge && this.bridge.process) this.bridge.process(JSON.stringify({action:a}), (res)=>console.log(res)); this.dispatchEvent(new CustomEvent('qgis-action',{detail:{action:a},bubbles:true,composed:true})); }
}
customElements.define('qgis-toolbar', QgisToolbar);
let bridge=null;
new QWebChannel(qt.webChannelTransport, (channel)=>{ bridge=channel.objects.bridge; document.getElementById('status').textContent='Bridge connected'; document.getElementById('layerCard').setBridge(bridge); document.getElementById('toolbar').setBridge(bridge); });
window.updateFromWC=(data)=>{ const info=typeof data==='string'?JSON.parse(data):data; document.getElementById('layerCard').update(info); window.dispatchEvent(new CustomEvent('qgis-message', {detail: info})); };
window.qgisBridge = window.qgisBridge || {};
window.qgisBridge.onMessage = window.updateFromWC;
</script>
</body>
</html>
"""

DIALOGS_INIT_PY = '''"""Dialogs package."""

from .main_dialog import MainDialog, make_declarative_dialog

try:
    from .web_dialog import show_web_dialog, web_dlg, Bridge
    __all__ = ["MainDialog", "make_declarative_dialog", "show_web_dialog", "web_dlg", "Bridge"]
except ImportError:
    __all__ = ["MainDialog", "make_declarative_dialog"]
'''


def _generate_bridge_dts(web_dir: Path, plugin_package_name: str):
    """Generate bridge.d.ts from a sample Bridge class for scaffolded plugins."""
    try:
        from .bridge import generate_ts_bridge

        class SampleBridge:
            def get_layer(self) -> dict:
                return {"name": "buildings", "count": 100}

            def get_extent(self) -> dict:
                return {"xmin": -180, "ymin": -90, "xmax": 180, "ymax": 90}

            def log(self, msg: str) -> str:
                return "ok"

            def process(self, data: str) -> dict:
                return {"status": "ok"}

        ts_code = generate_ts_bridge(SampleBridge, name="Bridge")
        (web_dir / "bridge.d.ts").write_text(ts_code, encoding="utf-8")

        wrapper = f"""/**
 * Bridge usage with @qgis-sdk/bridge
 * Auto-generated by qgis-sdk scaffold — regenerate via:
 *   qgis-plugin bridge generate --bridge {plugin_package_name}.dialogs.web_dialog:Bridge --output web/bridge.d.ts
 *   qgis-plugin bridge generate --bridge {plugin_package_name}.dialogs.web_dialog:Bridge --output web/ --package
 *
 * Install: npm install @qgis-sdk/bridge
 */

// Vanilla JS / TS
// import {{ createBridge }} from '@qgis-sdk/bridge';
// import type {{ Bridge }} from './bridge.d.ts';
// const bridge = await createBridge<Bridge>();

// React
// import {{ useQgisBridge }} from '@qgis-sdk/bridge/react';
// import type {{ Bridge }} from './bridge.d.ts';
// const {{ bridge, ready }} = useQgisBridge<Bridge>();

// Vue
// import {{ useQgisBridge }} from '@qgis-sdk/bridge/vue';
// const {{ bridge, ready }} = useQgisBridge<Bridge>();

// Web Components
// import '@qgis-sdk/bridge/webcomponents';
// <qgis-bridge object-name="bridge"></qgis-bridge>

export type {{ Bridge }} from './bridge.d.ts';
"""
        (web_dir / "bridge.ts").write_text(wrapper, encoding="utf-8")

    except Exception:
        (web_dir / "bridge.d.ts").write_text(
            """/**
 * Auto-generated Bridge interface — fallback
 * Regenerate via: qgis-plugin bridge generate --bridge my_plugin.dialogs.web_dialog:Bridge --output web/bridge.d.ts
 */
export interface Bridge {
  get_layer(callback: (result: any) => void): void;
  get_layer(): Promise<any>;
  get_extent(callback: (result: any) => void): void;
  get_extent(): Promise<any>;
  log(msg: string, callback: (result: string) => void): void;
  log(msg: string): Promise<string>;
  process(data: string, callback: (result: any) => void): void;
  process(data: string): Promise<any>;
}
""",
            encoding="utf-8",
        )


def scaffold_plugin(
    name: str,
    path: str,
    plugin_type: str = "general",
    with_rust: bool = False,
    with_web: bool = False,
    with_ui: bool = True,
    web_framework: str = "vanilla",
    author: str | None = None,
    email: str | None = None,
) -> str:
    base = Path(path) / name

    if base.exists():
        raise ValueError(f"directory already exists: {base}")

    base.mkdir(parents=True)
    (base / name).mkdir()

    class_name = to_pascal_case(name)
    author = author or "Your Name"
    email = email or "you@example.com"

    if with_web:
        init_py = f'''"""{name} — QGIS plugin with UI + WebEngine (React/Vue/Web Components) + @qgis-sdk/bridge + network + tasks."""

from qgis_sdk import Plugin, action, toolbar

class {class_name}Plugin(Plugin):
    name = "{name}"
    version = "0.1.0"
    description = "Does useful things — with dialogs, web view (React/Vue/WebComponents), typed bridge, network, tasks"
    author = "{author}"
    email = "{email}"
    qgis_min_version = "3.28"
    category = "Vector"

    @toolbar("{name} Toolbar")
    @action(tooltip="Run {name}")
    def run(self, iface):
        try:
            from .dialogs.main_dialog import MainDialog
            dlg = MainDialog(parent=iface.mainWindow())
            if dlg.exec() == MainDialog.Accepted:
                vals = dlg.get_values()
                iface.messageBar().pushMessage(f"{{name}}: {{vals}}")
        except Exception:
            try:
                from .dialogs.main_dialog import make_declarative_dialog
                if make_declarative_dialog:
                    dlg = make_declarative_dialog()
                    if dlg.exec() == 1:
                        iface.messageBar().pushMessage("Hello from {name}! (declarative)")
                else:
                    iface.messageBar().pushMessage("Hello from {name}!")
            except Exception:
                iface.messageBar().pushMessage("Hello from {name}!")

    @toolbar("{name} Toolbar")
    @action(tooltip="Open web map")
    def open_web(self, iface):
        try:
            from .dialogs.web_dialog import show_web_dialog
            show_web_dialog(parent=iface.mainWindow())
        except Exception as e:
            iface.messageBar().pushMessage(f"Web view requires QWebEngine: {{e}}")

    @toolbar("{name} Toolbar")
    @action(tooltip="Fetch data via QgsNetworkAccessManager")
    def fetch_data(self, iface):
        try:
            from .services.network import fetch_geojson, download_file
            # Respects QGIS proxy, cache, auth infrastructure
            data = fetch_geojson("https://example.com/data.geojson")
            iface.messageBar().pushMessage(f"Fetched {{len(data)}} features")
        except Exception as e:
            iface.messageBar().pushMessage(f"Network error: {{e}}")

    @toolbar("{name} Toolbar")
    @action(tooltip="Run background task via QgsTaskManager")
    def run_background_task(self, iface):
        try:
            from .services.tasks import run_heavy_task
            def on_finished(exception, result):
                if exception is None:
                    iface.messageBar().pushMessage(f"Task completed: {{result}}")
                else:
                    iface.messageBar().pushMessage(f"Task failed: {{exception}}")
            run_heavy_task(wait_time=2, on_finished=on_finished)
            iface.messageBar().pushMessage("Task started in background")
        except Exception as e:
            iface.messageBar().pushMessage(f"Task error: {{e}}")

def classFactory(iface):
    return {class_name}Plugin(iface)
'''
    else:
        init_py = f'''"""{name} — QGIS plugin with UI dialogs + network + tasks."""

from qgis_sdk import Plugin, action, toolbar

class {class_name}Plugin(Plugin):
    name = "{name}"
    version = "0.1.0"
    description = "Does useful things — with dialogs, network, tasks"
    author = "{author}"
    email = "{email}"
    qgis_min_version = "3.28"
    category = "Vector"

    @toolbar("{name} Toolbar")
    @action(tooltip="Run {name}")
    def run(self, iface):
        try:
            from .dialogs.main_dialog import MainDialog
            dlg = MainDialog(parent=iface.mainWindow())
            if dlg.exec() == MainDialog.Accepted:
                vals = dlg.get_values()
                iface.messageBar().pushMessage(f"{{name}}: {{vals}}")
        except Exception:
            try:
                from .dialogs.main_dialog import make_declarative_dialog
                if make_declarative_dialog:
                    dlg = make_declarative_dialog()
                    if dlg.exec() == 1:
                        iface.messageBar().pushMessage("Hello from {name}! (declarative)")
                else:
                    iface.messageBar().pushMessage("Hello from {name}!")
            except Exception:
                iface.messageBar().pushMessage("Hello from {name}!")

    @toolbar("{name} Toolbar")
    @action(tooltip="Fetch data via QgsNetworkAccessManager")
    def fetch_data(self, iface):
        try:
            from .services.network import fetch_geojson
            data = fetch_geojson("https://example.com/data.geojson")
            iface.messageBar().pushMessage(f"Fetched {{len(data)}} features")
        except Exception as e:
            iface.messageBar().pushMessage(f"Network error: {{e}}")

    @toolbar("{name} Toolbar")
    @action(tooltip="Run background task via QgsTaskManager")
    def run_background_task(self, iface):
        try:
            from .services.tasks import run_heavy_task
            def on_finished(exception, result):
                if exception is None:
                    iface.messageBar().pushMessage(f"Task completed: {{result}}")
                else:
                    iface.messageBar().pushMessage(f"Task failed: {{exception}}")
            run_heavy_task(wait_time=2, on_finished=on_finished)
            iface.messageBar().pushMessage("Task started in background")
        except Exception as e:
            iface.messageBar().pushMessage(f"Task error: {{e}}")

def classFactory(iface):
    return {class_name}Plugin(iface)
'''

    (base / name / "__init__.py").write_text(init_py, encoding="utf-8")

    if with_ui:
        dialogs_dir = base / name / "dialogs"
        dialogs_dir.mkdir()
        (dialogs_dir / "__init__.py").write_text(DIALOGS_INIT_PY.format(name=name), encoding="utf-8")
        (dialogs_dir / "main_dialog.py").write_text(DIALOGS_MAIN_DIALOG_PY.replace("{name}", name), encoding="utf-8")
        if with_web:
            (dialogs_dir / "web_dialog.py").write_text(DIALOGS_WEB_DIALOG_PY.replace("{name}", name), encoding="utf-8")

        ui_dir = base / name / "ui"
        ui_dir.mkdir()
        (ui_dir / "__init__.py").write_text("", encoding="utf-8")
        (ui_dir / "main_dialog.ui").write_text(MAIN_DIALOG_UI, encoding="utf-8")

        icons_dir = base / name / "icons"
        icons_dir.mkdir()
        (icons_dir / ".gitkeep").write_text("", encoding="utf-8")

    # Always create services with network + tasks examples
    services_dir = base / name / "services"
    services_dir.mkdir()
    (services_dir / "__init__.py").write_text("", encoding="utf-8")
    (services_dir / "network.py").write_text(SERVICES_NETWORK_PY, encoding="utf-8")
    (services_dir / "tasks.py").write_text(SERVICES_TASKS_PY, encoding="utf-8")

    if with_web:
        web_dir = base / name / "web"
        web_dir.mkdir()
        if web_framework == "react":
            (web_dir / "map.html").write_text(WEB_MAP_HTML, encoding="utf-8")
            (web_dir / "react.html").write_text(WEB_REACT_HTML, encoding="utf-8")
            (web_dir / "index.html").write_text(WEB_REACT_HTML, encoding="utf-8")
        elif web_framework == "vue":
            (web_dir / "map.html").write_text(WEB_MAP_HTML, encoding="utf-8")
            (web_dir / "vue.html").write_text(WEB_VUE_HTML, encoding="utf-8")
            (web_dir / "index.html").write_text(WEB_VUE_HTML, encoding="utf-8")
        elif web_framework == "webcomponents":
            (web_dir / "map.html").write_text(WEB_MAP_HTML, encoding="utf-8")
            (web_dir / "components.html").write_text(WEB_COMPONENTS_HTML, encoding="utf-8")
            (web_dir / "index.html").write_text(WEB_COMPONENTS_HTML, encoding="utf-8")
        else:
            (web_dir / "map.html").write_text(WEB_MAP_HTML, encoding="utf-8")
            (web_dir / "react.html").write_text(WEB_REACT_HTML, encoding="utf-8")
            (web_dir / "vue.html").write_text(WEB_VUE_HTML, encoding="utf-8")
            (web_dir / "components.html").write_text(WEB_COMPONENTS_HTML, encoding="utf-8")
        (web_dir / "__init__.py").write_text("", encoding="utf-8")

        _generate_bridge_dts(web_dir, name)

        if web_framework in ("react", "vue"):
            frontend_dir = base / name / "frontend"
            frontend_dir.mkdir()
            if web_framework == "react":
                (frontend_dir / "package.json").write_text(
                    """{
  "name": "%s-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build --outDir ../%s/web/dist",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@qgis-sdk/bridge": "^0.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0",
    "typescript": "^5.4.0"
  }
}
""" % (name, name),
                    encoding="utf-8",
                )
                (frontend_dir / "vite.config.js").write_text(
                    """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], base: './' });
""",
                    encoding="utf-8",
                )
                (frontend_dir / "tsconfig.json").write_text(
                    """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ES2020",
    "moduleResolution": "node",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
""",
                    encoding="utf-8",
                )
                src_dir = frontend_dir / "src"
                src_dir.mkdir()
                (src_dir / "App.tsx").write_text(
                    f"""import {{ useEffect, useState }} from 'react';
import {{ useQgisBridge }} from '@qgis-sdk/bridge/react';
import type {{ Bridge }} from '../../web/bridge.d.ts';

export default function App() {{
  const {{ bridge, ready, error }} = useQgisBridge<Bridge>();
  const [layer, setLayer] = useState<any>(null);

  useEffect(() => {{
    if (ready && bridge) {{
      bridge.get_layer().then(setLayer).catch(console.error);
    }}
  }}, [ready, bridge]);

  if (error) return <div>Error: {{error.message}}</div>;
  if (!ready) return <div>Connecting to QGIS... (bridge auto-injects qrc:///qtwebchannel/qwebchannel.js)</div>;

  return (
    <div style={{{{ padding: 16 }}}}>\
      <h2>{name} — React + @qgis-sdk/bridge</h2>
      <p>Layer: {{layer?.name}} ({{layer?.count}})</p>
      <button onClick={{() => bridge?.log("hello from React")}}>Send to Python</button>
    </div>
  );
}}
""",
                    encoding="utf-8",
                )
                (src_dir / "main.tsx").write_text(
                    """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
ReactDOM.createRoot(document.getElementById('root')!).render(<App />);
""",
                    encoding="utf-8",
                )
                (frontend_dir / "index.html").write_text(
                    """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/><title>QGIS + React</title></head>
<body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
""",
                    encoding="utf-8",
                )
            elif web_framework == "vue":
                (frontend_dir / "package.json").write_text(
                    """{
  "name": "%s-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build --outDir ../%s/web/dist",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "@qgis-sdk/bridge": "^0.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "typescript": "^5.4.0"
  }
}
""" % (name, name),
                    encoding="utf-8",
                )
                (frontend_dir / "vite.config.js").write_text(
                    """import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({ plugins: [vue()], base: './' });
""",
                    encoding="utf-8",
                )
                (frontend_dir / "tsconfig.json").write_text(
                    """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ES2020",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
""",
                    encoding="utf-8",
                )
                src_dir = frontend_dir / "src"
                src_dir.mkdir()
                (src_dir / "App.vue").write_text(
                    f"""<script setup lang="ts">
import {{ ref, watch }} from 'vue';
import {{ useQgisBridge }} from '@qgis-sdk/bridge/vue';
import type {{ Bridge }} from '../../web/bridge.d.ts';

const {{ bridge, ready }} = useQgisBridge<Bridge>();
const layer = ref<any>(null);

watch(ready, async (r) => {{
  if (r && bridge.value) {{
    layer.value = await bridge.value.get_layer();
  }}
}});
</script>

<template>
  <div style="padding:16px">
    <h2>{name} — Vue + @qgis-sdk/bridge</h2>
    <div v-if="!ready">Connecting to QGIS... (auto-injects qrc:///qtwebchannel/qwebchannel.js)</div>
    <div v-else>
      <p>Layer: {{{{ layer?.name }}}} ({{{{ layer?.count }}}})</p>
      <button @click="bridge?.value?.log('hello from Vue')">Send to Python</button>
    </div>
  </div>
</template>
""",
                    encoding="utf-8",
                )
                (src_dir / "main.ts").write_text(
                    """import { createApp } from 'vue';
import App from './App.vue';
createApp(App).mount('#app');
""",
                    encoding="utf-8",
                )
                (frontend_dir / "index.html").write_text(
                    """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"/><title>QGIS + Vue</title></head>
<body><div id="app"></div><script type="module" src="/src/main.ts"></script></body>
</html>
""",
                    encoding="utf-8",
                )

    metadata = f"""[general]
name={name}
qgisMinimumVersion=3.28
description=Does useful things
about=Does useful things
version=0.1.0
author={author}
email={email}
category=Vector
hasProcessingProvider={"True" if plugin_type == "processing" else "False"}
"""

    (base / "metadata.txt").write_text(metadata, encoding="utf-8")

    readme = f"""# {name}

QGIS plugin built with qgis-sdk — with UI dialogs, WebEngine (React/Vue/Web Components), typed bridge, network, tasks.

## Features

- **Dialogs via PyQt**: `dialogs/main_dialog.py` loads `ui/main_dialog.ui` via `uic.loadUiType`
- **WebEngine HTML**: `web/map.html` (Leaflet) + `web/react.html` (React 18) + `web/vue.html` (Vue 3) + `web/components.html` (Web Components) + QWebChannel bridge `qrc:///qtwebchannel/qwebchannel.js`
- **Typed bridge**: `web/bridge.d.ts` auto-generated from Python Bridge via `qgis-plugin bridge generate`, runtime via `npm install @qgis-sdk/bridge`
- **Network**: `services/network.py` — `qgis_sdk.network.NetworkManager` wrapper around `QgsNetworkAccessManager` (proxy, cache, auth), fallback to urllib for testing
- **Tasks**: `services/tasks.py` — `qgis_sdk.tasks.TaskManager` wrapper around `QgsTaskManager` / `QgsTask`, decorator `@task`, fallback to ThreadPoolExecutor
- **Declarative fallback**: `qgis_sdk.ui.Dialog` / `WebDialog` for testing without QGIS
- **Testing fixtures**: `pytest_plugins = ["qgis_sdk.testing"]` → `fake_iface`, `fake_bridge`, `fake_network_manager`, `fake_task_manager`, etc.

## Development

```bash
pip install qgis-sdk
python -m pytest
qgis-plugin install
qgis-plugin dev
qgis-plugin package
```

### Bridge generation

```bash
qgis-plugin bridge generate --bridge {name}.dialogs.web_dialog:Bridge --output web/bridge.d.ts
qgis-plugin bridge generate --bridge {name}.dialogs.web_dialog:Bridge --output web/ --package
```

### Network

```python
from qgis_sdk.network import NetworkManager, fetch_json, download

# Respects QGIS proxy, cache, auth infrastructure
response = NetworkManager.instance().get("https://example.com/api")
data = fetch_json("https://example.com/data.geojson", auth_cfg="my_auth_id")
path = download("https://example.com/file.zip", "/tmp/file.zip", progress_callback=lambda p: print(p))

# Helper from QGIS cookbook pattern
from qgis_sdk.network import NetworkAccessManager
http = NetworkAccessManager(auth_cfg="my_auth", timeout=15000)
response, content = http.request("https://example.com/api")
```

### Tasks

```python
from qgis_sdk.tasks import TaskManager, Task, task, run_task

def do_work(task, wait_time):
    for i in range(100):
        time.sleep(wait_time / 100.0)
        task.set_progress(i)
        if task.is_canceled():
            return None
    return {{"result": 42}}

def on_finished(exception, result):
    print(f"Done: {{result}}")

task = Task.from_function("My task", do_work, wait_time=2, on_finished=on_finished)
TaskManager.instance().add_task(task)

# Decorator
@task("My task", can_cancel=True, on_finished=on_finished)
def my_task(task, value=10):
    task.set_progress(50)
    return value * 2

run_task(my_task, value=10)

# Processing alg in background
from qgis_sdk.tasks import ProcessingAlgRunnerTask
task = ProcessingAlgRunnerTask("qgis:buffer", params, context, feedback)
TaskManager.instance().add_task(task)
```

### Testing

```python
# conftest.py
pytest_plugins = ["qgis_sdk.testing"]

# test_plugin.py
def test_toolbar(fake_iface, fake_action_factory):
    from {name} import {class_name}Plugin
    {class_name}Plugin.action_factory = staticmethod(fake_action_factory)
    plugin = {class_name}Plugin(fake_iface)
    plugin.init_gui()
    assert len(fake_iface.toolbar_icons) == 1

def test_bridge(fake_bridge):
    assert fake_bridge.get_layer() == {{"name": "test_layer"}}

def test_network(fake_network_manager):
    resp = fake_network_manager.get("https://example.com/api")
    assert resp.ok

def test_tasks(fake_task_manager):
    def work(task):
        return 42
    t = fake_task_manager.add_task(work, description="Test")
    assert t.is_finished()
```

## UI Patterns

### Qt Dialog (.ui)

```python
from qgis.PyQt import uic
FORM_CLASS, _ = uic.loadUiType("ui/main_dialog.ui")
class MainDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)
```

### WebEngine + QWebChannel + @qgis-sdk/bridge

```python
from qgis_sdk.ui import WebDialog, web_bridge
dlg = WebDialog.from_file("web/react.html")
@web_bridge(dlg)
class Bridge:
    def get_layer(self) -> dict:
        return {{"name": "buildings"}}
dlg.exec()
```

### Network

```python
from qgis_sdk.network import NetworkManager
response = NetworkManager.instance().get("https://example.com/api")
```

### Tasks

```python
from qgis_sdk.tasks import TaskManager, Task
task = Task.from_function("My task", my_function, on_finished=on_finished)
TaskManager.instance().add_task(task)
```
"""

    (base / "README.md").write_text(readme, encoding="utf-8")

    pyproject = f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0"
description = "QGIS plugin {name}"
readme = "README.md"
requires-python = ">=3.11"
dependencies = ["qgis-sdk"]

[tool.hatch.build.targets.wheel]
packages = ["{name}"]
include = [
    "{name}/ui/*.ui",
    "{name}/web/*.html",
    "{name}/web/*.d.ts",
    "{name}/web/dist/*",
    "{name}/icons/*",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
"""

    (base / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    tests_dir = base / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "conftest.py").write_text(
        'pytest_plugins = ["qgis_sdk.testing"]\n',
        encoding="utf-8",
    )
    (tests_dir / "test_dialog.py").write_text(
        f'''"""Test dialog logic without QGIS/Qt + bridge + network + tasks + fixtures."""

from {name}.dialogs.main_dialog import make_declarative_dialog

def test_dialog_defaults():
    if make_declarative_dialog is None:
        return
    dlg = make_declarative_dialog()
    assert dlg.get("threshold") == 0.5
    assert dlg.title == "Main Dialog"

def test_dialog_exec():
    if make_declarative_dialog is None:
        return
    dlg = make_declarative_dialog()
    result = dlg.exec()
    assert result == 1

def test_fake_iface(fake_iface, fake_action_factory):
    from {name} import {class_name}Plugin
    {class_name}Plugin.action_factory = staticmethod(fake_action_factory)
    plugin = {class_name}Plugin(fake_iface)
    plugin.init_gui()
    assert len(fake_iface.toolbar_icons) >= 1

def test_bridge(fake_bridge):
    assert fake_bridge.get_layer()["name"] == "test_layer"
    assert fake_bridge.get_extent()["xmin"] == -180

def test_network(fake_network_manager):
    resp = fake_network_manager.get("https://example.com/api")
    assert resp.ok
    assert resp.json()["mock"] is True

def test_tasks(fake_task_manager):
    def work(task):
        task.set_progress(100)
        return 42
    t = fake_task_manager.add_task(work, description="Test task")
    assert t.is_finished()
    assert t.progress() == 100
''',
        encoding="utf-8",
    )

    if with_rust:
        cargo_toml = f"""[package]
name = "{name}"
version = "0.1.0"
edition = "2021"

[lib]
name = "_native"
crate-type = ["cdylib"]

[dependencies]
pyo3 = {{ version = "0.22", features = ["extension-module"] }}
"""

        (base / "Cargo.toml").write_text(cargo_toml, encoding="utf-8")
        (base / "src").mkdir(exist_ok=True)
        (base / "src" / "lib.rs").write_text(
            """use pyo3::prelude::*;

#[pyfunction]
fn hello() -> &'static str {
    "Hello from Rust!"
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello, m)?)?;
    Ok(())
}
""",
            encoding="utf-8",
        )

    return str(base)
# ── New declarative + self-installing + QGIS Web API templates (bun) ───────

import pathlib as _pathlib

def _load_bootstrap_template():
    p = _pathlib.Path(__file__).parent / "bootstrap.py"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""

try:
    BOOTSTRAP_PY_TEMPLATE
except NameError:
    BOOTSTRAP_PY_TEMPLATE = _load_bootstrap_template()

DECLARATIVE_INIT_PY = '''"""{name} — QGIS plugin with declarative API, self-installing, QGIS Web API via bun.

- Self-bootstrapping: tries extlibs/vendor/bootstrap.py
- Declarative: @plugin, @toolbar, @action, @task, @bridge, @setting
- Webview with complete QGIS API: qgis.layers.addVector, qgis.tasks.run, qgis.network.fetch, qgis.message.info
- Built with bun: bun install, bun run build, bun test
"""


def _bootstrap():
    import sys, pathlib
    plugin_dir = pathlib.Path(__file__).parent
    extlibs = plugin_dir / "extlibs"
    if extlibs.exists() and str(extlibs) not in sys.path:
        sys.path.insert(0, str(extlibs))
    vendor = plugin_dir / "vendor"
    if vendor.exists() and str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    try:
        import qgis_sdk
        return qgis_sdk
    except ImportError:
        pass
    try:
        from .bootstrap import ensure_qgis_sdk
        if ensure_qgis_sdk(auto_install=True, ask_user=True):
            import qgis_sdk
            return qgis_sdk
    except Exception as e:
        print(f"[{name}] bootstrap failed: {{e}}")
    return None

_qgis_sdk = _bootstrap()

if _qgis_sdk is None:
    def classFactory(iface):
        try:
            from qgis.PyQt.QtWidgets import QMessageBox
            QMessageBox.warning(None, "{name}", "qgis-sdk not installed and auto-install failed.\\n\\nPlease install manually:\\npip install qgis-sdk\\nor\\nconda install -c conda-forge qgis-sdk")
        except Exception:
            print("qgis-sdk not installed")
        return None
else:
    from qgis_sdk import plugin, toolbar, action, task, setting
    from qgis_sdk.bridge import bridge, method, signal
    from qgis_sdk.network import Session
    from qgis_sdk.tasks import chain

    @plugin(
        name="{name}",
        version="0.1.0",
        description="Does useful things declaratively, with JS QGIS API",
        author="{author}",
        email="{email}",
        qgis_min_version="3.28",
        category="Vector",
        permissions=["layers", "project", "tasks", "network", "message", "settings", "iface", "processing"]
    )
    class {class_name}Plugin:
        @setting(default=10.0, persist=True)
        def distance(self): return 10.0

        @toolbar("{name} Toolbar")
        @action(tooltip="Run buffer", icon="icons/buffer.svg")
        def run_buffer(self, iface, distance: float = 10.0):
            session = Session(headers={{"User-Agent": "MyPlugin/1.0"}})
            try:
                resp = session.get("https://example.com/api", params={{"distance": distance}})
                resp.raise_for_status()
            except Exception as e:
                iface.messageBar().pushMessage(f"Network: {{e}}")
            result = self.buffer_task.delay(distance)
            iface.messageBar().pushMessage(f"Task {{result.id}} started, state={{result.state}}")

        @task("Buffer task", bind=True, can_cancel=True)
        def buffer_task(self, distance: float):
            self.set_progress(0)
            import time
            for i in range(100):
                self.set_progress(i)
                if self.is_canceled():
                    return None
                time.sleep(0.01)
            return {{"distance": distance}}

        @bridge(name="my_bridge")
        class Bridge:
            @method(return_type=dict)
            def get_layer(self, layer_id: str) -> dict:
                return {{"name": layer_id, "count": 42}}

            @method()
            def log(self, msg: str) -> str:
                print(f"[JS] {{msg}}")
                return "ok"

            @signal()
            def layer_changed(self, layer_id: str):
                pass

        @toolbar("{name} Toolbar")
        @action(tooltip="Open webview with full QGIS API")
        def open_webview(self, iface):
            try:
                from qgis_sdk.ui import WebView
                from qgis.PyQt.QtCore import QUrl
                import pathlib
                webview = WebView(
                    bridge=self.Bridge(),
                    enable_qgis_api=True,
                    iface=iface,
                    permissions=self._qgis_sdk_metadata.get("permissions")
                )
                html_path = pathlib.Path(__file__).parent / "web" / "dist" / "index.html"
                if not html_path.exists():
                    html_path = pathlib.Path(__file__).parent / "web" / "index.html"
                webview.load(QUrl.fromLocalFile(str(html_path)))
                webview.show()
            except Exception as e:
                iface.messageBar().pushMessage(f"Webview error: {{e}}")

    def classFactory(iface):
        return {class_name}Plugin(iface)
'''


WEB_BUN_INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{name} — QGIS WebView with complete QGIS API</title>
<style>
  html, body { margin:0; padding:0; font-family: sans-serif; height:100%; }
  #app { padding:16px; }
  button { margin:4px; padding:8px 16px; background:#0078d4; color:white; border:none; border-radius:4px; cursor:pointer; }
  .card { border:1px solid #ddd; border-radius:8px; padding:12px; margin:8px 0; }
  code { background:#eee; padding:2px 4px; border-radius:3px; }
</style>
</head>
<body>
<div id="app">
  <h2>{name} — QGIS + Bun + Complete QGIS API</h2>
  <p><small>Using <code>window.qgis</code> global — no custom bridge needed for layers, tasks, network, message</small></p>
  <div class="card">
    <h3>Layers</h3>
    <div id="layers">Loading...</div>
    <button id="btn-add-vector">Add Vector Layer</button>
    <button id="btn-list-layers">List Layers</button>
  </div>
  <div class="card">
    <h3>Tasks</h3>
    <button id="btn-run-task">Run Buffer Task</button>
    <div id="task-status"></div>
    <div id="progress"></div>
  </div>
  <div class="card">
    <h3>Messages</h3>
    <button id="btn-message">Show Message in QGIS</button>
  </div>
  <div class="card">
    <h3>Network (via QGIS)</h3>
    <button id="btn-fetch">Fetch via QGIS NAM</button>
    <pre id="fetch-result"></pre>
  </div>
  <div class="card">
    <h3>Custom Bridge</h3>
    <button id="btn-custom">Call custom bridge.get_layer</button>
    <pre id="custom-result"></pre>
  </div>
</div>
<script type="module">
  let qgis, bridge;
  try {
    const mod = await import('./qgis-bridge.js');
    const res = await mod.createQgisBridge();
    qgis = res.qgis;
    bridge = res.bridge;
  } catch (e) {
    console.log('Trying global qgis', e);
    if (window.qgis) {
      qgis = window.qgis;
      bridge = window.qgisBridge;
    } else {
      try {
        const { createQgisBridge } = await import('@qgis-sdk/bridge');
        const res = await createQgisBridge();
        qgis = res.qgis;
        bridge = res.bridge;
      } catch (e2) {
        console.error('Failed to create bridge', e2);
        document.getElementById('layers').textContent = 'Bridge not available (run inside QGIS)';
      }
    }
  }

  if (qgis) {
    console.log('QGIS API ready', qgis);
    async function listLayers() {
      const layers = await qgis.layers.list();
      document.getElementById('layers').innerHTML = layers.map(l => `<div>${l.name} (${l.type}) — ${l.id}</div>`).join('') || 'No layers';
    }
    await listLayers();
    document.getElementById('btn-list-layers').onclick = listLayers;
    document.getElementById('btn-add-vector').onclick = async () => {
      const path = prompt('Vector path:', '/data/roads.shp');
      if (path) {
        try {
          const layer = await qgis.layers.addVector(path, 'Roads');
          alert('Added ' + layer.id);
          await listLayers();
        } catch (e) { alert('Failed: ' + e); }
      }
    };

    document.getElementById('btn-run-task').onclick = async () => {
      const task = await qgis.tasks.run('buffer_task', {distance: 10});
      document.getElementById('task-status').textContent = `Task ${task.task_id} started`;
      task.onProgress(p => document.getElementById('progress').textContent = p + '%');
      task.onFinished(result => document.getElementById('task-status').textContent = 'Finished: ' + JSON.stringify(result));
    };

    document.getElementById('btn-message').onclick = async () => {
      await qgis.message.info('My Plugin', 'Hello from JS webview!', 5);
    };

    document.getElementById('btn-fetch').onclick = async () => {
      try {
        const resp = await qgis.network.fetch('https://example.com/api');
        const json = await resp.json();
        document.getElementById('fetch-result').textContent = JSON.stringify(json, null, 2);
      } catch (e) {
        document.getElementById('fetch-result').textContent = 'Error: ' + e;
      }
    };

    document.getElementById('btn-custom').onclick = async () => {
      try {
        const layer = await bridge.get_layer('my_layer');
        document.getElementById('custom-result').textContent = JSON.stringify(layer, null, 2);
      } catch (e) {
        document.getElementById('custom-result').textContent = 'Error: ' + e;
      }
    };

    qgis.addEventListener('layer_added', (e) => console.log('layer added', e.detail));
    bridge.addEventListener('layer_changed', (e) => console.log('layer changed', e.detail));
  }
</script>
</body>
</html>
"""

WEB_BUN_APP_TS = """// {name} web app — using complete QGIS API via bun, no custom bridge boilerplate
import { createQgisBridge, QgisBridge } from '@qgis-sdk/bridge';

const { bridge, qgis } = await createQgisBridge();

await qgis.message.info("My Plugin", "Webview ready!", 3);

const layers = await qgis.layers.list();
console.log("Layers", layers);

const addVectorBtn = document.getElementById("btn-add-vector");
addVectorBtn?.addEventListener("click", async () => {
  const layer = await qgis.layers.addVector("/data/roads.shp", "Roads");
  console.log("Added", layer.id);
  await qgis.layers.zoomTo(layer.id);
});

const runTaskBtn = document.getElementById("btn-run-task");
runTaskBtn?.addEventListener("click", async () => {
  const task = await qgis.tasks.run("buffer_task", {distance: 10});
  task.onProgress(p => {
    const el = document.getElementById("progress");
    if (el) el.textContent = `${p}%`;
  });
  task.onFinished(result => {
    console.log("Task finished", result);
    qgis.message.success("Task", `Done: ${JSON.stringify(result)}`);
  });
});

const fetchBtn = document.getElementById("btn-fetch");
fetchBtn?.addEventListener("click", async () => {
  const resp = await qgis.network.fetch("https://example.com/api", {authCfg: "my_auth"});
  const data = await resp.json();
  console.log(data);
});

bridge.addEventListener("open", () => console.log("bridge open, state:", bridge.readyState));
const customBtn = document.getElementById("btn-custom");
customBtn?.addEventListener("click", async () => {
  const layer = await bridge.get_layer("my_layer");
  console.log(layer);
});

console.log(bridge.readyState === QgisBridge.OPEN);
"""

WEB_BUN_PACKAGE_JSON = """{
  "name": "{name}-web",
  "type": "module",
  "version": "0.1.0",
  "scripts": {
    "dev": "bun --bun vite",
    "build": "bun build src/app.ts --outdir dist --target browser --minify --sourcemap external && cp src/index.html dist/index.html",
    "test": "bun test"
  },
  "dependencies": {
    "@qgis-sdk/bridge": "workspace:*"
  },
  "devDependencies": {
    "vite": "^5.0.0"
  }
}
"""

BUN_ROOT_PACKAGE_JSON = """{
  "name": "{name}",
  "private": true,
  "type": "module",
  "workspaces": ["web"],
  "scripts": {
    "build": "bun run --filter '*' build",
    "test": "bun test",
    "dev": "bun --bun vite --cwd web"
  },
  "packageManager": "bun@1.2.0"
}
"""

def _write_declarative_plugin(base, name, class_name, author, email):
    from pathlib import Path as _Path
    (base / name / "__init__.py").write_text(
        DECLARATIVE_INIT_PY.format(name=name, class_name=class_name, author=author, email=email),
        encoding="utf-8"
    )
    # bootstrap
    try:
        src_boot = _Path(__file__).parent / "bootstrap.py"
        if src_boot.exists():
            (base / name / "bootstrap.py").write_text(src_boot.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            (base / name / "bootstrap.py").write_text(BOOTSTRAP_PY_TEMPLATE, encoding="utf-8")
    except Exception:
        (base / name / "bootstrap.py").write_text(BOOTSTRAP_PY_TEMPLATE, encoding="utf-8")
    (base / ".gitignore").write_text("extlibs/\nwheels/\n__pycache__/\n*.pyc\nnode_modules/\nweb/dist/\nweb/node_modules/\n", encoding="utf-8")
    (base / name / "icons").mkdir(exist_ok=True)
    (base / name / "icons" / ".gitkeep").write_text("", encoding="utf-8")
    web_dir = base / name / "web"
    web_dir.mkdir(parents=True, exist_ok=True)
    (web_dir / "index.html").write_text(WEB_BUN_INDEX_HTML.replace("{name}", name), encoding="utf-8")
    src_dir = web_dir / "src"
    src_dir.mkdir(exist_ok=True)
    (src_dir / "app.ts").write_text(WEB_BUN_APP_TS.replace("{name}", name), encoding="utf-8")
    (web_dir / "package.json").write_text(WEB_BUN_PACKAGE_JSON.replace("{name}", name), encoding="utf-8")
    (base / "package.json").write_text(BUN_ROOT_PACKAGE_JSON.replace("{name}", name), encoding="utf-8")
    (web_dir / "tsconfig.json").write_text('{\n  "compilerOptions": {\n    "target": "ES2022",\n    "module": "ESNext",\n    "moduleResolution": "bundler",\n    "strict": true,\n    "esModuleInterop": true\n  }\n}\n', encoding="utf-8")
    (web_dir / "bridge.json").write_text('{\n  "name": "my_bridge",\n  "methods": [\n    {"name": "get_layer", "args": [{"name": "layer_id", "type": "string"}], "return_type": "object"},\n    {"name": "log", "args": [{"name": "msg", "type": "string"}], "return_type": "string"}\n  ],\n  "signals": [{"name": "layer_changed", "args": [{"name": "layer_id", "type": "string"}]}]\n}\n', encoding="utf-8")
    services_dir = base / name / "services"
    services_dir.mkdir(exist_ok=True)
    (services_dir / "__init__.py").write_text("", encoding="utf-8")
    try:
        (services_dir / "network.py").write_text(SERVICES_NETWORK_PY, encoding="utf-8")
        (services_dir / "tasks.py").write_text(SERVICES_TASKS_PY, encoding="utf-8")
    except NameError:
        pass

def scaffold_plugin_declarative(
    name: str,
    path: str,
    author: str | None = None,
    email: str | None = None,
    with_bundle: bool = False,
    offline_wheel: str | None = None,
) -> str:
    from pathlib import Path
    base = Path(path) / name
    if base.exists():
        raise ValueError(f"directory already exists: {base}")
    base.mkdir(parents=True)
    (base / name).mkdir()
    class_name = to_pascal_case(name)
    author = author or "Your Name"
    email = email or "you@example.com"

    _write_declarative_plugin(base, name, class_name, author, email)

    metadata = f"""[general]
name={name}
qgisMinimumVersion=3.28
description=Does useful things declaratively with QGIS Web API
about=Does useful things
version=0.1.0
author={author}
email={email}
category=Vector
hasProcessingProvider=False
"""
    (base / "metadata.txt").write_text(metadata, encoding="utf-8")

    pyproject = f"""[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{name}"
version = "0.1.0"
description = "QGIS plugin {name}"
readme = "README.md"
requires-python = ">=3.11"
dependencies = ["qgis-sdk"]

[tool.hatch.build.targets.wheel]
packages = ["{name}"]
include = [
    "{name}/bootstrap.py",
    "{name}/web/*.html",
    "{name}/web/*.json",
    "{name}/web/dist/*",
    "{name}/icons/*",
    "{name}/web/src/*",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
"""
    (base / "pyproject.toml").write_text(pyproject, encoding="utf-8")

    readme = f"""# {name}

Declarative QGIS plugin with self-installing runtime and complete QGIS Web API via bun.

## Features

- **Self-installing**: `bootstrap.py` vendored (<300 LOC), auto-installs `qgis-sdk` to `extlibs/` via pip, fallback to `wheels/` or PyPI. No CLI needed.
- **Declarative**: `@plugin(permissions=[...])`, `@toolbar`, `@action`, `@task`, `@bridge`, `@setting`
- **Complete QGIS API in JS**: `window.qgis` with `layers.addVector/list/zoom`, `project.crs/setCrs`, `message.info/warning`, `tasks.run`, `network.fetch` (via QgsNetworkAccessManager), `iface`, `settings`, `processing`
- **Bun**: `bun install`, `bun run build`, `bun test` — uses `@qgis-sdk/bridge` with EventTarget/WebSocket-like API

## Quick start

```bash
cd {name}
bun install
bun run build
python -m pytest
```

## Self-install helper

Plugin zip contains `bootstrap.py` + `extlibs/` gitignored. On first load in QGIS:

1. Try `extlibs/` and `vendor/`
2. Try `wheels/qgis_sdk*.whl` offline
3. Try pip install to `extlibs/`
4. Ask user via QMessageBox: auto-install or manual instructions

To vendor offline wheel:

```bash
qgis-plugin vendor --output {name}/wheels
# or
qgis-plugin package --bundle --offline-wheel dist/qgis_sdk-0.1.0-py3-none-any.whl
```

## JS QGIS API

```js
import {{ createQgisBridge }} from '@qgis-sdk/bridge';
const {{ qgis, bridge }} = await createQgisBridge();

// Layers
const layers = await qgis.layers.list();
const layer = await qgis.layers.addVector("/data/roads.shp", "Roads");
await qgis.layers.zoomTo(layer.id);

// Tasks
const task = await qgis.tasks.run("buffer_task", {{distance: 10}});
task.onProgress(p => console.log(p + "%"));
task.onFinished(r => qgis.message.success("Done", JSON.stringify(r)));

// Network via QGIS (no CORS, respects proxy/auth)
const resp = await qgis.network.fetch("https://example.com/api", {{authCfg: "my_auth"}});
const data = await resp.json();

// Messages
await qgis.message.info("My Plugin", "Hello from JS!");

// Custom bridge still works
const custom = await bridge.get_layer("my_layer");
```

## Permissions

Declared via `@plugin(permissions=[...])`. JS `qgis` only exposes allowed namespaces. Default all allowed, but you can restrict.

## Bridge description (no codegen)

Python `Bridge` decorated with `@bridge` + `@method` + `@signal` generates JSON description via `BridgeDescription.from_class`. Runtime loads JSON, not codegen.

```python
from qgis_sdk.bridge import BridgeDescription
desc = BridgeDescription.from_class(MyPlugin.Bridge, name="my_bridge")
print(desc.to_json())
```

JS side auto-loads `window.__QGIS_BRIDGE_DESCRIPTION__` injected by Python `BridgeRuntime`.

## Testing

```python
pytest_plugins = ["qgis_sdk.testing"]

def test_plugin(fake_iface, fake_action_factory):
    from {name} import {class_name}Plugin
    plugin = {class_name}Plugin(fake_iface)
    assert plugin._qgis_sdk_metadata["permissions"]
```

```bash
bun test  # JS tests via bun:test
```

## Packaging

```bash
qgis-plugin package --bundle --offline-wheel dist/qgis_sdk-*.whl
# produces zip with extlibs empty, wheels/ contains wheel, bootstrap.py vendored
```
"""

    (base / "README.md").write_text(readme, encoding="utf-8")

    tests_dir = base / "tests"
    tests_dir.mkdir()
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "conftest.py").write_text('pytest_plugins = ["qgis_sdk.testing"]\n', encoding="utf-8")
    (tests_dir / "test_plugin.py").write_text(f'''"""Test declarative plugin + QGIS API + self-install."""

def test_plugin_meta():
    from {name} import {class_name}Plugin
    assert hasattr({class_name}Plugin, "_qgis_sdk_metadata")
    meta = {class_name}Plugin._qgis_sdk_metadata
    assert meta["name"] == "{name}"
    assert "layers" in meta["permissions"]

def test_bridge_description():
    from {name} import {class_name}Plugin
    from qgis_sdk.bridge import BridgeDescription
    desc = BridgeDescription.from_class({class_name}Plugin.Bridge, name="my_bridge")
    assert "get_layer" in [m.name for m in desc.methods]
    json_str = desc.to_json()
    assert "my_bridge" in json_str

def test_qgis_api_description():
    from qgis_sdk.bridge.qgis_api import QgisApi
    api = QgisApi(permissions=["layers", "message"])
    desc = api.description
    names = [m.name for m in desc]
    assert "layers_list" in names
    assert "message_info" in names
    assert "tasks_run" not in names

def test_bootstrap_exists():
    from pathlib import Path
    import {name}.bootstrap as bs
    assert hasattr(bs, "ensure_qgis_sdk")
    assert Path(__file__).parent.parent / "{name}" / "bootstrap.py"

def test_fake_bridge_qgis_api(fake_qgis_api):
    layers = fake_qgis_api.layers.list()
    assert isinstance(layers, list)
''', encoding="utf-8")

    if with_bundle:
        wheels_dir = base / "wheels"
        wheels_dir.mkdir(exist_ok=True)
        if offline_wheel:
            import shutil
            shutil.copy(offline_wheel, wheels_dir / _pathlib.Path(offline_wheel).name)
        (wheels_dir / ".gitkeep").write_text("", encoding="utf-8")

    return str(base)

_original_scaffold_plugin = scaffold_plugin

def scaffold_plugin(
    name: str,
    path: str,
    plugin_type: str = "general",
    with_rust: bool = False,
    with_web: bool = False,
    with_ui: bool = True,
    web_framework: str = "vanilla",
    author: str | None = None,
    email: str | None = None,
    declarative: bool = False,
    with_bundle: bool = False,
    offline_wheel: str | None = None,
    **kwargs,
) -> str:
    if declarative or web_framework == "bun":
        return scaffold_plugin_declarative(name, path, author=author, email=email, with_bundle=with_bundle, offline_wheel=offline_wheel)
    return _original_scaffold_plugin(name, path, plugin_type, with_rust, with_web, with_ui, web_framework, author, email)
