"""
Rendering helpers — thin Python wrappers over Rust core.
"""

from __future__ import annotations

from . import _core

# Re-export for convenience
Extent = _core.Extent
Crs = _core.Crs
RenderSettings = _core.RenderSettings
Project = _core.Project
