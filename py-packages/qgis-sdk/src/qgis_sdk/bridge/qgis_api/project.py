"""qgis_sdk.bridge.qgis_api.project — project API."""

from __future__ import annotations

from typing import Any, Dict

from ._resolver import resolve_qgis_resource


class ProjectAPI:
    def info(self) -> Dict[str, Any]:
        project = resolve_qgis_resource("project")
        if not project:
            return {"path": "", "crs": "", "title": ""}
        try:
            return {
                "path": project.fileName(),
                "crs": project.crs().authid() if hasattr(project, "crs") else "",
                "title": project.title() if hasattr(project, "title") else "",
            }
        except Exception as e:
            return {"path": "", "crs": "", "title": "", "error": str(e)}

    def write(self) -> bool:
        project = resolve_qgis_resource("project")
        if not project:
            return False
        try:
            return project.write()
        except Exception:
            return False

    def crs(self) -> str:
        project = resolve_qgis_resource("project")
        if not project:
            return ""
        try:
            return project.crs().authid()
        except Exception:
            return ""

    def set_crs(self, authid: str) -> bool:
        project = resolve_qgis_resource("project")
        if not project:
            return False
        try:
            from qgis.core import QgsCoordinateReferenceSystem
            crs = QgsCoordinateReferenceSystem(authid)
            project.setCrs(crs)
            return True
        except Exception as e:
            print(f"[ProjectAPI] set_crs failed: {e}")
            return False

    def path(self) -> str:
        project = resolve_qgis_resource("project")
        if not project:
            return ""
        try:
            return project.fileName()
        except Exception:
            return ""
