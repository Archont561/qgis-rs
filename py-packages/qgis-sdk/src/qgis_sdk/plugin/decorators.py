"""qgis_sdk.plugin.decorators — declarative decorators @plugin, @toolbar, @action, etc.

Provides new declarative API while keeping backwards compat with old Plugin base class.

Usage:
    from qgis_sdk import plugin, toolbar, action, task, setting

    @plugin(name="My Plugin", version="0.1.0", author="Me", qgis_min_version="3.28", permissions=["layers","tasks"])
    class MyPlugin:
        @setting(default=10.0, persist=True)
        def distance(self): return 10.0

        @toolbar("My Toolbar")
        @action(tooltip="Run", icon="icons/run.svg")
        def run(self, iface, distance: float = None):
            ...
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Type

from .registry import registry
from .base import Plugin as PluginBase, ActionSpec as OldActionSpec
from ..metadata import render_metadata


def plugin(
    name: str = "",
    version: str = "0.1.0",
    description: str = "",
    about: str = None,
    author: str = "",
    email: str = "",
    category: str = None,
    tags: tuple = (),
    qgis_min_version: str = "3.28",
    qgis_max_version: str = None,
    homepage: str = None,
    repository: str = None,
    tracker: str = None,
    experimental: bool = False,
    deprecated: bool = False,
    has_processing_provider: bool = False,
    server: bool = False,
    icon: str = None,
    changelog: str = None,
    plugin_dependencies: str = None,
    permissions: list = None,
    algorithms: list | None = None,
    **extra,
):
    """Class decorator to declare a plugin.

    Creates metadata.txt, classFactory, init_gui from registry.

    Args:
        name, version, description, etc: metadata for metadata.txt
        permissions: list of permissions for JS qgis API, e.g. ["layers", "tasks", "network", "message"]
        **extra: additional metadata fields
    """

    def decorator(cls: Type) -> Type:
        metadata = {
            "name": name or getattr(cls, "name", ""),
            "version": version or getattr(cls, "version", "0.1.0"),
            "description": description or getattr(cls, "description", ""),
            "about": about or getattr(cls, "about", None),
            "author": author or getattr(cls, "author", ""),
            "email": email or getattr(cls, "email", ""),
            "category": category or getattr(cls, "category", None),
            "tags": tags or getattr(cls, "tags", ()),
            "qgis_min_version": qgis_min_version or getattr(cls, "qgis_min_version", "3.28"),
            "qgis_max_version": qgis_max_version or getattr(cls, "qgis_max_version", None),
            "homepage": homepage or getattr(cls, "homepage", None),
            "repository": repository or getattr(cls, "repository", None),
            "tracker": tracker or getattr(cls, "tracker", None),
            "experimental": experimental or getattr(cls, "experimental", False),
            "deprecated": deprecated or getattr(cls, "deprecated", False),
            "has_processing_provider": has_processing_provider or getattr(cls, "has_processing_provider", False),
            "server": server or getattr(cls, "server", False),
            "icon": icon or getattr(cls, "icon", None),
            "changelog": changelog or getattr(cls, "changelog", None),
            "plugin_dependencies": plugin_dependencies or getattr(cls, "plugin_dependencies", None),
            "permissions": permissions or [],
            **extra,
        }

        if algorithms is not None:
            metadata["algorithms"] = list(algorithms)
            cls.algorithms = list(algorithms)

        # Register plugin
        registry.register_plugin(cls, metadata)

        # Inject resolved attributes for backwards compatibility. The metadata
        # mapping already prefers explicit class values when decorator arguments
        # are omitted, so assigning it here keeps metadata_txt(), processing
        # discovery, and the registry in sync for both standalone classes and
        # Plugin subclasses.
        for k, v in metadata.items():
            setattr(cls, k, v)

        # Store metadata
        cls._qgis_sdk_metadata = metadata
        cls._qgis_sdk_registry = registry
        cls._qgis_sdk_permissions = permissions or []

        # Ensure cls has actions() method like old Plugin
        if not hasattr(cls, "actions"):
            # Provide actions() that uses registry
            @classmethod
            def actions(klass):
                specs = registry.get_actions(klass)
                # Convert to old ActionSpec for compatibility
                old_specs = []
                for s in specs:
                    old = OldActionSpec(
                        func_name=s.func_name,
                        tooltip=s.tooltip,
                        icon=s.icon,
                        toolbar=s.toolbar,
                        menu=s.menu or (),
                    )
                    old_specs.append(old)
                # Also include old-style actions declared via @action decorator in base.py
                # Check MRO for __qgis_sdk_action__
                for klass2 in reversed(klass.__mro__):
                    for attr_name, val in vars(klass2).items():
                        old_attr = getattr(val, "__qgis_sdk_action__", None)
                        if old_attr:
                            # Avoid duplicates
                            if old_attr.func_name not in {o.func_name for o in old_specs}:
                                old_specs.append(old_attr)
                return old_specs

            cls.actions = actions

        if not hasattr(cls, "metadata_txt"):
            @classmethod
            def metadata_txt(klass):
                return render_metadata(klass)

            cls.metadata_txt = metadata_txt

        # A declarative plugin does not need to inherit Plugin. Inject the small
        # lifecycle/action surface that PluginBase provides so @plugin works as
        # a real class decorator, not only as a metadata marker. Existing Plugin
        # subclasses retain their own inherited constructor and implementation.
        is_plugin_subclass = isinstance(cls, type) and issubclass(cls, PluginBase)
        if not is_plugin_subclass:
            original_init = cls.__dict__.get("__init__")
            if original_init is None:
                def __init__(self, iface=None):
                    self.iface = iface
                    self._created = []
                    self._processing_provider = None
            else:
                def __init__(self, *args, **kwargs):
                    original_init(self, *args, **kwargs)
                    if getattr(self, "iface", None) is None:
                        self.iface = kwargs.get("iface", args[0] if args else None)
                    self._created = list(getattr(self, "_created", []))
                    self._processing_provider = getattr(self, "_processing_provider", None)

            cls.__init__ = __init__

        if not is_plugin_subclass:
            for method_name in ("_create_action", "_invoke", "_init_processing_provider", "_unload_processing_provider"):
                if not hasattr(cls, method_name):
                    setattr(cls, method_name, getattr(PluginBase, method_name))
            if not hasattr(cls, "action_factory"):
                cls.action_factory = None
            if not hasattr(cls, "on_init"):
                cls.on_init = lambda self, iface: None
            if not hasattr(cls, "on_unload"):
                cls.on_unload = lambda self, iface: None

        # Inject init_gui and unload if not present, using the same lifecycle as
        # the base-class API but sourcing actions from the global registry.
        if "init_gui" not in cls.__dict__:
            def init_gui(self, iface=None):
                if iface is not None:
                    self.iface = iface
                if self.iface is None:
                    raise RuntimeError("init_gui() needs an interface")

                for spec in registry.get_actions(self.__class__):
                    old_spec = OldActionSpec(
                        func_name=spec.func_name,
                        tooltip=spec.tooltip,
                        icon=spec.icon,
                        toolbar=spec.toolbar,
                        menu=spec.menu or (),
                    )
                    widget = self._create_action(old_spec)
                    self._created.append((old_spec, widget))
                    if old_spec.toolbar and hasattr(self.iface, "addToolBarIcon"):
                        self.iface.addToolBarIcon(widget)
                    if old_spec.menu and hasattr(self.iface, "addPluginToMenu"):
                        self.iface.addPluginToMenu(old_spec.menu_path, widget)

                self._init_processing_provider()
                self.on_init(self.iface)

            cls.init_gui = init_gui

        if "unload" not in cls.__dict__:
            def unload(self, iface=None):
                if iface is not None:
                    self.iface = iface
                self._unload_processing_provider()
                for spec, widget in reversed(getattr(self, "_created", [])):
                    try:
                        if spec.toolbar and self.iface is not None and hasattr(self.iface, "removeToolBarIcon"):
                            self.iface.removeToolBarIcon(widget)
                        if spec.menu and self.iface is not None and hasattr(self.iface, "removePluginMenu"):
                            self.iface.removePluginMenu(spec.menu_path, widget)
                    except Exception:
                        pass
                self._created.clear()
                self.on_unload(self.iface)

            cls.unload = unload

        # Handle pending actions that were decorated before plugin decorator
        if hasattr(registry, "_pending_actions"):
            pending = list(registry._pending_actions)
            for spec in pending:
                if spec.func.__name__ in cls.__dict__:
                    if spec.cls is None:
                        spec.cls = cls
                    key = cls.__name__
                    registry._actions.setdefault(key, []).append(spec)
                    if key in registry.plugins:
                        registry.plugins[key].actions.append(spec)
                    try:
                        registry._pending_actions.remove(spec)
                    except ValueError:
                        pass

        # Handle pending tasks
        if hasattr(registry, "_pending_tasks"):
            pending_tasks = list(registry._pending_tasks)
            for spec in pending_tasks:
                # Check if task func name in class
                fname = spec.func.__name__ if hasattr(spec.func, "__name__") else ""
                if fname in cls.__dict__ or spec.wrapper.__name__ in cls.__dict__:
                    if spec.cls is None:
                        spec.cls = cls
                    # Already in _tasks dict, just add to plugin meta
                    key = cls.__name__
                    if key in registry.plugins:
                        if spec not in registry.plugins[key].tasks:
                            registry.plugins[key].tasks.append(spec)
                    try:
                        registry._pending_tasks.remove(spec)
                    except ValueError:
                        pass

        # Handle pending settings
        if hasattr(registry, "_pending_settings"):
            pending_settings = list(registry._pending_settings)
            for spec in pending_settings:
                if spec.func.__name__ in cls.__dict__:
                    if spec.cls is None:
                        spec.cls = cls
                    key = cls.__name__
                    registry._settings.setdefault(key, []).append(spec)
                    if key in registry.plugins:
                        if spec not in registry.plugins[key].settings:
                            registry.plugins[key].settings.append(spec)
                    try:
                        registry._pending_settings.remove(spec)
                    except ValueError:
                        pass

        return cls

    return decorator


def toolbar(name: str):
    """Attach action to toolbar."""

    def decorator(func: Callable) -> Callable:
        from .base import _ACTION_ATTR, _require_spec, _replace, ActionSpec as OldSpec

        # For old API, check if func already has action spec — if not, raise
        # But for new API, func may have _is_action from @action decorator (which runs first)
        has_old = getattr(func, _ACTION_ATTR, None) is not None
        has_new = getattr(func, "_is_action", False)

        if not has_old and not has_new:
            # Check if this is being used without @action — raise for old API compat
            # However, if func has _toolbar already, it means toolbar was applied twice? Ignore
            # For new API, @toolbar is above @action, so when toolbar runs, action has already run and set _is_action
            # So if neither, it's broken
            raise TypeError(
                f"{func.__name__} is decorated with @toolbar/@menu but not @action; put @action closest to the method"
            )

        # Old style handling
        try:
            old_spec = getattr(func, _ACTION_ATTR, None)
            if old_spec:
                setattr(func, _ACTION_ATTR, _replace(old_spec, toolbar=name))
        except Exception:
            pass

        # New registry handling
        if hasattr(registry, "_pending_actions"):
            for spec in registry._pending_actions:
                if spec.func == func or spec.func_name == func.__name__:
                    spec.toolbar = name
                    break
            else:
                # No existing, register new with toolbar (should not happen if action was first)
                registry.register_action(func, toolbar=name, tooltip=getattr(func, "_tooltip", ""), icon=getattr(func, "_icon", None))
        else:
            registry.register_action(func, toolbar=name)

        func._toolbar = name
        return func

    return decorator


def action(*, tooltip: str = "", icon: str = None, name: str = None, menu: tuple = None):
    """Mark method as plugin action."""

    def decorator(func: Callable) -> Callable:
        func_name = name or func.__name__
        # Old decorator
        from .base import _ACTION_ATTR, ActionSpec as OldSpec

        old_spec = OldSpec(func_name=func_name, tooltip=tooltip, icon=icon, toolbar=getattr(func, "_toolbar", None), menu=menu or ())
        setattr(func, _ACTION_ATTR, old_spec)

        # New registry
        # Check if already has toolbar from @toolbar decorator
        toolbar_name = getattr(func, "_toolbar", None)
        # Also check if menu provided
        menu_path = menu

        # Register
        registry.register_action(func, toolbar=toolbar_name, menu=menu_path, tooltip=tooltip, icon=icon)

        func._tooltip = tooltip
        func._icon = icon
        func._is_action = True

        return func

    return decorator


def menu(*path: str):
    """Attach action to menu path."""
    if not path:
        raise ValueError("menu() needs at least one path component")

    def decorator(func: Callable) -> Callable:
        from .base import _ACTION_ATTR, _require_spec, _replace

        has_old = getattr(func, _ACTION_ATTR, None) is not None
        has_new = getattr(func, "_is_action", False)

        if not has_old and not has_new:
            raise TypeError(
                f"{func.__name__} is decorated with @toolbar/@menu but not @action; put @action closest to the method"
            )

        try:
            old_spec = _require_spec(func)
            setattr(func, _ACTION_ATTR, _replace(old_spec, menu=path))
        except Exception:
            func._menu = path

        if hasattr(registry, "_pending_actions"):
            for spec in registry._pending_actions:
                if spec.func == func or spec.func_name == func.__name__:
                    spec.menu = path
                    break
            else:
                registry.register_action(func, menu=path, tooltip=getattr(func, "_tooltip", ""), icon=getattr(func, "_icon", None), toolbar=getattr(func, "_toolbar", None))
        else:
            registry.register_action(func, menu=path)

        func._menu = path
        return func

    return decorator


def setting(default: Any = None, persist: bool = True):
    """Decorator for plugin setting."""

    def decorator(func: Callable) -> Callable:
        func._is_setting = True
        func._setting_default = default
        func._setting_persist = persist

        registry.register_setting(func, default=default, persist=persist)

        return func

    return decorator


def task(description: str = "Task", bind: bool = False, can_cancel: bool = True, **kwargs):
    """Decorator for background task — celery-like, also registers in plugin registry."""

    def decorator(func: Callable):
        from ..tasks import TaskWrapper

        wrapper = TaskWrapper(func, description=description, bind=bind, can_cancel=can_cancel, **kwargs)
        registry.register_task(wrapper, func=func, description=description)

        # Also store on func
        wrapper._is_task = True
        return wrapper

    return decorator


# Re-export for convenience
__all__ = ["plugin", "toolbar", "action", "menu", "setting", "task", "registry"]
