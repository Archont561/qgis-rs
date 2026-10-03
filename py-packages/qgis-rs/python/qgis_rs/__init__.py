"""qgis-rs — Python bindings and CLI for qgis-rs.

Native-speed QGIS rendering, tiling and project inspection, implemented in Rust
and reached through a single JSON call across the PyO3 boundary. Install from
pip or conda-forge::

    pip install qgis-rs
    conda install -c conda-forge qgis-rs

Example::

    >>> from qgis_rs import Project, Extent, TilePlan, ZoomRange, Crs
    >>> project = Project.open("map.qgs")
    >>> print(project.path)
    >>> print(project.info().to_dict())

    >>> extent = Extent.parse("14,50,15,51")
    >>> plan = TilePlan(extent, ZoomRange.parse("10-14"))
    >>> print(f"Would render {plan.tile_count()} tiles")

CLI::

    $ qgis-cli info map.qgs --json
    $ qgis-cli tiles map.qgs -z 10-14 -b 14,50,15,51 --dry-run
    $ qgis-cli render map.qgs -o map.png

Architecture: the classes above are a *client*. They hold values and ask the
Rust engine every question that has an answer — parsing, validation, tile
arithmetic — over the versioned transport in :mod:`qgis_rs._transport`. Adding
an operation to qgis-rs therefore touches the Rust engine and this client, and
never a function signature in between. See
``.knowledge/decisions/D09-wire-protocol-over-ffi.md``.
"""

from __future__ import annotations

from ._api import (
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
    engine_info,
    plan_tiles,
    transport_version,
    version,
)
from ._transport import (
    TRANSPORT_VERSION,
    EngineError,
    EngineIOError,
    InvalidInput,
    ProjectNotFound,
    TransportMismatch,
    Unimplemented,
    invoke,
)

__version__ = version()

# The SDK is a separate distribution; its presence enables the hybrid
# plugin workflow documented in py-packages/qgis-sdk/README.md.
try:  # pragma: no cover - depends on what else is installed
    import qgis_sdk  # type: ignore  # noqa: F401

    HAS_QGIS_SDK = True
except ImportError:  # pragma: no cover
    HAS_QGIS_SDK = False

__all__ = [
    "HAS_QGIS_SDK",
    "MAX_LATITUDE",
    "MAX_ZOOM",
    "TRANSPORT_VERSION",
    "Crs",
    "EngineError",
    "EngineIOError",
    "Extent",
    "InvalidInput",
    "LayerSummary",
    "Project",
    "ProjectInfo",
    "ProjectNotFound",
    "RenderSettings",
    "RenderedMap",
    "Tile",
    "TilePlan",
    "TransportMismatch",
    "Unimplemented",
    "ZoomLevelPlan",
    "ZoomRange",
    "__version__",
    "engine_info",
    "invoke",
    "plan_tiles",
    "transport_version",
    "version",
]
