"""qgis_sdk.plugin — declarative plugin API.

New declarative API:
    from qgis_sdk import plugin, toolbar, action, task, setting

    @plugin(name="My Plugin", version="0.1.0", permissions=["layers","tasks"])
    class MyPlugin:
        @toolbar("My Toolbar")
        @action(tooltip="Run")
        def run(self, iface): ...

Old API still works via Plugin base class.
"""

from .base import Plugin, ActionSpec, class_factory, action as old_action, toolbar as old_toolbar, menu as old_menu
from .registry import registry, PluginRegistry
from .decorators import plugin, toolbar, action, menu, setting, task

__all__ = [
    "Plugin",
    "ActionSpec",
    "PluginRegistry",
    "registry",
    "class_factory",
    "plugin",
    "toolbar",
    "action",
    "menu",
    "setting",
    "task",
    # old aliases
    "old_action",
    "old_toolbar",
    "old_menu",
]
