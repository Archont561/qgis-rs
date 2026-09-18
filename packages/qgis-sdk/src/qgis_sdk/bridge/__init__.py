"""qgis_sdk.bridge — new description loader + window-like + QGIS API, with legacy codegen shim.

New API:
    from qgis_sdk.bridge import bridge, method, signal, BridgeDescription, BridgeRuntime, QgisApi, load_bridge_description

    @bridge(name="my_bridge")
    class MyBridge:
        @method(return_type=dict)
        def get_layer(self, layer_id: str) -> dict:
            return {"name": layer_id}

    desc = BridgeDescription.from_class(MyBridge)
    runtime = BridgeRuntime(description=desc, impl_instance=MyBridge(), enable_qgis_api=True, iface=iface)
    runtime.register(webview)

Legacy API (still works):
    from qgis_sdk.bridge import generate_ts_bridge, generate_js_wrapper, generate_package, load_bridge_class
"""

from __future__ import annotations

# New API
from .description import BridgeDescription, MethodDescription, BridgeRegistry, bridge_registry
from .decorators import bridge, method, slot, signal, bridge_property, window as bridge_window
from .runtime import BridgeRuntime
from .window import BridgeWindow, EventTarget, Event, Window
from .qgis_api import QgisApi, QgisAPI
from .loader import load_bridge_description, load_bridge_description_from_window

# Legacy codegen — keep backwards compat
try:
    from .codegen import (
        generate_ts_bridge,
        generate_js_wrapper,
        generate_package,
        load_bridge_class,
        _py_type_to_ts,
    )
except ImportError as e:
    # Fallback if codegen missing
    generate_ts_bridge = generate_js_wrapper = generate_package = load_bridge_class = None
    _py_type_to_ts = None
    print(f"[bridge] legacy codegen not available: {e}")

# For convenience, expose decorators at top level
# Also expose QgisApi submodules
from . import qgis_api as qgis_api_module

__all__ = [
    # New description loader
    "BridgeDescription",
    "MethodDescription",
    "BridgeRegistry",
    "bridge_registry",
    "bridge",
    "method",
    "slot",
    "signal",
    "bridge_property",
    "bridge_window",
    "BridgeRuntime",
    "BridgeWindow",
    "EventTarget",
    "Event",
    "Window",
    "QgisApi",
    "QgisAPI",
    "load_bridge_description",
    "load_bridge_description_from_window",
    "qgis_api_module",
    # Legacy
    "generate_ts_bridge",
    "generate_js_wrapper",
    "generate_package",
    "load_bridge_class",
    "_py_type_to_ts",
]
