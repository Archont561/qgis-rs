"""Project helpers.

A convenience namespace — :class:`qgis_py.Project` is already the high-level
wrapper (it is a client of the Rust engine, not a thin shell over a pyclass),
so this module re-exports it instead of wrapping it a second time.
"""

from __future__ import annotations

from ._api import LayerSummary, Project, ProjectInfo, plan_tiles

__all__ = ["LayerSummary", "Project", "ProjectInfo", "plan_tiles"]
