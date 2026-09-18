"""qgis-sdk — a Python SDK for building QGIS plugins on top of PyQGIS.

The SDK is importable without QGIS installed: only :mod:`qgis_sdk.runtime`
touches PyQGIS, and it does so lazily. That is what makes unit-testing plugin
logic possible on a plain developer machine.
"""

from __future__ import annotations

from .algorithm import Algorithm, OutputSpec, ParamSpec, output, parameter
from .metadata import METADATA_FIELDS, render_metadata, write_metadata
from .plugin import ActionSpec, Plugin, action, class_factory, menu, toolbar
from .runtime import PyQgisImportError, expected_pythonpath, qgis_core, qgis_gui

__version__ = "0.1.0"

__all__ = [
    "METADATA_FIELDS",
    "ActionSpec",
    "Algorithm",
    "OutputSpec",
    "ParamSpec",
    "Plugin",
    "PyQgisImportError",
    "__version__",
    "action",
    "class_factory",
    "expected_pythonpath",
    "menu",
    "output",
    "parameter",
    "qgis_core",
    "qgis_gui",
    "render_metadata",
    "toolbar",
    "write_metadata",
]
