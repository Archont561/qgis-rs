"""qgis_sdk.plugin.registry — global registry for declarative decorators.

Inspired by FastAPI, Celery, click.

Registry holds plugins, actions, tasks, bridges, settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type


@dataclass
class ActionSpec:
    func: Callable
    func_name: str
    toolbar: Optional[str] = None
    menu: Optional[tuple] = None
    tooltip: str = ""
    icon: Optional[str] = None
    cls: Optional[Type] = None  # plugin class that owns it


@dataclass
class TaskSpec:
    wrapper: Any  # TaskWrapper
    func: Callable
    description: str
    cls: Optional[Type] = None


@dataclass
class BridgeSpec:
    cls: Type
    name: str
    description: Optional[str] = None
    plugin_cls: Optional[Type] = None


@dataclass
class SettingSpec:
    func: Callable
    default: Any = None
    persist: bool = True
    cls: Optional[Type] = None


@dataclass
class PluginMeta:
    cls: Type
    metadata: Dict[str, Any]
    actions: List[ActionSpec] = field(default_factory=list)
    tasks: List[TaskSpec] = field(default_factory=list)
    bridges: List[BridgeSpec] = field(default_factory=list)
    settings: List[SettingSpec] = field(default_factory=list)


class PluginRegistry:
    def __init__(self):
        self.plugins: Dict[str, PluginMeta] = {}
        self._actions: Dict[str, List[ActionSpec]] = {}  # plugin class name -> actions
        self._tasks: Dict[str, TaskSpec] = {}  # task name -> spec
        self._bridges: Dict[str, BridgeSpec] = {}
        self._settings: Dict[str, List[SettingSpec]] = {}

    def register_plugin(self, cls: Type, metadata: Dict[str, Any]):
        key = cls.__name__
        if key not in self.plugins:
            self.plugins[key] = PluginMeta(cls=cls, metadata=metadata)
        else:
            self.plugins[key].metadata.update(metadata)
            self.plugins[key].cls = cls
        # Ensure actions list exists
        self._actions.setdefault(key, [])

    def register_action(self, func: Callable, toolbar: Optional[str] = None, menu: Optional[tuple] = None, tooltip: str = "", icon: Optional[str] = None, cls: Optional[Type] = None):
        # Determine owning plugin class from func's qualname or explicit cls
        # For simplicity, store without cls and later associate via decorator order
        spec = ActionSpec(
            func=func,
            func_name=func.__name__,
            toolbar=toolbar,
            menu=menu,
            tooltip=tooltip,
            icon=icon,
            cls=cls,
        )
        # If cls provided, add to its list
        if cls:
            key = cls.__name__
            self._actions.setdefault(key, []).append(spec)
            if key in self.plugins:
                self.plugins[key].actions.append(spec)
        else:
            # Store in generic bucket, will be associated when plugin decorator runs
            # Use func's module + qualname to track
            # For now, store in _pending_actions
            if not hasattr(self, "_pending_actions"):
                self._pending_actions: List[ActionSpec] = []
            self._pending_actions.append(spec)
        return spec

    def register_task(self, wrapper: Any, func: Callable = None, description: str = "Task", cls: Optional[Type] = None):
        task_name = getattr(wrapper, "name", getattr(func, "__name__", "task")) if func or wrapper else "task"
        spec = TaskSpec(wrapper=wrapper, func=func or wrapper.func if hasattr(wrapper, "func") else wrapper, description=description, cls=cls)
        self._tasks[task_name] = spec
        if cls:
            key = cls.__name__
            if key in self.plugins:
                self.plugins[key].tasks.append(spec)
        else:
            # Check pending
            if not hasattr(self, "_pending_tasks"):
                self._pending_tasks: List[TaskSpec] = []
            self._pending_tasks.append(spec)
        return spec

    def get_task(self, name: str) -> Optional[Any]:
        spec = self._tasks.get(name)
        if spec:
            return spec.wrapper
        # Try find by func name
        for spec in self._tasks.values():
            if spec.func.__name__ == name:
                return spec.wrapper
        return None

    def register_bridge(self, cls: Type, name: str, description: Optional[str] = None, plugin_cls: Optional[Type] = None):
        spec = BridgeSpec(cls=cls, name=name, description=description, plugin_cls=plugin_cls)
        self._bridges[name] = spec
        if plugin_cls:
            key = plugin_cls.__name__
            if key in self.plugins:
                self.plugins[key].bridges.append(spec)
        return spec

    def register_setting(self, func: Callable, default: Any = None, persist: bool = True, cls: Optional[Type] = None):
        spec = SettingSpec(func=func, default=default, persist=persist, cls=cls)
        if cls:
            key = cls.__name__
            self._settings.setdefault(key, []).append(spec)
            if key in self.plugins:
                self.plugins[key].settings.append(spec)
        else:
            if not hasattr(self, "_pending_settings"):
                self._pending_settings: List[SettingSpec] = []
            self._pending_settings.append(spec)
        return spec

    def get_actions(self, plugin_cls: Type) -> List[ActionSpec]:
        key = plugin_cls.__name__
        # Merge registered actions for this class + pending that belong to it
        actions = list(self._actions.get(key, []))
        # Also check plugins meta
        if key in self.plugins:
            # Avoid duplicates
            existing_names = {a.func_name for a in actions}
            for a in self.plugins[key].actions:
                if a.func_name not in existing_names:
                    actions.append(a)

        # Also try to find pending actions whose func is defined in plugin_cls
        if hasattr(self, "_pending_actions"):
            for pending in self._pending_actions:
                # If pending func is in plugin_cls's dict
                if pending.func.__name__ in dir(plugin_cls):
                    # Check if func is same object or name matches
                    try:
                        attr = getattr(plugin_cls, pending.func.__name__)
                        if attr == pending.func or getattr(attr, "__name__", None) == pending.func.__name__:
                            if pending.func_name not in {a.func_name for a in actions}:
                                actions.append(pending)
                    except Exception:
                        pass

        return actions

    def get_plugin(self, cls_or_name) -> Optional[PluginMeta]:
        if isinstance(cls_or_name, str):
            return self.plugins.get(cls_or_name)
        return self.plugins.get(cls_or_name.__name__)

    def clear(self):
        self.plugins.clear()
        self._actions.clear()
        self._tasks.clear()
        self._bridges.clear()
        self._settings.clear()
        if hasattr(self, "_pending_actions"):
            self._pending_actions.clear()
        if hasattr(self, "_pending_tasks"):
            self._pending_tasks.clear()
        if hasattr(self, "_pending_settings"):
            self._pending_settings.clear()


# Global registry
registry = PluginRegistry()
