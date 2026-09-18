"""qgis_sdk.bridge.runtime — BridgeRuntime that registers QWebChannel and injects description + qgis API.

New architecture:
- Loads BridgeDescription from Python class (no codegen)
- Registers both user bridge and built-in QgisApi as "qgis" object
- Injects window.__QGIS_BRIDGE_DESCRIPTION__ and window.__QGIS_API_DESCRIPTION__ as JSON
- Provides window-like API for Python side

Usage:
    from qgis_sdk.bridge import BridgeRuntime, QgisApi
    from qgis_sdk.bridge.description import BridgeDescription

    desc = BridgeDescription.from_class(MyBridge, name="my_bridge")
    runtime = BridgeRuntime(description=desc, impl_instance=MyBridge(), qgis_api=QgisApi(iface=iface))
    runtime.register(webview)

    window = runtime.to_window()
    window.send({"ready": True})
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Type

from .description import BridgeDescription, bridge_registry
from .window import BridgeWindow
from .qgis_api import QgisApi


class BridgeRuntime:
    def __init__(
        self,
        description: Optional[BridgeDescription] = None,
        impl_instance: Any = None,
        impl_class: Optional[Type] = None,
        qgis_api: Optional[QgisApi] = None,
        object_name: str = "bridge",
        qgis_object_name: str = "qgis",
        enable_qgis_api: bool = True,
        permissions: Optional[list] = None,
        iface: Any = None,
        plugin: Any = None,
    ):
        """
        Args:
            description: BridgeDescription for user bridge
            impl_instance: instance of user bridge class
            impl_class: class (if instance not provided, will instantiate)
            qgis_api: QgisApi instance (if None and enable_qgis_api, creates one)
            object_name: QWebChannel object name for user bridge (default "bridge")
            qgis_object_name: QWebChannel object name for qgis API (default "qgis")
            enable_qgis_api: whether to enable built-in qgis API
            permissions: list of permissions for qgis API
            iface: QGIS iface
            plugin: plugin instance
        """
        self.object_name = object_name
        self.qgis_object_name = qgis_object_name
        self.enable_qgis_api = enable_qgis_api
        self.permissions = permissions
        self.iface = iface
        self.plugin = plugin

        # Resolve description
        if description is None and impl_instance is not None:
            # Try to get from instance
            if hasattr(impl_instance, "_bridge_description"):
                description = impl_instance._bridge_description
            else:
                description = BridgeDescription.from_class(impl_instance.__class__, name=object_name)
        elif description is None and impl_class is not None:
            if hasattr(impl_class, "_bridge_description"):
                description = impl_class._bridge_description
            else:
                description = BridgeDescription.from_class(impl_class, name=object_name)

        if description is None:
            # Empty description
            description = BridgeDescription(name=object_name, methods=[], signals=[])

        self.description = description

        # Resolve impl instance
        if impl_instance is None and impl_class is not None:
            try:
                impl_instance = impl_class()
            except Exception:
                impl_instance = None

        self.impl = impl_instance
        self.impl_class = impl_class or (impl_instance.__class__ if impl_instance else None)

        # QgisApi
        if qgis_api is None and enable_qgis_api:
            qgis_api = QgisApi(iface=iface, plugin=plugin, permissions=permissions)
        self.qgis_api = qgis_api

        self._channel = None
        self._webview = None
        self._window: Optional[BridgeWindow] = None

    def register(self, webview: Any):
        """Register bridge and qgis API with webview via QWebChannel."""
        self._webview = webview

        try:
            from .._qt import QWebChannel
        except ImportError:
            try:
                from qgis.PyQt.QtWebChannel import QWebChannel  # type: ignore
            except ImportError:
                try:
                    from PyQt5.QtWebChannel import QWebChannel  # type: ignore
                except ImportError:
                    try:
                        from PyQt6.QtWebChannel import QWebChannel  # type: ignore
                    except ImportError:
                        try:
                            from PySide6.QtWebChannel import QWebChannel  # type: ignore
                        except ImportError:
                            # No QWebChannel available — fallback for testing
                            print("[BridgeRuntime] QWebChannel not available, skipping registration")
                            return self

        try:
            channel = QWebChannel(webview.page() if hasattr(webview, "page") else webview)
            # Register user bridge if exists
            if self.impl is not None:
                channel.registerObject(self.object_name, self.impl)

            # Register qgis API if enabled
            if self.enable_qgis_api and self.qgis_api is not None:
                channel.registerObject(self.qgis_object_name, self.qgis_api)

            # Set channel to webview
            if hasattr(webview, "page"):
                webview.page().setWebChannel(channel)
            elif hasattr(webview, "setWebChannel"):
                webview.setWebChannel(channel)

            self._channel = channel

            # Inject description JSON into window
            self._inject_descriptions(webview)

        except Exception as e:
            print(f"[BridgeRuntime] register failed: {e}")
            import traceback
            traceback.print_exc()

        return self

    def _inject_descriptions(self, webview: Any):
        """Inject bridge and qgis API descriptions as JSON into window."""
        try:
            bridge_json = self.description.to_json()
            qgis_json = self.qgis_api.description.to_json() if self.qgis_api else "{}"

            js = f"""
            window.__QGIS_BRIDGE_DESCRIPTION__ = {bridge_json};
            window.__QGIS_API_DESCRIPTION__ = {qgis_json};
            window.__QGIS_BRIDGE_NAME__ = "{self.object_name}";
            window.__QGIS_API_NAME__ = "{self.qgis_object_name}";
            console.log("[qgis-sdk] Bridge description injected", window.__QGIS_BRIDGE_DESCRIPTION__);
            console.log("[qgis-sdk] QGIS API description injected", window.__QGIS_API_DESCRIPTION__);
            """

            if hasattr(webview, "page") and hasattr(webview.page(), "runJavaScript"):
                webview.page().runJavaScript(js)
            elif hasattr(webview, "runJavaScript"):
                webview.runJavaScript(js)

            # Also inject via setHtml if needed — for initial load
            # We store for later injection if page reloads
            self._injected_js = js

        except Exception as e:
            print(f"[BridgeRuntime] inject descriptions failed: {e}")

    def to_window(self) -> BridgeWindow:
        """Return window-like object for Python → JS."""
        if self._window is None:
            self._window = BridgeWindow(runtime=self, webview=self._webview)
            self._window.readyState = BridgeWindow.OPEN
        return self._window

    def create_window(self, webview: Any = None) -> BridgeWindow:
        """Create new window-like object."""
        return BridgeWindow(runtime=self, webview=webview or self._webview)

    def get_description(self) -> BridgeDescription:
        return self.description

    def get_qgis_api_description(self) -> Optional[BridgeDescription]:
        if self.qgis_api:
            return self.qgis_api.description
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bridge": self.description.to_dict(),
            "qgis": self.qgis_api.description.to_dict() if self.qgis_api else None,
            "object_name": self.object_name,
            "qgis_object_name": self.qgis_object_name,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_class(
        cls,
        bridge_class: Type,
        name: str = "bridge",
        enable_qgis_api: bool = True,
        iface: Any = None,
        plugin: Any = None,
        permissions: Optional[list] = None,
    ) -> "BridgeRuntime":
        """Create runtime from bridge class."""
        desc = BridgeDescription.from_class(bridge_class, name=name)
        try:
            impl = bridge_class()
        except Exception:
            impl = None
        return cls(
            description=desc,
            impl_instance=impl,
            impl_class=bridge_class,
            enable_qgis_api=enable_qgis_api,
            iface=iface,
            plugin=plugin,
            permissions=permissions,
            object_name=name,
        )


# For backwards compat
BridgeWindowFactory = BridgeRuntime
