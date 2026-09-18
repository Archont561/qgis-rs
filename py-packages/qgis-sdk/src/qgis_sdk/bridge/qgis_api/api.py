"""qgis_sdk.bridge.qgis_api — built-in QGIS API exposed to JS.

This is the high-level API that JS can use without user defining custom bridge methods.
It is automatically registered as QWebChannel object "qgis" alongside user bridge.

JS usage:
    const { qgis } = await createQgisBridge();
    await qgis.layers.addVector("/path/to.shp", "Roads");
    await qgis.message.info("Hello", "From JS");
    const task = await qgis.tasks.run("my_task", {distance: 10});
    const resp = await qgis.network.fetch("https://example.com/api");

Python side: QgisApi class with @method decorators, auto-registers signals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..description import BridgeDescription, MethodDescription
from .layers import LayersAPI
from .project import ProjectAPI
from .message import MessageAPI
from .tasks import TasksAPI
from .network import NetworkAPI
from .iface import IfaceAPI
from .settings import SettingsAPI
from .processing import ProcessingAPI


class QgisApi:
    """
    Built-in QGIS API exposed to JS automatically.

    Registered as "qgis" QWebChannel object.
    """

    def __init__(self, iface=None, plugin=None, plugin_name: str = "my_plugin", permissions: Optional[List[str]] = None):
        self.iface = iface
        self.plugin = plugin
        self.plugin_name = plugin_name
        self.permissions = set(permissions) if permissions else None  # None = all allowed

        # Sub-APIs
        self._layers = LayersAPI(iface=iface)
        self._project = ProjectAPI()
        self._message = MessageAPI(iface=iface)
        self._tasks = TasksAPI(plugin=plugin, iface=iface)
        self._network = NetworkAPI()
        self._iface = IfaceAPI(iface=iface)
        self._settings = SettingsAPI(plugin_name=plugin_name)
        self._processing = ProcessingAPI(iface=iface)

    def _check_permission(self, namespace: str) -> bool:
        if self.permissions is None:
            return True
        return namespace in self.permissions

    def _ensure_permission(self, namespace: str):
        if not self._check_permission(namespace):
            raise PermissionError(f"Permission denied for qgis.{namespace} — not in {self.permissions}")

    # ---- Message ----
    def message_info(self, title: str, message: str, duration: int = 5) -> bool:
        self._ensure_permission("message")
        return self._message.info(title, message, duration)

    def message_warning(self, title: str, message: str, duration: int = 5) -> bool:
        self._ensure_permission("message")
        return self._message.warning(title, message, duration)

    def message_critical(self, title: str, message: str, duration: int = 5) -> bool:
        self._ensure_permission("message")
        return self._message.critical(title, message, duration)

    def message_success(self, title: str, message: str, duration: int = 5) -> bool:
        self._ensure_permission("message")
        return self._message.success(title, message, duration)

    # ---- Layers ----
    def layers_list(self) -> List[Dict[str, Any]]:
        self._ensure_permission("layers")
        return self._layers.list()

    def layers_active(self) -> Optional[Dict[str, Any]]:
        self._ensure_permission("layers")
        return self._layers.active()

    def layers_add_vector(self, path: str, name: str = "", provider: str = "ogr") -> Dict[str, Any]:
        self._ensure_permission("layers")
        return self._layers.add_vector(path, name, provider)

    def layers_add_raster(self, path: str, name: str = "", provider: str = "gdal") -> Dict[str, Any]:
        self._ensure_permission("layers")
        return self._layers.add_raster(path, name, provider)

    def layers_remove(self, layer_id: str) -> bool:
        self._ensure_permission("layers")
        return self._layers.remove(layer_id)

    def layers_zoom_to(self, layer_id: str) -> bool:
        self._ensure_permission("layers")
        return self._layers.zoom_to(layer_id)

    def layers_set_active(self, layer_id: str) -> bool:
        self._ensure_permission("layers")
        return self._layers.set_active(layer_id)

    def layers_get(self, layer_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_permission("layers")
        return self._layers.get(layer_id)

    # ---- Project ----
    def project_info(self) -> Dict[str, Any]:
        self._ensure_permission("project")
        return self._project.info()

    def project_write(self) -> bool:
        self._ensure_permission("project")
        return self._project.write()

    def project_crs(self) -> str:
        self._ensure_permission("project")
        return self._project.crs()

    def project_set_crs(self, authid: str) -> bool:
        self._ensure_permission("project")
        return self._project.set_crs(authid)

    def project_path(self) -> str:
        self._ensure_permission("project")
        return self._project.path()

    # ---- Tasks ----
    def tasks_run(self, task_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        self._ensure_permission("tasks")
        return self._tasks.run(task_name, params)

    def tasks_list(self) -> List[Dict[str, Any]]:
        self._ensure_permission("tasks")
        return self._tasks.list()

    def tasks_cancel(self, task_id: str) -> bool:
        self._ensure_permission("tasks")
        return self._tasks.cancel(task_id)

    # ---- Network ----
    def network_fetch(self, url: str, method: str = "GET", headers: Dict[str, str] = None, body: str = None, auth_cfg: str = None) -> Dict[str, Any]:
        self._ensure_permission("network")
        return self._network.fetch(url, method, headers, body, auth_cfg)

    def network_get(self, url: str, headers: Dict[str, str] = None, auth_cfg: str = None) -> Dict[str, Any]:
        self._ensure_permission("network")
        return self._network.get(url, headers, auth_cfg)

    def network_post(self, url: str, body: str = None, headers: Dict[str, str] = None, auth_cfg: str = None) -> Dict[str, Any]:
        self._ensure_permission("network")
        return self._network.post(url, body, headers, auth_cfg)

    # ---- Iface ----
    def iface_zoom_to_layer(self, layer_id: str) -> bool:
        self._ensure_permission("iface")
        return self._iface.zoom_to_layer(layer_id)

    def iface_show_message(self, title: str, message: str, level: int = 0, duration: int = 5) -> bool:
        self._ensure_permission("message")
        return self._iface.show_message(title, message, level, duration)

    def iface_active_layer(self) -> Optional[Dict[str, Any]]:
        self._ensure_permission("iface")
        return self._iface.active_layer()

    # ---- Settings ----
    def settings_get(self, key: str, default: str = "") -> str:
        self._ensure_permission("settings")
        return self._settings.get(key, default)

    def settings_set(self, key: str, value: str) -> bool:
        self._ensure_permission("settings")
        return self._settings.set(key, value)

    # ---- Processing ----
    def processing_run(self, alg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_permission("processing")
        return self._processing.run(alg_id, params)

    @property
    def description(self) -> BridgeDescription:
        """Build BridgeDescription for this QgisApi — for JS to know methods."""
        methods = []
        # Inspect self for public methods that are part of API
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            if attr_name == "description":
                continue
            attr = getattr(self, attr_name)
            if not callable(attr):
                continue
            # Only include methods that are part of qgis API (we have explicit list)
            # Build MethodDescription with simple args inspection
            import inspect
            try:
                sig = inspect.signature(attr)
                args = [p.name for p in sig.parameters.values() if p.name not in ("self",)]
                # We don't need arg types for built-in, keep any
                arg_types = ["any"] * len(args)
            except Exception:
                args = []
                arg_types = []

            methods.append(
                MethodDescription(
                    name=attr_name,
                    args=args,
                    arg_types=arg_types,
                    return_type="any",
                    doc=inspect.getdoc(attr) or "",
                )
            )

        return BridgeDescription(
            name="qgis",
            methods=methods,
            signals=[
                MethodDescription(name="layer_added", args=["layer_id"], arg_types=["string"], is_signal=True),
                MethodDescription(name="layer_removed", args=["layer_id"], arg_types=["string"], is_signal=True),
                MethodDescription(name="task_progress", args=["task_id", "progress"], arg_types=["string", "number"], is_signal=True),
                MethodDescription(name="task_finished", args=["task_id", "result"], arg_types=["string", "object"], is_signal=True),
            ],
            version="1.0",
            doc="Built-in QGIS API exposed to JS",
        )


# For backwards compat, expose as QgisAPI too
QgisAPI = QgisApi
