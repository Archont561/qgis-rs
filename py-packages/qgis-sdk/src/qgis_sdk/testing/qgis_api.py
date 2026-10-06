"""Fakes for ``window.qgis`` — the object a plugin's web UI talks to.

doc-5's module list does not name these; they are the JavaScript-facing
façade the bridge installs, and they are separated from
:mod:`qgis_sdk.testing.bridge` on purpose: that module tests the *protocol*,
this one gives a web-UI test an object with the camelCase methods the browser
side calls. Both exist because a plugin's TypeScript calls
``qgis.layers.addVector`` while the wire carries ``layers.add_vector``, and a
fake that blurred the two would hide exactly the renaming bug worth catching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .calls import CallLog, call_log
from .iface import FakeIface
from .network import FakeNetworkManager
from .tasks import FakeAsyncResult, FakeTask, FakeTaskManager


class FakeLayersAPI:
    def __init__(self):
        self._layers = [
            {"id": "layer1", "name": "Roads", "type": "vector", "crs": "EPSG:4326"},
            {"id": "layer2", "name": "Buildings", "type": "vector", "crs": "EPSG:4326"},
        ]

    def list(self):
        return list(self._layers)

    def active(self):
        return self._layers[0] if self._layers else None

    def addVector(self, path, name=None, provider="ogr"):  # noqa: N802 - web API naming
        layer = {"id": f"layer_{len(self._layers)+1}", "name": name or Path(path).stem, "type": "vector", "path": path, "provider": provider}
        self._layers.append(layer)
        return layer

    def addRaster(self, path, name=None, provider="gdal"):  # noqa: N802 - web API naming
        layer = {"id": f"layer_{len(self._layers)+1}", "name": name or Path(path).stem, "type": "raster", "path": path, "provider": provider}
        self._layers.append(layer)
        return layer

    def remove(self, layer_id):
        self._layers = [l for l in self._layers if l["id"] != layer_id]
        return True

    def zoomTo(self, layer_id):  # noqa: N802 - web API naming
        return True

    def get(self, layer_id):
        for l in self._layers:
            if l["id"] == layer_id:
                return l
        return None


class FakeProjectAPI:
    def __init__(self):
        self._crs = "EPSG:4326"
        self._path = "/tmp/project.qgz"

    def info(self):
        return {"crs": self._crs, "path": self._path, "title": "Test Project"}

    def write(self):
        return True

    def crs(self):
        return self._crs

    def setCrs(self, crs):  # noqa: N802 - web API naming
        self._crs = crs
        return True

    def path(self):
        return self._path


class FakeMessageAPI:
    def __init__(self):
        self.messages = []

    def info(self, title, text, duration=5):
        self.messages.append({"level": "info", "title": title, "text": text, "duration": duration})
        return True

    def warning(self, title, text, duration=5):
        self.messages.append({"level": "warning", "title": title, "text": text, "duration": duration})
        return True

    def critical(self, title, text, duration=5):
        self.messages.append({"level": "critical", "title": title, "text": text, "duration": duration})
        return True

    def success(self, title, text, duration=5):
        self.messages.append({"level": "success", "title": title, "text": text, "duration": duration})
        return True


class FakeTasksAPI:
    def __init__(self, task_manager=None):
        self._tm = task_manager or FakeTaskManager()
        self._tasks = {}

    def run(self, name, params=None):
        t = FakeTask(description=name, function=lambda task, **kw: {"name": name, "params": params})
        async_res = FakeAsyncResult(t)
        task_id = t.id
        self._tasks[task_id] = async_res

        class TaskHandle:
            def __init__(self, task_id, async_res):
                self.task_id = task_id
                self._async_res = async_res
                self._progress_cbs = []
                self._finished_cbs = []

            def onProgress(self, cb):  # noqa: N802 - web API naming
                self._progress_cbs.append(cb)
                for p in [0, 50, 100]:
                    try:
                        cb(p)
                    except Exception:
                        pass
                return self

            def onFinished(self, cb):  # noqa: N802 - web API naming
                self._finished_cbs.append(cb)
                try:
                    cb(self._async_res.get())
                except Exception:
                    pass
                return self

            def cancel(self):
                self._async_res._task.cancel()

        return TaskHandle(task_id, async_res)

    def list(self):
        return list(self._tasks.keys())

    def cancel(self, task_id):
        if task_id in self._tasks:
            self._tasks[task_id]._task.cancel()
            return True
        return False


class FakeNetworkAPI:
    def __init__(self, network_manager=None):
        self._nm = network_manager or FakeNetworkManager()

    def fetch(self, url, options=None):
        resp = self._nm.get(url)

        class FakeResp:
            def __init__(self, resp):
                self._resp = resp
                self.ok = resp.ok
                self.status = resp.status_code
                self.url = resp.url

            def json(self):
                return self._resp.json()

            def text(self):
                return self._resp.text

            def arrayBuffer(self):  # noqa: N802 - web API naming
                return self._resp.content

        return FakeResp(resp)

    def get(self, url, options=None):
        return self.fetch(url, options)

    def post(self, url, data=None, options=None):
        resp = self._nm.post(url, data=data)

        class FakeResp:
            def __init__(self, resp):
                self._resp = resp
                self.ok = resp.ok
                self.status = resp.status_code

            def json(self):
                return self._resp.json()

            def text(self):
                return self._resp.text

        return FakeResp(resp)


class FakeIfaceAPI:
    def __init__(self, iface=None):
        self._iface = iface or FakeIface()
        self._active_layer = {"id": "layer1", "name": "Roads"}

    def zoomToLayer(self, layer_id):  # noqa: N802 - web API naming
        return True

    def showMessage(self, title, text, level=0, duration=5):  # noqa: N802 - web API naming
        self._iface.pushMessage(f"{title}: {text}")
        return True

    def activeLayer(self):  # noqa: N802 - web API naming
        return self._active_layer


class FakeSettingsAPI:
    def __init__(self):
        self._store = {}

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self._store[key] = value
        return True


class FakeProcessingAPI:
    def run(self, alg_id, params=None):
        return {"alg": alg_id, "params": params, "result": "ok"}


class FakeQgisAPI:
    """Fake window.qgis — complete QGIS Web API for testing."""

    def __init__(self, iface=None, network_manager=None, task_manager=None, calls: Optional[CallLog] = None):
        self.calls = call_log(calls)
        self.layers = FakeLayersAPI()
        self.project = FakeProjectAPI()
        self.message = FakeMessageAPI()
        self.messageBar = self.message
        self.tasks = FakeTasksAPI(task_manager=task_manager)
        self.network = FakeNetworkAPI(network_manager=network_manager)
        self.iface = FakeIfaceAPI(iface=iface)
        self.settings = FakeSettingsAPI()
        self.processing = FakeProcessingAPI()
        self._event_listeners = {}

    def addEventListener(self, event, cb):  # noqa: N802 - web API naming
        self._event_listeners.setdefault(event, []).append(cb)

    def removeEventListener(self, event, cb):  # noqa: N802 - web API naming
        if event in self._event_listeners:
            try:
                self._event_listeners[event].remove(cb)
            except ValueError:
                pass

    def dispatchEvent(self, event, detail=None):  # noqa: N802 - web API naming
        self.calls.record("qgis", "event.dispatch", event=event)
        for cb in self._event_listeners.get(event, []):
            try:
                cb(type("obj", (), {"detail": detail})())
            except Exception:
                pass


def fake_qgis_api_factory(iface=None, network_manager=None, task_manager=None):
    return FakeQgisAPI(iface=iface, network_manager=network_manager, task_manager=task_manager)


__all__ = [
    "FakeLayersAPI",
    "FakeProjectAPI",
    "FakeMessageAPI",
    "FakeTasksAPI",
    "FakeNetworkAPI",
    "FakeIfaceAPI",
    "FakeSettingsAPI",
    "FakeProcessingAPI",
    "FakeQgisAPI",
    "fake_qgis_api_factory",
]
