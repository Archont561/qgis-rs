"""qgis_sdk.bridge.window — Window-like EventTarget for Python side.

Provides EventSource/WebSocket-like API for Python to dispatch events to JS.

Python side:
    window = bridge_runtime.to_window()
    window.add_event_listener("message", lambda e: print(e.data))
    window.send({"status": "ready"})
    window.dispatch_event("layer_changed", {"layer_id": "test"})
    window.post_message({"action": "buffer"})

JS side counterpart is QgisBridge extends EventTarget in @qgis-sdk/bridge.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional


class Event:
    def __init__(self, type: str, detail: Any = None, data: Any = None):
        self.type = type
        self.detail = detail
        self.data = data if data is not None else detail


class EventTarget:
    """Minimal EventTarget like browser."""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def add_event_listener(self, event: str, callback: Callable):
        self._listeners.setdefault(event, []).append(callback)

    def addEventListener(self, event: str, callback: Callable, options: Any = None):
        self.add_event_listener(event, callback)

    def remove_event_listener(self, event: str, callback: Callable):
        if event in self._listeners:
            try:
                self._listeners[event].remove(callback)
            except ValueError:
                pass

    def removeEventListener(self, event: str, callback: Callable):
        self.remove_event_listener(event, callback)

    def dispatch_event(self, event: str, data: Any = None) -> bool:
        evt = Event(event, detail=data, data=data)
        listeners = self._listeners.get(event, [])
        for cb in listeners:
            try:
                cb(evt)
            except Exception as e:
                print(f"[BridgeWindow] listener error for {event}: {e}")
        return True

    def dispatchEvent(self, event: Any) -> bool:
        # If event is string, treat as type
        if isinstance(event, str):
            return self.dispatch_event(event)
        # If event has type attribute
        etype = getattr(event, "type", "message")
        detail = getattr(event, "detail", None) or getattr(event, "data", None)
        return self.dispatch_event(etype, detail)


class BridgeWindow(EventTarget):
    """Window-like object for Python → JS communication.

    Wraps a webview and allows sending events to JS via runJavaScript.

    Like WebSocket + EventSource:
    - send(data): sends message event to JS
    - post_message(data): alias
    - dispatch_event(event, data): dispatches CustomEvent to JS
    - close(): closes
    - readyState: CONNECTING/OPEN/CLOSED
    """

    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3

    def __init__(self, runtime: Any = None, webview: Any = None):
        super().__init__()
        self.runtime = runtime
        self.webview = webview
        self.readyState = self.CONNECTING
        self.url = "qgis://bridge"
        self._closed = False

    def _run_js(self, js: str):
        if self.webview is None and self.runtime and hasattr(self.runtime, "webview"):
            webview = self.runtime.webview
        else:
            webview = self.webview

        if webview is None:
            # No webview — just dispatch locally (for testing)
            return

        try:
            # Try QWebEngineView page().runJavaScript
            if hasattr(webview, "page"):
                page = webview.page()
                if hasattr(page, "runJavaScript"):
                    page.runJavaScript(js)
                    return
            # Fallback: webview.runJavaScript
            if hasattr(webview, "runJavaScript"):
                webview.runJavaScript(js)
        except Exception as e:
            print(f"[BridgeWindow] runJavaScript failed: {e}")

    def send(self, data: Any):
        """Send message to JS — like WebSocket send()."""
        try:
            json_data = json.dumps(data)
        except Exception:
            json_data = json.dumps(str(data))
        js = f"""
        (function() {{
            if (window.qgisBridge) {{
                window.qgisBridge.dispatchEvent(new MessageEvent('message', {{data: {json_data}}}));
                if (window.qgisBridge.onmessage) window.qgisBridge.onmessage(new MessageEvent('message', {{data: {json_data}}}));
            }}
            if (window.qgis) {{
                window.qgis.dispatchEvent(new CustomEvent('message', {{detail: {json_data}}}));
            }}
            window.dispatchEvent(new CustomEvent('qgis-bridge-message', {{detail: {json_data}}}));
        }})();
        """
        self._run_js(js)
        # Also dispatch locally for Python listeners
        self.dispatch_event("message", data)

    def post_message(self, data: Any, target_origin: str = "*"):
        self.send(data)

    def postMessage(self, data: Any, target_origin: str = "*"):
        self.send(data)

    def dispatch_event(self, event: str, data: Any = None) -> bool:
        # Dispatch locally first
        super().dispatch_event(event, data)
        # Then dispatch to JS
        try:
            json_data = json.dumps(data) if data is not None else "null"
        except Exception:
            json_data = json.dumps(str(data)) if data is not None else "null"

        js = f"""
        (function() {{
            var detail = {json_data};
            var ev = new CustomEvent('{event}', {{detail: detail}});
            if (window.qgisBridge) window.qgisBridge.dispatchEvent(ev);
            if (window.qgis) window.qgis.dispatchEvent(ev);
            window.dispatchEvent(ev);
        }})();
        """
        self._run_js(js)
        return True

    def close(self, code: int = 1000, reason: str = ""):
        self.readyState = self.CLOSED
        self._closed = True
        js = f"""
        (function() {{
            if (window.qgisBridge) {{
                window.qgisBridge.readyState = 3;
                window.qgisBridge.dispatchEvent(new CloseEvent('close', {{code: {code}, reason: '{reason}'}}));
                if (window.qgisBridge.onclose) window.qgisBridge.onclose(new CloseEvent('close', {{code: {code}, reason: '{reason}'}}));
            }}
        }})();
        """
        self._run_js(js)
        self.dispatch_event("close", {"code": code, "reason": reason})

    def open(self):
        self.readyState = self.OPEN
        js = """
        (function() {
            if (window.qgisBridge) {
                window.qgisBridge.readyState = 1;
                window.qgisBridge.dispatchEvent(new Event('open'));
                if (window.qgisBridge.onopen) window.qgisBridge.onopen(new Event('open'));
            }
        })();
        """
        self._run_js(js)
        self.dispatch_event("open", {})

    def __repr__(self):
        return f"<BridgeWindow readyState={self.readyState} url={self.url}>"


# For backwards compat
Window = BridgeWindow
