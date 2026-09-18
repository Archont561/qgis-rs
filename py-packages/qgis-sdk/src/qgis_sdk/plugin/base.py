"""Plugin definition: the :class:`Plugin` base class and its decorators.

Declare a plugin as a class; the SDK turns the class attributes and decorated
methods into the ``metadata.txt``, ``classFactory`` entry point, and the
``initGui``/``unload`` lifecycle QGIS expects.

    from qgis_sdk import Plugin, action, toolbar, menu

    class MyPlugin(Plugin):
        name = "My Plugin"
        version = "0.1.0"

        @toolbar("My Toolbar")
        @action(tooltip="Run my tool", icon="icons/tool.svg")
        def run_tool(self, iface):
            iface.message_bar.push("hello")
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..metadata import render_metadata, write_metadata

__all__ = [
    "ActionSpec",
    "Plugin",
    "action",
    "class_factory",
    "menu",
    "toolbar",
]

_ACTION_ATTR = "__qgis_sdk_action__"


@dataclass(frozen=True)
class ActionSpec:
    """A toolbar button / menu entry declared with :func:`action`."""

    func_name: str
    tooltip: str = ""
    icon: str | None = None
    toolbar: str | None = None
    menu: tuple[str, ...] = ()

    @property
    def menu_path(self) -> str:
        """The menu path QGIS wants, e.g. ``Plugins/My Plugin``."""
        return "/".join(self.menu)


def action(
    *,
    tooltip: str = "",
    icon: str | None = None,
    name: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a method as a user-invocable plugin action."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(
            func,
            _ACTION_ATTR,
            ActionSpec(func_name=name or func.__name__, tooltip=tooltip, icon=icon),
        )
        return func

    return decorator


def toolbar(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Attach an already-declared action to a toolbar called ``name``."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        spec = _require_spec(func)
        setattr(func, _ACTION_ATTR, _replace(spec, toolbar=name))
        return func

    return decorator


def menu(*path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Attach an already-declared action to a menu path.

    ``@menu("Plugins", "My Plugin")`` produces the path ``Plugins/My Plugin``.
    """
    if not path:
        raise ValueError("menu() needs at least one path component")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        spec = _require_spec(func)
        setattr(func, _ACTION_ATTR, _replace(spec, menu=path))
        return func

    return decorator


def _require_spec(func: Callable[..., Any]) -> ActionSpec:
    spec = getattr(func, _ACTION_ATTR, None)
    if spec is None:
        raise TypeError(
            f"{func.__name__} is decorated with @toolbar/@menu but not @action; "
            "put @action closest to the method"
        )
    return spec


def _replace(spec: ActionSpec, **changes: Any) -> ActionSpec:
    return ActionSpec(**{**spec.__dict__, **changes})


class Plugin:
    """Base class for a QGIS plugin.

    Subclasses declare metadata as class attributes and actions as decorated
    methods. ``init_gui``/``unload`` wire those actions into the QGIS interface.
    """

    #: Attributes rendered into ``metadata.txt``.
    name: str = ""
    version: str = "0.0.0"
    description: str = ""
    about: str | None = None
    author: str = ""
    email: str = ""
    category: str | None = None
    tags: tuple[str, ...] = ()
    qgis_min_version: str = "3.28"
    qgis_max_version: str | None = None
    homepage: str | None = None
    repository: str | None = None
    tracker: str | None = None
    experimental: bool = False
    deprecated: bool = False
    has_processing_provider: bool = False
    server: bool = False
    icon: str | None = None
    changelog: str | None = None
    plugin_dependencies: str | None = None

    def __init__(self, iface: Any = None) -> None:
        self.iface = iface
        self._created: list[tuple[ActionSpec, Any]] = []
        self._processing_provider: Any = None

    # -- declaration ------------------------------------------------------

    @classmethod
    def actions(cls) -> list[ActionSpec]:
        """Every action declared on the class, in declaration order."""
        specs: list[ActionSpec] = []
        for klass in reversed(cls.__mro__):
            for attribute, value in vars(klass).items():
                spec = getattr(value, _ACTION_ATTR, None)
                if spec is None:
                    continue
                specs.append(_replace(spec, func_name=attribute))
        return specs

    @classmethod
    def metadata_txt(cls) -> str:
        """The ``metadata.txt`` body for this plugin."""
        return render_metadata(cls)

    @classmethod
    def write_metadata(cls, directory: str) -> str:
        """Write ``metadata.txt`` into ``directory``; returns the path."""
        return write_metadata(cls, directory)

    # -- lifecycle --------------------------------------------------------

    def init_gui(self, iface: Any = None) -> None:
        """Create the actions and add them to the QGIS interface.

        ``iface`` is a ``QgisInterface`` in QGIS; tests can pass any object with
        ``addAction``, ``addToolBarIcon``, and ``addPluginToMenu`` methods.
        """
        if iface is not None:
            self.iface = iface
        if self.iface is None:
            raise RuntimeError("init_gui() needs an interface")

        for spec in self.actions():
            widget = self._create_action(spec)
            self._created.append((spec, widget))
            if spec.toolbar:
                self.iface.addToolBarIcon(widget)
            if spec.menu:
                self.iface.addPluginToMenu(spec.menu_path, widget)

        # Processing provider registration
        self._init_processing_provider()

        self.on_init(self.iface)

    def unload(self, iface: Any = None) -> None:
        """Remove everything :meth:`init_gui` added."""
        if iface is not None:
            self.iface = iface
        
        # Unregister processing provider
        self._unload_processing_provider()
        
        for spec, widget in reversed(self._created):
            if spec.toolbar and hasattr(self.iface, "removeToolBarIcon"):
                self.iface.removeToolBarIcon(widget)
            if spec.menu and hasattr(self.iface, "removePluginMenu"):
                self.iface.removePluginMenu(spec.menu_path, widget)
        self._created.clear()
        self.on_unload(self.iface)

    def _init_processing_provider(self) -> None:
        """Initialize processing provider if algorithms defined."""
        algorithms = getattr(self, "algorithms", None) or getattr(self.__class__, "algorithms", [])
        if not algorithms and not getattr(self, "has_processing_provider", False) and not getattr(self.__class__, "has_processing_provider", False):
            return

        if not algorithms:
            # No algorithms but flag set — nothing to register, but keep honest
            return

        try:
            from ..processing_bridge import build_provider, register_provider
            provider_id = getattr(self, "provider_id", None) or getattr(self.__class__, "provider_id", "") or ""
            if not provider_id:
                # Derive from first algorithm id or plugin name
                first = algorithms[0] if algorithms else None
                if first:
                    alg_id = getattr(first, "id", "") if not isinstance(first, type) else getattr(first, "id", "")
                    if ":" in alg_id:
                        provider_id = alg_id.split(":", 1)[0]
                if not provider_id:
                    provider_id = getattr(self, "name", "qgis_sdk").lower().replace(" ", "_")

            provider_name = getattr(self, "provider_name", None) or getattr(self.__class__, "provider_name", "") or getattr(self, "name", "") or provider_id
            icon = getattr(self, "icon", None) or getattr(self.__class__, "icon", "") or ""

            provider = build_provider(algorithms, provider_id=provider_id, provider_name=provider_name, icon_path=icon)
            if register_provider(provider):
                self._processing_provider = provider
        except Exception as e:
            print(f"[Plugin] failed to register processing provider: {e}")

    def _unload_processing_provider(self) -> None:
        if self._processing_provider is None:
            return
        try:
            from ..processing_bridge import unregister_provider
            unregister_provider(self._processing_provider)
            self._processing_provider = None
        except Exception as e:
            print(f"[Plugin] failed to unregister provider: {e}")

    # -- hooks ------------------------------------------------------------

    def on_init(self, iface: Any) -> None:
        """Override for extra set-up after the actions exist."""

    def on_unload(self, iface: Any) -> None:
        """Override for clean-up before the actions are removed."""

    # -- internals --------------------------------------------------------

    def _create_action(self, spec: ActionSpec) -> Any:
        """Build the clickable widget for ``spec``.

        Uses a real ``QAction`` inside QGIS; :attr:`action_factory` can replace
        it, which is how the test-suite avoids needing Qt.
        """
        if self.action_factory is not None:
            return self.action_factory(spec, self._invoke(spec))
        try:
            from .._qt import make_action  # type: ignore
        except ImportError:
            from ..qt import make_action  # type: ignore  # fallback shim

        return make_action(spec, self._invoke(spec), parent=self.iface)

    #: Override (or set on an instance) to inject your own widget factory.
    action_factory: Callable[[ActionSpec, Callable[[], None]], Any] | None = None

    def _invoke(self, spec: ActionSpec) -> Callable[[], None]:
        def run() -> None:
            getattr(self, spec.func_name)(self.iface)

        return run


def class_factory(plugin: type[Plugin]) -> Callable[[Any], Plugin]:
    """Return the ``classFactory(iface)`` callable QGIS loads."""

    def factory(iface: Any) -> Plugin:
        return plugin(iface)

    factory.__name__ = "classFactory"
    return factory
