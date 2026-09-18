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
