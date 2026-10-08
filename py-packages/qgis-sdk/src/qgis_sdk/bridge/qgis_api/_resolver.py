"""Lazy QGIS runtime resolution shared by the built-in QGIS API modules."""

from __future__ import annotations

from typing import Any, Literal


def resolve_qgis_resource(resource: Literal["iface", "project"], iface: Any = None) -> Any:
    """Resolve the host iface or current project without importing QGIS eagerly.

    An explicitly injected iface takes precedence whenever it is not ``None``,
    including falsey objects. QGIS being absent is the only condition converted
    to ``None``; other lookup and singleton errors preserve their behavior.
    """
    if resource == "iface" and iface is not None:
        return iface

    try:
        if resource == "iface":
            from qgis.utils import iface as qgis_iface

            return qgis_iface
        if resource == "project":
            from qgis.core import QgsProject

            return QgsProject.instance()
    except ImportError:
        return None

    raise ValueError(f"Unknown QGIS resource: {resource}")
