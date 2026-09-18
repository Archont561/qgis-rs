"""
qgis_sdk.testing — pytest fixtures and fakes for testing QGIS plugins without QGIS.

This module is importable without QGIS/Qt. It provides:
- Fake QGIS interface (QgisInterface) and actions
- Fake contexts for Algorithms
- Fake dialogs and web views
- Fake network (requests-like) and tasks (celery-like)
- pytest fixtures (auto-discovered if you add `pytest_plugins = ["qgis_sdk.testing"]` or via entry point)

Usage in tests:

    # conftest.py
    pytest_plugins = ["qgis_sdk.testing"]

    # test_my_plugin.py
    def test_toolbar(fake_iface, fake_action_factory):
        from my_plugin import MyPlugin
        MyPlugin.action_factory = staticmethod(fake_action_factory)
        plugin = MyPlugin(fake_iface)
        plugin.init_gui()
        assert len(fake_iface.toolbar_icons) == 1
        fake_iface.toolbar_icons[0].trigger()
        assert "hello" in fake_iface.messages

    def test_dialog(fake_dialog_factory, fake_webview_factory):
        from qgis_sdk.ui import Dialog, field, layout, Button
        dlg = Dialog(title="Test", layout=[field.text("name", default="hi")])
        dlg._qdialog = fake_dialog_factory()
        assert dlg.get("name") == "hi"

    def test_bridge(fake_bridge):
        assert fake_bridge.get_layer() == {"name": "test"}

    def test_network(fake_network_manager):
        resp = fake_network_manager.get("https://example.com/api")
        assert resp.ok
        assert resp.json()["mock"] is True

    def test_network_requests_like(fake_session):
        resp = fake_session.get("https://example.com/api", params={"q": "test"})
        assert resp.status_code == 200
        assert resp.ok
        resp.raise_for_status()

    def test_tasks_celery_like(fake_task_manager):
        from qgis_sdk.tasks import task

        @task(bind=True)
        def add(self, x, y):
            self.set_progress(50)
            return x + y

        result = add(4, 4)  # sync
        assert result == 8

        async_result = add.delay(4, 4)  # async via FakeTaskManager
        assert async_result.get() == 8
        assert async_result.ready()
        assert async_result.successful()
        assert async_result.state == "SUCCESS"
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse


# ── Fake QGIS interface ─────────────────────────────────────────────────────

class FakeAction:
    """Fake QAction — stands in for QgisInterface toolbar/menu actions."""

    def __init__(self, spec, callback: Callable[[], None]):
        self.spec = spec
        self.callback = callback
        self.triggered = 0
        self.objectName = f"qgis_sdk_{spec.func_name}" if hasattr(spec, "func_name") else "fake_action"
        self.tooltip = getattr(spec, "tooltip", "")
        self.icon = getattr(spec, "icon", None)

    def trigger(self):
        self.triggered += 1
        self.callback()

    def setObjectName(self, name: str):
        self.objectName = name


class FakeIface:
    """Fake QgisInterface — minimal impl for plugin lifecycle tests."""

    def __init__(self):
        self.toolbar_icons: List[Any] = []
        self.menu_entries: List[Tuple[str, Any]] = []
        self.messages: List[str] = []
        self._main_window = None

    def addToolBarIcon(self, widget):  # noqa: N802 - PyQGIS naming
        self.toolbar_icons.append(widget)

    def addPluginToMenu(self, path, widget):  # noqa: N802 - PyQGIS naming
        self.menu_entries.append((path, widget))

    def removeToolBarIcon(self, widget):  # noqa: N802 - PyQGIS naming
        if widget in self.toolbar_icons:
            self.toolbar_icons.remove(widget)

    def removePluginMenu(self, path, widget):  # noqa: N802 - PyQGIS naming
        if (path, widget) in self.menu_entries:
            self.menu_entries.remove((path, widget))

    def messageBar(self):
        return self

    def pushMessage(self, text, level=0, duration=5):  # noqa: N802
        self.messages.append(text)

    def message(self, text):
        self.messages.append(text)

    def mainWindow(self):  # noqa: N802
        return self._main_window

    def activeLayer(self):  # noqa: N802
        return None


def _make_fake_action(spec, callback):
    """Internal factory that creates FakeAction."""
    return FakeAction(spec, callback)


def fake_action_factory(spec, callback):
    """Factory that creates FakeAction — use as Plugin.action_factory."""
    return FakeAction(spec, callback)


# ── Fake contexts for Algorithms ────────────────────────────────────────────

class FakeContext:
    """Fake processing context for Algorithm tests."""

    def __init__(self, values: Optional[Dict[str, Any]] = None):
        self.values = values or {}
        self.progress: List[float] = []
        self._canceled = False

    def get(self, name, default=None):
        key = getattr(name, "name", name)
        return self.values.get(key, default)

    def set_progress(self, fraction: float):
        self.progress.append(fraction)

    @property
    def is_canceled(self):
        return self._canceled

    def create_sink(self, output, fields=None, geometry_type=None, crs=None):
        return FakeSink()

    def source_path(self, param):
        return f"/tmp/{getattr(param, 'name', param)}.gpkg"

    def sink_path(self, param):
        return f"/tmp/{getattr(param, 'name', param)}_out.gpkg"


class FakeSink:
    """Fake sink for algorithm outputs."""

    def __init__(self):
        self.features_list: List[Any] = []
        self.fields = []
        self.geometry_type = "Point"

    def add_feature(self, feature):
        self.features_list.append(feature)

    @property
    def feature_count(self):
        return len(self.features_list)

    def features(self):
        return iter(self.features_list)

    def dissolve(self):
        if self.features_list:
            self.features_list = self.features_list[:1]


class FakeFeature:
    """Fake QgsFeature."""

    def __init__(self, fid=0, attributes=None, geometry=None):
        self.id = fid
        self._attributes = attributes or {"name": f"feature_{fid}"}
        self._geometry = geometry or FakeGeometry()

    def __getitem__(self, key):
        return self._attributes.get(key)

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, geom):
        self._geometry = geom

    def clone(self):
        return FakeFeature(self.id, dict(self._attributes), self._geometry)


class FakeGeometry:
    """Fake QgsGeometry."""

    def __init__(self, wkt="POINT(0 0)", area=1.0):
        self._wkt = wkt
        self._area = area

    @property
    def area(self):
        return self._area

    def buffer(self, distance, segments=8, end_cap_style=None):
        return FakeGeometry(f"BUFFER({self._wkt}, {distance})", area=self._area + distance)

    def to_wkt(self):
        return self._wkt


class FakeFields:
    """Fake QgsFields."""

    def __init__(self, names=None):
        self.names = names or ["name", "id"]


def mock_features(count=10, geometry_type="Point"):
    """Create list of fake features."""
    return [FakeFeature(fid=i) for i in range(count)]


def mock_source(features=None, fields=None, geometry_type="Point", feature_count=None, crs=None):
    """Create fake source (vector layer)."""

    class FakeSource:
        def __init__(self):
            self._features = features or mock_features(feature_count or 10, geometry_type)
            self._fields = fields or FakeFields()
            self.geometry_type = geometry_type
            self.crs = crs

        @property
        def feature_count(self):
            return len(self._features)

        def features(self, bbox=None, limit=None, filter=None):
            feats = self._features
            if limit:
                feats = feats[:limit]
            return iter(feats)

        @property
        def fields(self):
            return self._fields

    return FakeSource()


def mock_context(values=None):
    """Create fake processing context."""
    return FakeContext(values)


# ── Fake dialogs ────────────────────────────────────────────────────────────

class FakeDialogWidget:
    """Fake widget inside dialog (QLineEdit, QSpinBox, etc.)."""

    def __init__(self, value=None, checked=False, text="", current_text=""):
        self._value = value
        self._checked = checked
        self._text = text or str(value or "")
        self._current_text = current_text or self._text
        self._current_layer = None

    def text(self):
        return self._text

    def setText(self, t):
        self._text = t

    def value(self):
        return self._value

    def setValue(self, v):
        self._value = v

    def isChecked(self):
        return self._checked

    def setChecked(self, c):
        self._checked = c

    def currentText(self):
        return self._current_text

    def setCurrentText(self, t):
        self._current_text = t

    def currentLayer(self):
        return self._current_layer


class FakeDialog:
    """Fake QDialog for testing dialog logic without Qt."""

    Accepted = 1
    Rejected = 0

    def __init__(self, values=None):
        self.values = values or {}
        self._widgets: Dict[str, FakeDialogWidget] = {}
        for k, v in self.values.items():
            self._widgets[k] = FakeDialogWidget(value=v, text=str(v))
            self._widgets[f"{k}_field"] = self._widgets[k]
        self._accepted = True

    def get(self, key):
        w = self._widgets.get(key) or self._widgets.get(f"{key}_field")
        if w:
            if hasattr(w, "text") and w.text():
                try:
                    return float(w.text()) if "." in w.text() else w.text()
                except Exception:
                    return w.text()
            return w.value()
        return self.values.get(key)

    def exec(self):
        return FakeDialog.Accepted if self._accepted else FakeDialog.Rejected

    def accept(self):
        self._accepted = True

    def reject(self):
        self._accepted = False


def _make_fake_dialog(values=None):
    return FakeDialog(values)


def fake_dialog_factory(values=None):
    """Factory for FakeDialog."""
    return FakeDialog(values)


# ── Fake web views ──────────────────────────────────────────────────────────

class FakeWebPage:
    """Fake QWebEnginePage."""

    def __init__(self):
        self.js_calls: List[str] = []
        self.html = ""
        self.url = ""

    def runJavaScript(self, js_code, callback=None):
        self.js_calls.append(js_code)
        if callback:
            callback(f"result of {js_code[:20]}")

    def setWebChannel(self, channel):
        self.channel = channel


class FakeWebView:
    """Fake QWebEngineView."""

    def __init__(self, parent=None):
        self._page = FakeWebPage()
        self.parent = parent
        self.html = ""
        self.url = ""

    def page(self):
        return self._page

    def setHtml(self, html, baseUrl=None):
        self.html = html
        self._page.html = html

    def setUrl(self, url):
        self.url = str(url)
        self._page.url = str(url)


class FakeWebChannel:
    """Fake QWebChannel."""

    def __init__(self):
        self.objects: Dict[str, Any] = {}

    def registerObject(self, name, obj):
        self.objects[name] = obj


def _make_fake_webview(html=""):
    view = FakeWebView()
    view.setHtml(html)
    return view


def fake_webview_factory(html=""):
    """Factory for FakeWebView."""
    view = FakeWebView()
    view.setHtml(html)
    return view


class FakeBridge:
    """Fake bridge for testing JS↔Python communication."""

    def get_layer(self):
        return {"name": "test_layer", "count": 42}

    def get_extent(self):
        return {"xmin": -180, "ymin": -90, "xmax": 180, "ymax": 90}

    def log(self, msg):
        return f"logged: {msg}"

    def process(self, data):
        try:
            parsed = json.loads(data) if isinstance(data, str) else data
            return {"status": "ok", "action": parsed.get("action", "unknown")}
        except Exception:
            return {"status": "ok", "data": str(data)}


def fake_bridge_factory():
    return FakeBridge()


# ── Fake network (requests-like) ────────────────────────────────────────────

def _build_url(url: str, params: Optional[Dict[str, Any]] = None) -> str:
    if not params:
        return url
    parsed = urlparse(url)
    existing = parse_qs(parsed.query)
    merged: Dict[str, Any] = {}
    for k, v in existing.items():
        merged[k] = v[0] if len(v) == 1 else v
    merged.update(params)
    query = urlencode(merged, doseq=True)
    return urlunparse(parsed._replace(query=query))


class FakeNetworkResponse:
    """Fake NetworkResponse — requests-like for testing without QGIS."""

    def __init__(
        self,
        url="https://example.com",
        status_code=200,
        content=b'{"ok": true}',
        headers=None,
        error=None,
        encoding="utf-8",
        elapsed=0.01,
        reason=None,
        cookies=None,
    ):
        self.url = url
        self.status_code = status_code
        self.content = content if isinstance(content, bytes) else str(content).encode("utf-8")
        self.headers = {k.lower(): v for k, v in (headers or {"content-type": "application/json"}).items()}
        self.error = error
        self.error_code = 0 if error is None else 1
        self.encoding = encoding
        self.elapsed = elapsed
        self.reason = reason or ("OK" if status_code == 200 else "Error")
        self.cookies = cookies or {}
        self.history: List["FakeNetworkResponse"] = []

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        try:
            return self.content.decode(self.encoding or "utf-8")
        except Exception:
            return self.content.decode("latin-1", errors="ignore")

    @property
    def apparent_encoding(self) -> str:
        return "utf-8"

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if not self.ok:
            try:
                from .network import HTTPError

                raise HTTPError(f"{self.status_code} {self.reason}: {self.error or self.text[:200]} for url: {self.url}", response=self)
            except ImportError:
                raise Exception(f"HTTP {self.status_code}: {self.error or self.text[:200]}")

    def iter_content(self, chunk_size: int = 1024) -> Iterator[bytes]:
        for i in range(0, len(self.content), chunk_size):
            yield self.content[i : i + chunk_size]

    def iter_lines(self, chunk_size: int = 1024, decode_unicode: bool = False) -> Iterator[Any]:
        lines = self.content.split(b"\n")
        for line in lines:
            if decode_unicode:
                yield line.decode(self.encoding or "utf-8", errors="ignore")
            else:
                yield line

    @property
    def is_redirect(self) -> bool:
        return self.status_code in (301, 302, 303, 307, 308)

    def __bool__(self):
        return self.ok

    def __repr__(self):
        return f"<FakeNetworkResponse [{self.status_code}]>"


class FakeNetworkManager:
    """Fake NetworkManager — requests-like, returns canned responses, captures requests."""

    def __init__(self, responses: Optional[Dict[str, FakeNetworkResponse]] = None, headers: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.requests: List[Dict[str, Any]] = []
        self.downloads: List[Tuple[str, str]] = []
        self.headers: Dict[str, str] = dict(headers or {})
        self.auth_cfg: Optional[str] = None
        self.timeout: int = 15000

    def _match_response(self, url: str) -> FakeNetworkResponse:
        if url in self.responses:
            return self.responses[url]
        for pattern, resp in self.responses.items():
            if pattern in url:
                return resp
        # Default mock
        return FakeNetworkResponse(url=url, status_code=200, content=b'{"mock": true}')

    def request(
        self,
        url,
        method="GET",
        data=None,
        json=None,
        headers=None,
        params=None,
        auth_cfg=None,
        blocking=True,
        timeout=None,
        **kwargs,
    ):
        full_url = _build_url(url, params)
        all_headers = dict(self.headers)
        if headers:
            all_headers.update(headers)
        self.requests.append(
            {
                "url": full_url,
                "original_url": url,
                "method": method,
                "data": data,
                "json": json,
                "headers": all_headers,
                "params": params,
                "auth_cfg": auth_cfg,
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )
        return self._match_response(full_url)

    def get(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="GET", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def post(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="POST", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def put(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="PUT", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def patch(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="PATCH", data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def delete(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="DELETE", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def head(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="HEAD", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def options(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request(url, method="OPTIONS", params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def download(self, url, dest_path, progress_callback=None, auth_cfg=None, timeout=None, params=None, **kwargs):
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self.downloads.append((url, str(dest_path)))
        resp = self.request(url, params=params, auth_cfg=auth_cfg, timeout=timeout, **kwargs)
        dest.write_bytes(resp.content)
        if progress_callback:
            progress_callback(100)
        return dest

    def fetch(self, url, params=None, auth_cfg=None):
        full_url = _build_url(url, params)
        return FakeContentFetcher(full_url, response=self.request(full_url, auth_cfg=auth_cfg))

    def fetch_blocking(self, url, params=None, auth_cfg=None, timeout=None):
        full_url = _build_url(url, params)
        return self.request(full_url, auth_cfg=auth_cfg, timeout=timeout)

    def session(self, **kwargs):
        return FakeSession(responses=self.responses, **kwargs)

    @classmethod
    def instance(cls, **kwargs):
        # For singleton pattern compatibility
        return cls(**kwargs)


class FakeSession(FakeNetworkManager):
    """Fake Session — requests-like Session for testing."""

    def __init__(self, responses=None, auth_cfg=None, timeout=15000, headers=None, params=None, verify=True):
        super().__init__(responses=responses, headers=headers)
        self.auth_cfg = auth_cfg
        self.timeout = timeout
        self.params = dict(params or {})
        self.verify = verify
        self.cookies: Dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        pass

    def request(self, method, url, params=None, data=None, json=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        # Merge session params/headers
        merged_params = dict(self.params)
        if params:
            merged_params.update(params)
        merged_headers = dict(self.headers)
        if headers:
            merged_headers.update(headers)
        return super().request(
            url,
            method=method,
            data=data,
            json=json,
            params=merged_params if merged_params else None,
            headers=merged_headers,
            auth_cfg=auth_cfg or self.auth_cfg,
            timeout=timeout or self.timeout,
            **kwargs,
        )

    # Override verb methods to use method-first signature
    def get(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("GET", url, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def post(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("POST", url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def put(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("PUT", url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def patch(self, url, data=None, json=None, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("PATCH", url, data=data, json=json, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def delete(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("DELETE", url, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def head(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("HEAD", url, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)

    def options(self, url, params=None, headers=None, auth_cfg=None, timeout=None, **kwargs):
        return self.request("OPTIONS", url, params=params, headers=headers, auth_cfg=auth_cfg, timeout=timeout, **kwargs)


class FakeContentFetcher:
    """Fake ContentFetcher — requests-like params support."""

    def __init__(self, url="", response: Optional[FakeNetworkResponse] = None, params=None):
        self.url = _build_url(url, params) if params else url
        self._response = response or FakeNetworkResponse(url=self.url)
        self._finished_callbacks: List[Callable] = []

    def fetch(self, url, params=None):
        self.url = _build_url(url, params) if params else url
        for cb in self._finished_callbacks:
            try:
                cb()
            except Exception:
                pass

    def fetch_blocking(self, url, params=None, timeout=None):
        self.url = _build_url(url, params) if params else url
        return self._response

    def content_as_string(self):
        return self._response.text

    def content_as_bytes(self):
        return self._response.content

    @property
    def finished(self):
        class _MockSignal:
            def __init__(self, outer):
                self.outer = outer

            def connect(self, cb):
                self.outer._finished_callbacks.append(cb)
                try:
                    cb()
                except Exception:
                    pass

        return _MockSignal(self)

    @property
    def reply(self):
        return None


def fake_network_manager_factory(responses=None, **kwargs):
    return FakeNetworkManager(responses, **kwargs)


def fake_network_response_factory(**kwargs):
    return FakeNetworkResponse(**kwargs)


def fake_content_fetcher_factory(**kwargs):
    return FakeContentFetcher(**kwargs)


def fake_session_factory(responses=None, **kwargs):
    return FakeSession(responses, **kwargs)


# ── Fake task manager (celery-like) ─────────────────────────────────────────

class FakeTask:
    """Fake Task — celery-like + QGIS-like for testing without QGIS."""

    def __init__(self, description="Task", function=None, *args, on_finished=None, can_cancel=True, bind=False, **kwargs):
        self.description = description
        self._function = function
        self._args = args
        self._kwargs = kwargs
        self._on_finished = on_finished
        self._can_cancel = can_cancel
        self._bind = bind
        self._is_canceled = False
        self._is_finished = False
        self._progress = 0
        self._result = None
        self._exception = None
        self._id = str(uuid.uuid4())
        self._state = "PENDING"

    @property
    def id(self):
        return self._id

    @property
    def task_id(self):
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def status(self):
        return self._state

    def run(self):
        if self._function:
            try:
                import inspect

                sig = inspect.signature(self._function)
                params = list(sig.parameters.values())
                if self._bind or (params and params[0].name in ("task", "self", "celery_task", "qgis_task", "bind_task")):
                    return self._function(self, *self._args, **self._kwargs)
                else:
                    return self._function(*self._args, **self._kwargs)
            except Exception as e:
                raise e
        return True

    def set_progress(self, progress):
        self._progress = progress

    def setProgress(self, progress):
        self._progress = progress

    def progress(self):
        return self._progress

    def is_canceled(self):
        return self._is_canceled

    def isCanceled(self):
        return self._is_canceled

    def is_finished(self):
        return self._is_finished

    def isFinished(self):
        return self._is_finished

    def cancel(self):
        self._is_canceled = True
        self._state = "REVOKED"

    def can_cancel(self):
        return self._can_cancel

    def canCancel(self):
        return self._can_cancel

    def finished(self, result):
        pass

    def _execute(self):
        self._state = "STARTED"
        try:
            result = self.run()
            self._result = result
            self._is_finished = True
            self._state = "SUCCESS"
            if self._on_finished:
                try:
                    self._on_finished(None, result)
                except Exception:
                    pass
            return result
        except Exception as e:
            self._exception = e
            self._is_finished = True
            self._state = "FAILURE"
            if self._on_finished:
                try:
                    self._on_finished(e, None)
                except Exception:
                    pass
            return None

    def result(self):
        return self._result

    def exception(self):
        return self._exception

    @classmethod
    def from_function(cls, description, function, *args, on_finished=None, flags=None, bind=False, **kwargs):
        return cls(description, function, *args, on_finished=on_finished, bind=bind, **kwargs)

    # Celery-like API
    def delay(self, *args, **kwargs):
        # For FakeTask used as function wrapper, delay creates new task
        new_task = FakeTask(self.description, self._function, *args, on_finished=self._on_finished, bind=self._bind, **{**self._kwargs, **kwargs})
        return FakeAsyncResult(new_task)

    def apply_async(self, args=None, kwargs=None, **options):
        args = args or ()
        kwargs = kwargs or {}
        return self.delay(*args, **kwargs)


class FakeAsyncResult:
    """Fake AsyncResult — celery-like."""

    def __init__(self, task: FakeTask):
        self._task = task
        # Auto-execute for sync testing
        if not task.is_finished():
            task._execute()

    @property
    def id(self):
        return self._task.id

    @property
    def task_id(self):
        return self._task.id

    def get(self, timeout=None, propagate=True):
        if self._task._exception and propagate:
            raise self._task._exception
        return self._task._result

    def wait(self, timeout=None, propagate=True):
        return self.get(timeout=timeout, propagate=propagate)

    def ready(self):
        return self._task.is_finished()

    def successful(self):
        return self._task.is_finished() and self._task._exception is None

    def failed(self):
        return self._task.is_finished() and self._task._exception is not None

    @property
    def result(self):
        return self._task._result

    @property
    def state(self):
        return self._task._state

    @property
    def status(self):
        return self.state

    def revoke(self, terminate=False):
        self._task.cancel()

    def __repr__(self):
        return f"<FakeAsyncResult [{self.state}] id={self.id}>"


class FakeSignature:
    """Fake Signature — celery-like."""

    def __init__(self, task, args=(), kwargs=None, immutable=False, options=None):
        self.task = task
        self.args = args
        self.kwargs = kwargs or {}
        self.immutable = immutable
        self.options = options or {}

    def delay(self, *args, **kwargs):
        if self.immutable:
            return self.task.delay(*self.args, **self.kwargs)
        merged_args = self.args + args
        merged_kwargs = {**self.kwargs, **kwargs}
        return self.task.delay(*merged_args, **merged_kwargs)

    def apply_async(self, args=None, kwargs=None, **options):
        if self.immutable:
            return self.task.delay(*self.args, **self.kwargs)
        merged_args = self.args + (args or ())
        merged_kwargs = {**self.kwargs, **(kwargs or {})}
        return self.task.delay(*merged_args, **merged_kwargs)

    def __call__(self, *args, **kwargs):
        if self.immutable:
            return self.task._function(*self.args, **self.kwargs) if hasattr(self.task, "_function") else self.task(*self.args, **self.kwargs)
        merged_args = self.args + args
        merged_kwargs = {**self.kwargs, **kwargs}
        # Direct call
        if hasattr(self.task, "_function") and self.task._function:
            import inspect

            sig = inspect.signature(self.task._function)
            params = list(sig.parameters.values())
            if params and params[0].name in ("task", "self"):
                dummy = FakeTask()
                return self.task._function(dummy, *merged_args, **merged_kwargs)
            return self.task._function(*merged_args, **merged_kwargs)
        return self.task(*merged_args, **merged_kwargs)


class FakeTaskWrapper:
    """Fake TaskWrapper — celery-like decorator result for testing."""

    def __init__(self, func, description="Task", bind=False, can_cancel=True, on_finished=None):
        self.func = func
        self.description = description
        self.bind = bind
        self.can_cancel = can_cancel
        self.on_finished = on_finished
        self.name = getattr(func, "__name__", "task")

    def __call__(self, *args, **kwargs):
        import inspect

        sig = inspect.signature(self.func)
        params = list(sig.parameters.values())
        if self.bind or (params and params[0].name in ("task", "self")):
            dummy = FakeTask(description=self.description, bind=self.bind)
            return self.func(dummy, *args, **kwargs)
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        task = FakeTask(self.description, self.func, *args, on_finished=self.on_finished, bind=self.bind, **kwargs)
        return FakeAsyncResult(task)

    def apply_async(self, args=None, kwargs=None, **options):
        args = args or ()
        kwargs = kwargs or {}
        return self.delay(*args, **kwargs)

    def s(self, *args, **kwargs):
        return FakeSignature(self, args, kwargs, immutable=False)

    def si(self, *args, **kwargs):
        return FakeSignature(self, args, kwargs, immutable=True)


class FakeTaskManager:
    """Fake TaskManager — celery-like + QGIS-like, synchronous for tests."""

    def __init__(self):
        self._tasks: List[FakeTask] = []
        self.added_tasks: List[FakeTask] = []
        self.results: List[FakeAsyncResult] = []

    def add_task(self, task, *args, **kwargs):
        # Handle TaskWrapper
        if isinstance(task, FakeTaskWrapper):
            async_res = task.delay(*args, **kwargs)
            self.added_tasks.append(async_res._task)
            self.results.append(async_res)
            return async_res

        # Handle Signature
        if isinstance(task, FakeSignature):
            async_res = task.delay(*args, **kwargs)
            self.added_tasks.append(async_res._task)
            self.results.append(async_res)
            return async_res

        # Handle callable or FakeTask
        if callable(task) and not isinstance(task, FakeTask):
            description = kwargs.pop("description", "Task")
            on_finished = kwargs.pop("on_finished", None)
            bind = kwargs.pop("bind", False)
            t = FakeTask(description, task, *args, on_finished=on_finished, bind=bind, **kwargs)
        else:
            t = task

        self._tasks.append(t)
        self.added_tasks.append(t)

        # Execute immediately (synchronous for tests)
        result = FakeAsyncResult(t)
        self._tasks.remove(t)
        self.results.append(result)
        return result if isinstance(task, FakeTaskWrapper) or kwargs.get("return_async", True) else t

    def tasks(self):
        return list(self._tasks)

    def count(self):
        return len(self._tasks)

    def cancel_all(self):
        for t in self._tasks:
            t.cancel()


def fake_task_manager_factory():
    return FakeTaskManager()


def fake_task_factory(description="Task", function=None, *args, **kwargs):
    return FakeTask(description, function, *args, **kwargs)


# ── Pytest fixtures ─────────────────────────────────────────────────────────

try:
    import pytest

    @pytest.fixture
    def fake_iface():
        return FakeIface()

    @pytest.fixture(name="fake_action_factory")
    def _fixture_fake_action_factory():
        return fake_action_factory

    @pytest.fixture
    def fake_context():
        return FakeContext()

    @pytest.fixture(name="fake_dialog_factory")
    def _fixture_fake_dialog_factory():
        return fake_dialog_factory

    @pytest.fixture(name="fake_webview_factory")
    def _fixture_fake_webview_factory():
        return fake_webview_factory

    @pytest.fixture
    def fake_bridge():
        return FakeBridge()

    @pytest.fixture(name="fake_dialog")
    def _fixture_fake_dialog():
        return FakeDialog()

    @pytest.fixture(name="fake_webview")
    def _fixture_fake_webview():
        return FakeWebView()

    @pytest.fixture
    def mock_features_fixture():
        return mock_features

    @pytest.fixture
    def mock_source_fixture():
        return mock_source

    @pytest.fixture
    def mock_context_fixture():
        return mock_context

    @pytest.fixture(name="mock_features")
    def _fixture_mock_features():
        return mock_features

    @pytest.fixture(name="mock_source")
    def _fixture_mock_source():
        return mock_source

    @pytest.fixture(name="mock_context")
    def _fixture_mock_context():
        return mock_context

    @pytest.fixture
    def fake_network_response():
        return FakeNetworkResponse()

    @pytest.fixture(name="fake_network_manager")
    def _fixture_fake_network_manager():
        return FakeNetworkManager()

    @pytest.fixture(name="fake_content_fetcher")
    def _fixture_fake_content_fetcher():
        return FakeContentFetcher()

    @pytest.fixture(name="fake_session")
    def _fixture_fake_session():
        return FakeSession()

    @pytest.fixture
    def fake_task():
        return FakeTask()

    @pytest.fixture(name="fake_task_manager")
    def _fixture_fake_task_manager():
        return FakeTaskManager()

    @pytest.fixture(name="fake_async_result")
    def _fixture_fake_async_result():
        t = FakeTask("Test", lambda: 42)
        return FakeAsyncResult(t)

    @pytest.fixture(name="fake_task_wrapper")
    def _fixture_fake_task_wrapper():
        def my_func(x, y):
            return x + y

        return FakeTaskWrapper(my_func, description="Test task")

except ImportError:
    pass


# ── Entry point for pytest plugin ───────────────────────────────────────────

def pytest_configure(config):
    """Register markers for qgis_sdk tests."""
    config.addinivalue_line("markers", "qgis: mark test as requiring QGIS")
    config.addinivalue_line("markers", "webengine: mark test as requiring QWebEngine")
    config.addinivalue_line("markers", "network: mark test as requiring network")
    config.addinivalue_line("markers", "tasks: mark test as requiring QgsTaskManager")


__all__ = [
    "FakeAction",
    "FakeIface",
    "FakeContext",
    "FakeSink",
    "FakeFeature",
    "FakeGeometry",
    "FakeFields",
    "FakeDialog",
    "FakeDialogWidget",
    "FakeWebView",
    "FakeWebPage",
    "FakeWebChannel",
    "FakeBridge",
    "FakeNetworkResponse",
    "FakeNetworkManager",
    "FakeSession",
    "FakeContentFetcher",
    "FakeTask",
    "FakeAsyncResult",
    "FakeSignature",
    "FakeTaskWrapper",
    "FakeTaskManager",
    "fake_action_factory",
    "fake_dialog_factory",
    "fake_webview_factory",
    "fake_bridge_factory",
    "fake_network_manager_factory",
    "fake_network_response_factory",
    "fake_content_fetcher_factory",
    "fake_session_factory",
    "fake_task_manager_factory",
    "fake_task_factory",
    "mock_features",
    "mock_source",
    "mock_context",
]
