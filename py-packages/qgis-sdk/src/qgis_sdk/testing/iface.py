"""Fake ``QgisInterface`` and the actions a plugin hangs off it.

Pure Python: nothing here imports Qt or QGIS. The fake records what a plugin
did to the host — toolbar icons, menu entries, messages — both in the lists
existing tests assert on and in a shared :class:`~qgis_sdk.testing.calls.CallLog`.
"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

from .calls import CallLog, call_log


class FakeAction:
    """Fake QAction — stands in for QgisInterface toolbar/menu actions."""

    def __init__(self, spec, callback: Callable[[], None], calls: Optional[CallLog] = None):
        self.spec = spec
        self.callback = callback
        self.triggered = 0
        self.objectName = f"qgis_sdk_{spec.func_name}" if hasattr(spec, "func_name") else "fake_action"
        self.tooltip = getattr(spec, "tooltip", "")
        self.icon = getattr(spec, "icon", None)
        self.calls = call_log(calls)

    def trigger(self):
        self.triggered += 1
        self.calls.record("iface", "action.trigger", name=self.objectName)
        self.callback()

    def setObjectName(self, name: str):  # noqa: N802 - PyQt naming
        self.objectName = name


class FakeIface:
    """Fake QgisInterface — minimal impl for plugin lifecycle tests."""

    def __init__(self, calls: Optional[CallLog] = None):
        self.toolbar_icons: List[Any] = []
        self.menu_entries: List[Tuple[str, Any]] = []
        self.messages: List[str] = []
        self.calls = call_log(calls)
        self._main_window = None

    def addToolBarIcon(self, widget):  # noqa: N802 - PyQGIS naming
        self.calls.record("iface", "toolbar.add", widget=widget)
        self.toolbar_icons.append(widget)

    def addPluginToMenu(self, path, widget):  # noqa: N802 - PyQGIS naming
        self.calls.record("iface", "menu.add", path=path, widget=widget)
        self.menu_entries.append((path, widget))

    def removeToolBarIcon(self, widget):  # noqa: N802 - PyQGIS naming
        self.calls.record("iface", "toolbar.remove", widget=widget)
        if widget in self.toolbar_icons:
            self.toolbar_icons.remove(widget)

    def removePluginMenu(self, path, widget):  # noqa: N802 - PyQGIS naming
        self.calls.record("iface", "menu.remove", path=path, widget=widget)
        if (path, widget) in self.menu_entries:
            self.menu_entries.remove((path, widget))

    def messageBar(self):  # noqa: N802 - PyQGIS naming
        return self

    def pushMessage(self, text, level=0, duration=5):  # noqa: N802
        self.calls.record("iface", "message.push", text=text, level=level, duration=duration)
        self.messages.append(text)

    def message(self, text):
        self.calls.record("iface", "message.push", text=text)
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


__all__ = ["FakeAction", "FakeIface", "fake_action_factory"]
