"""Fake dialogs, widgets and web views — the UI seam without Qt.

These stand in for ``QDialog``, ``QWebEngineView`` and ``QWebChannel`` so a
dialog's *logic* (field values, accept/reject, what JavaScript it ran) can be
tested in a pure process. They are not a Qt reimplementation: a test that
needs real widget behaviour belongs behind the ``qt`` marker and the
``qt_app`` fixture, where a real ``QApplication`` exists.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .calls import CallLog, call_log


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

    def setText(self, t):  # noqa: N802 - Qt naming
        self._text = t

    def value(self):
        return self._value

    def setValue(self, v):  # noqa: N802 - Qt naming
        self._value = v

    def isChecked(self):  # noqa: N802 - Qt naming
        return self._checked

    def setChecked(self, c):  # noqa: N802 - Qt naming
        self._checked = c

    def currentText(self):  # noqa: N802 - Qt naming
        return self._current_text

    def setCurrentText(self, t):  # noqa: N802 - Qt naming
        self._current_text = t

    def currentLayer(self):  # noqa: N802 - Qt naming
        return self._current_layer


class FakeDialog:
    """Fake QDialog for testing dialog logic without Qt."""

    Accepted = 1
    Rejected = 0

    def __init__(self, values=None, calls: Optional[CallLog] = None):
        self.values = values or {}
        self.calls = call_log(calls)
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
        self.calls.record("ui", "dialog.exec", accepted=self._accepted)
        return FakeDialog.Accepted if self._accepted else FakeDialog.Rejected

    def accept(self):
        self.calls.record("ui", "dialog.accept")
        self._accepted = True

    def reject(self):
        self.calls.record("ui", "dialog.reject")
        self._accepted = False


class FakeWebPage:
    """Fake QWebEnginePage."""

    def __init__(self, calls: Optional[CallLog] = None):
        self.js_calls: List[str] = []
        self.html = ""
        self.url = ""
        self.calls = call_log(calls)

    def runJavaScript(self, js_code, callback=None):  # noqa: N802 - Qt naming
        self.js_calls.append(js_code)
        self.calls.record("ui", "webview.run_javascript", script=js_code)
        if callback:
            callback(f"result of {js_code[:20]}")

    def setWebChannel(self, channel):  # noqa: N802 - Qt naming
        self.channel = channel


class FakeWebView:
    """Fake QWebEngineView."""

    def __init__(self, parent=None, calls: Optional[CallLog] = None):
        self.calls = call_log(calls)
        self._page = FakeWebPage(calls=self.calls)
        self.parent = parent
        self.html = ""
        self.url = ""

    def page(self):
        return self._page

    def setHtml(self, html, baseUrl=None):  # noqa: N802 - Qt naming
        self.calls.record("ui", "webview.set_html", length=len(html))
        self.html = html
        self._page.html = html

    def setUrl(self, url):  # noqa: N802 - Qt naming
        self.calls.record("ui", "webview.set_url", url=str(url))
        self.url = str(url)
        self._page.url = str(url)


class FakeWebChannel:
    """Fake QWebChannel."""

    def __init__(self):
        self.objects: Dict[str, Any] = {}

    def registerObject(self, name, obj):  # noqa: N802 - Qt naming
        self.objects[name] = obj


def _make_fake_dialog(values=None):
    return FakeDialog(values)


def fake_dialog_factory(values=None):
    """Factory for FakeDialog."""
    return FakeDialog(values)


def _make_fake_webview(html=""):
    view = FakeWebView()
    view.setHtml(html)
    return view


def fake_webview_factory(html=""):
    """Factory for FakeWebView."""
    view = FakeWebView()
    view.setHtml(html)
    return view


__all__ = [
    "FakeDialog",
    "FakeDialogWidget",
    "FakeWebView",
    "FakeWebPage",
    "FakeWebChannel",
    "fake_dialog_factory",
    "fake_webview_factory",
]
