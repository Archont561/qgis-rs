"""qgis_sdk.bridge.qgis_api.iface — iface API for JS."""

from __future__ import annotations


def _get_iface(iface=None):
    if iface is not None:
        return iface
    try:
        from qgis.utils import iface as qgis_iface
        return qgis_iface
    except ImportError:
        return None


def _get_project():
    try:
        from qgis.core import QgsProject
        return QgsProject.instance()
    except ImportError:
        return None


class IfaceAPI:
    def __init__(self, iface=None):
        self.iface = iface

    def zoom_to_layer(self, layer_id: str) -> bool:
        iface = _get_iface(self.iface)
        project = _get_project()
        if not iface or not project:
            return False
        try:
            layer = project.mapLayer(layer_id)
            if not layer:
                return False
            iface.mapCanvas().setExtent(layer.extent())
            iface.mapCanvas().refresh()
            return True
        except Exception:
            return False

    def show_message(self, title: str, message: str, level: int = 0, duration: int = 5) -> bool:
        iface = _get_iface(self.iface)
        if not iface:
            print(f"[Iface] {title}: {message}")
            return True
        try:
            from qgis.core import Qgis
            level_map = {0: Qgis.Info, 1: Qgis.Warning, 2: Qgis.Critical, 3: Qgis.Success}
            qlevel = level_map.get(level, Qgis.Info)
            iface.messageBar().pushMessage(title, message, level=qlevel, duration=duration)
            return True
        except Exception:
            try:
                iface.messageBar().pushMessage(title, message, duration=duration)
                return True
            except Exception:
                return False

    def active_layer(self):
        iface = _get_iface(self.iface)
        if not iface:
            return None
        try:
            layer = iface.activeLayer()
            if not layer:
                return None
            return {"id": layer.id(), "name": layer.name()}
        except Exception:
            return None
