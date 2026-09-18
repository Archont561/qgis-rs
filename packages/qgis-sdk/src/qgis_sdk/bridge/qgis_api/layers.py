"""qgis_sdk.bridge.qgis_api.layers — layers API exposed to JS."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get_project():
    try:
        from qgis.core import QgsProject
        return QgsProject.instance()
    except ImportError:
        return None


def _get_iface(iface=None):
    if iface is not None:
        return iface
    try:
        from qgis.utils import iface as qgis_iface
        return qgis_iface
    except ImportError:
        return None


class LayersAPI:
    def __init__(self, iface=None):
        self.iface = iface

    def list(self) -> List[Dict[str, Any]]:
        project = _get_project()
        if not project:
            return []
        layers = []
        for layer_id, layer in project.mapLayers().items():
            try:
                ltype = "vector" if layer.type() == 0 else "raster" if layer.type() == 1 else "unknown"
            except Exception:
                ltype = "unknown"
            try:
                crs = layer.crs().authid() if hasattr(layer, "crs") else ""
            except Exception:
                crs = ""
            try:
                name = layer.name()
            except Exception:
                name = str(layer_id)
            info = {"id": layer_id, "name": name, "type": ltype, "crs": crs}
            # Add feature count for vector
            try:
                if hasattr(layer, "featureCount"):
                    info["featureCount"] = layer.featureCount()
            except Exception:
                pass
            layers.append(info)
        return layers

    def active(self) -> Optional[Dict[str, Any]]:
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

    def add_vector(self, path: str, name: str = "", provider: str = "ogr") -> Dict[str, Any]:
        project = _get_project()
        if not project:
            raise RuntimeError("QGIS not available")
        from qgis.core import QgsVectorLayer
        layer_name = name or path
        layer = QgsVectorLayer(path, layer_name, provider)
        if not layer.isValid():
            raise ValueError(f"Failed to load vector layer {path}")
        project.addMapLayer(layer)
        return {"id": layer.id(), "name": layer.name(), "type": "vector"}

    def add_raster(self, path: str, name: str = "", provider: str = "gdal") -> Dict[str, Any]:
        project = _get_project()
        if not project:
            raise RuntimeError("QGIS not available")
        from qgis.core import QgsRasterLayer
        layer_name = name or path
        layer = QgsRasterLayer(path, layer_name, provider)
        if not layer.isValid():
            raise ValueError(f"Failed to load raster layer {path}")
        project.addMapLayer(layer)
        return {"id": layer.id(), "name": layer.name(), "type": "raster"}

    def remove(self, layer_id: str) -> bool:
        project = _get_project()
        if not project:
            return False
        try:
            project.removeMapLayer(layer_id)
            return True
        except Exception:
            return False

    def zoom_to(self, layer_id: str) -> bool:
        project = _get_project()
        iface = _get_iface(self.iface)
        if not project or not iface:
            return False
        try:
            layer = project.mapLayer(layer_id)
            if not layer:
                return False
            # If active layer is same, zoom to active, else set extent
            try:
                iface.mapCanvas().setExtent(layer.extent())
                iface.mapCanvas().refresh()
                return True
            except Exception:
                # Fallback
                iface.zoomToActiveLayer()
                return True
        except Exception as e:
            print(f"[LayersAPI] zoom_to failed: {e}")
            return False

    def set_active(self, layer_id: str) -> bool:
        project = _get_project()
        iface = _get_iface(self.iface)
        if not project or not iface:
            return False
        try:
            layer = project.mapLayer(layer_id)
            if layer:
                iface.setActiveLayer(layer)
                return True
        except Exception as e:
            print(f"[LayersAPI] set_active failed: {e}")
        return False

    def get(self, layer_id: str) -> Optional[Dict[str, Any]]:
        project = _get_project()
        if not project:
            return None
        try:
            layer = project.mapLayer(layer_id)
            if not layer:
                return None
            return {"id": layer.id(), "name": layer.name()}
        except Exception:
            return None
