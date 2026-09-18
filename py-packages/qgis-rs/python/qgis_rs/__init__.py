"""
qgis-rs — Python bindings and CLI for qgis-rs

Native-speed QGIS rendering, tiling, and project inspection, implemented in Rust
and exposed to Python via PyO3. Install from pip or conda-forge:

    pip install qgis-rs
    conda install -c conda-forge qgis-rs

Both the API and the `qgis-cli` command run at native Rust speed.

Example:
    >>> from qgis_rs import Project, Extent, TilePlan, ZoomRange, Crs
    >>> project = Project.open("map.qgs")
    >>> print(project.path)
    >>> info = project.info()
    >>> print(info.to_dict())

    >>> extent = Extent.parse("14,50,15,51")
    >>> zooms = ZoomRange.parse("10-14")
    >>> plan = TilePlan(extent, zooms)
    >>> print(f"Would render {plan.tile_count()} tiles")

CLI:
    $ qgis-cli info map.qgs --json
    $ qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 --dry-run
    $ qgis-cli render map.qgs -o map.png
"""

from __future__ import annotations

try:
    from ._core import (
        MAX_LATITUDE,
        MAX_ZOOM,
        Crs,
        Extent,
        LayerSummary,
        Project,
        ProjectInfo,
        RenderedMap,
        RenderSettings,
        Tile,
        TilePlan,
        ZoomLevelPlan,
        ZoomRange,
        plan_tiles,
        version,
    )
    _USING_FALLBACK = False
except ImportError as _exc:  # pragma: no cover - fallback path for dev without cargo
    # Fallback to pure-Python implementation when Rust extension is not built.
    # This allows `pip install -e .` and tests to work without cargo, but at
    # reduced speed. The real wheel built by maturin will always have _core.
    import warnings

    warnings.warn(
        f"qgis_rs._core extension not found ({_exc}), using pure-Python fallback. "
        "For native speed, build with: pip install maturin && (cd py-packages/qgis-rs && maturin develop)",
        ImportWarning,
        stacklevel=2,
    )
    from ._fallback import (
        MAX_LATITUDE,
        MAX_ZOOM,
        Crs,
        Extent,
        LayerSummary,
        Project,
        ProjectInfo,
        RenderedMap,
        RenderSettings,
        Tile,
        TilePlan,
        ZoomLevelPlan,
        ZoomRange,
        plan_tiles,
        version,
    )

    _USING_FALLBACK = True

# High-level Python wrappers / convenience re-exports — lazy to avoid circular imports
# `project` module is imported lazily via importlib when needed, but we try here
# after _core is resolved.
try:
    from . import cli as cli_module  # noqa: F401
except Exception:
    cli_module = None  # type: ignore

__version__ = version()

# Provide high-level Project wrapper as qgis_rs.ProjectHighLevel if desired
try:
    from .project import Project as ProjectHighLevel  # noqa: F401
except Exception:
    ProjectHighLevel = Project  # type: ignore  # fallback to Rust Project directly
__all__ = [
    "MAX_LATITUDE",
    "MAX_ZOOM",
    "Crs",
    "Extent",
    "LayerSummary",
    "Project",
    "ProjectInfo",
    "RenderedMap",
    "RenderSettings",
    "Tile",
    "TilePlan",
    "ZoomLevelPlan",
    "ZoomRange",
    "__version__",
    "_USING_FALLBACK",
    "plan_tiles",
    "version",
]

# Optional: try to import qgis_sdk if available for hybrid mode
try:
    import qgis_sdk  # type: ignore  # noqa: F401
    HAS_QGIS_SDK = True
except ImportError:
    HAS_QGIS_SDK = False
