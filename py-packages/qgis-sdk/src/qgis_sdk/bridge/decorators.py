"""qgis_sdk.bridge.decorators — declarative decorators for bridge.

Provides @bridge, @method, @signal, @slot, @property decorators that
register BridgeDescription without codegen.

Usage:
    from qgis_sdk.bridge import bridge, method, signal

    @bridge(name="my_bridge", version="1.0")
    class MyBridge:
        @method(return_type=dict, doc="Get layer")
        def get_layer(self, layer_id: str) -> dict:
            return {"name": layer_id}

        @signal()
        def layer_changed(self, layer_id: str):
            pass
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Type

from .description import BridgeDescription, bridge_registry


def bridge(name: str = "bridge", version: str = "1.0", description: Optional[str] = None, permissions: Optional[list] = None):
    """Class decorator to mark a bridge and register its description.

    Args:
        name: QWebChannel object name (default "bridge")
        version: bridge version
        description: optional doc
        permissions: optional list of permissions for JS qgis API (not used here, for plugin decorator)
    """

    def decorator(cls: Type) -> Type:
        # Set attributes for description extraction
        cls._bridge_name = name
        cls._bridge_version = version
        if description:
            cls._bridge_doc = description
        if permissions:
            cls._bridge_permissions = permissions

        # Build description
        desc = BridgeDescription.from_class(cls, name=name)
        desc.version = version
        if description:
            desc.doc = description

        # Register
        bridge_registry.register(desc, cls)

        # Attach description to class
        cls._bridge_description = desc

        return cls

    return decorator


def method(return_type: Any = None, doc: Optional[str] = None, name: Optional[str] = None):
    """Method decorator to mark a bridge method (slot).

    Args:
        return_type: Python type or string for TS
        doc: docstring override
        name: optional override for method name in JS (not yet used)
    """

    def decorator(func: Callable) -> Callable:
        func._is_bridge_method = True
        func._is_slot = True
        if return_type is not None:
            func._bridge_return_type = return_type
            func._return_type = return_type
        if doc is not None:
            func._bridge_doc = doc
        if name is not None:
            func._bridge_name = name
        return func

    return decorator


def slot(*args, **kwargs):
    """Alias for @method — QWebChannel slot."""
    return method(*args, **kwargs)


def signal(arg_types: Any = None, doc: Optional[str] = None):
    """Signal decorator — marks method as QGIS signal (JS can listen).

    In QWebChannel, signals are methods that JS can connect to via
    bridge.signal.connect(callback).

    Usage:
        @signal()
        def layer_changed(self, layer_id: str):
            pass

        # In Python, emit via self.layer_changed.emit(layer_id) or via BridgeWindow
    """

    def decorator(func: Callable) -> Callable:
        func._is_signal = True
        func._is_bridge_method = False
        if arg_types is not None:
            func._bridge_arg_types = arg_types
        if doc is not None:
            func._bridge_doc = doc
        return func

    return decorator


def bridge_property(doc: Optional[str] = None, return_type: Any = None):
    """Property decorator for bridge properties."""

    def decorator(func: Callable) -> Callable:
        func._is_bridge_property = True
        if doc is not None:
            func._bridge_doc = doc
        if return_type is not None:
            func._bridge_return_type = return_type
        return func

    return decorator


# For backwards compatibility and declarative plugin
def window(func: Callable) -> Callable:
    """Decorator for bridge window event handler.

    Usage:
        @bridge.window
        def on_window(self, window):
            window.add_event_listener("message", lambda e: ...)
    """
    func._is_bridge_window_handler = True
    return func


__all__ = ["bridge", "method", "slot", "signal", "bridge_property", "window"]
