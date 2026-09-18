"""Plugin declaration, decorators, and the initGui/unload lifecycle.

A fake interface and a fake action factory stand in for ``QgisInterface`` and
``QAction``, so these tests run without QGIS or Qt.
"""

from __future__ import annotations

import pytest

from qgis_sdk import Plugin, action, class_factory, menu, toolbar


class FakeAction:
    def __init__(self, spec, callback):
        self.spec = spec
        self.callback = callback
        self.triggered = 0

    def trigger(self):
        self.triggered += 1
        self.callback()


class FakeIface:
    def __init__(self):
        self.toolbar_icons = []
        self.menu_entries = []
        self.messages = []

    def addToolBarIcon(self, widget):  # noqa: N802 - PyQGIS naming
        self.toolbar_icons.append(widget)

    def addPluginToMenu(self, path, widget):  # noqa: N802 - PyQGIS naming
        self.menu_entries.append((path, widget))

    def removeToolBarIcon(self, widget):  # noqa: N802 - PyQGIS naming
        self.toolbar_icons.remove(widget)

    def removePluginMenu(self, path, widget):  # noqa: N802 - PyQGIS naming
        self.menu_entries.remove((path, widget))

    def message(self, text):
        self.messages.append(text)


def factory(spec, callback):
    return FakeAction(spec, callback)


class Sample(Plugin):
    name = "Sample"
    version = "0.1.0"
    author = "Tester"
    email = "t@example.org"

    action_factory = staticmethod(factory)

    @toolbar("Sample Toolbar")
    @action(tooltip="Run the tool", icon="icons/tool.svg")
    def run_tool(self, iface):
        iface.message("tool ran")

    @menu("Plugins", "Sample")
    @action(tooltip="Open settings")
    def open_settings(self, iface):
        iface.message("settings opened")

    @action(tooltip="Not wired to the UI")
    def headless(self, iface):
        iface.message("headless ran")


def test_actions_are_collected_in_declaration_order():
    assert [spec.func_name for spec in Sample.actions()] == [
        "run_tool",
        "open_settings",
        "headless",
    ]


def test_decorator_arguments_are_recorded():
    run_tool = Sample.actions()[0]
    assert run_tool.tooltip == "Run the tool"
    assert run_tool.icon == "icons/tool.svg"
    assert run_tool.toolbar == "Sample Toolbar"
    assert run_tool.menu == ()


def test_menu_path_joins_components():
    assert Sample.actions()[1].menu_path == "Plugins/Sample"


def test_toolbar_and_menu_require_action_first():
    with pytest.raises(TypeError, match="not @action"):

        class Broken(Plugin):
            @toolbar("Nope")
            def no_action(self, iface):
                pass


def test_menu_needs_a_path():
    with pytest.raises(ValueError, match="at least one path"):
        menu()


def test_init_gui_adds_toolbar_icon_and_menu_entry():
    iface = FakeIface()
    plugin = Sample(iface)
    plugin.init_gui()

    assert len(iface.toolbar_icons) == 1
    assert iface.menu_entries[0][0] == "Plugins/Sample"
    # The action with no toolbar/menu is created but not attached.
    assert len(iface.toolbar_icons) + len(iface.menu_entries) == 2


def test_triggering_an_action_calls_the_method():
    iface = FakeIface()
    plugin = Sample(iface)
    plugin.init_gui()

    iface.toolbar_icons[0].trigger()
    assert iface.messages == ["tool ran"]


def test_unload_removes_everything():
    iface = FakeIface()
    plugin = Sample(iface)
    plugin.init_gui()
    plugin.unload()

    assert iface.toolbar_icons == []
    assert iface.menu_entries == []


def test_init_gui_without_iface_raises():
    with pytest.raises(RuntimeError, match="needs an interface"):
        Sample().init_gui()


def test_class_factory_builds_the_plugin():
    iface = FakeIface()
    factory_fn = class_factory(Sample)
    assert factory_fn.__name__ == "classFactory"
    plugin = factory_fn(iface)
    assert isinstance(plugin, Sample)
    assert plugin.iface is iface


def test_inherited_actions_are_included():
    class Extended(Sample):
        @action(tooltip="Extra")
        def extra(self, iface):
            iface.message("extra ran")

    assert [spec.func_name for spec in Extended.actions()] == [
        "run_tool",
        "open_settings",
        "headless",
        "extra",
    ]
