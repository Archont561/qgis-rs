"""The ergonomic client: values here, every answer from the Rust engine.

Each class below holds what the engine told it and asks the engine everything
else. Parsing an extent, validating a zoom range, counting the tiles in a
pyramid, deciding whether a CRS is geographic — all of that is one rule, stated
once in ``crates/qgis-render`` and reached over the transport in
:mod:`qgis_rs._transport`. Nothing in this file recomputes a number the engine
can produce; that is the whole reason the wire is the interface.

See ``.knowledge/decisions/D09-wire-protocol-over-ffi.md``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from ._transport import invoke

__all__ = [
    "MAX_LATITUDE",
    "MAX_ZOOM",
    "Crs",
    "Extent",
    "LayerSummary",
    "Project",
    "ProjectInfo",
    "RenderSettings",
    "RenderedMap",
    "Tile",
    "TilePlan",
    "ZoomLevelPlan",
    "ZoomRange",
    "engine_info",
    "plan_tiles",
    "transport_version",
    "version",
]

ExtentLike = Union["Extent", str, Sequence[float], Mapping[str, float]]
ZoomLike = Union["ZoomRange", int, str, Mapping[str, int]]

_ENGINE_INFO: Optional[Dict[str, Any]] = None


def engine_info() -> Dict[str, Any]:
    """What the engine behind this wheel is, and what it can do.

    Cached: the answer describes the build, and the build does not change
    while the interpreter is running.
    """
    global _ENGINE_INFO  # noqa: PLW0603 - one process-wide cache of a constant answer
    if _ENGINE_INFO is None:
        _ENGINE_INFO = invoke("engine_info")
    return _ENGINE_INFO


def version() -> str:
    """The qgis-rs release this extension was built from."""
    return str(engine_info()["version"])


def transport_version() -> int:
    """The envelope version this extension speaks."""
    return int(engine_info()["transport_version"])


#: Deepest zoom level the engine will plan, straight from the engine.
MAX_ZOOM: int = int(engine_info()["max_zoom"])
#: The Web Mercator latitude limit, straight from the engine.
MAX_LATITUDE: float = float(engine_info()["max_latitude"])


def _extent_payload(value: ExtentLike) -> Any:
    """Anything extent-shaped, in the form the wire accepts.

    Text, four numbers and an :class:`Extent` all reach the same parser in
    Rust, so a caller never has to convert before asking.
    """
    if isinstance(value, Extent):
        return value.to_dict()
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, Sequence):
        edges = [float(edge) for edge in value]
        if len(edges) != 4:
            raise TypeError(f"an extent needs four numbers, got {len(edges)}")
        return {"min_x": edges[0], "min_y": edges[1], "max_x": edges[2], "max_y": edges[3]}
    raise TypeError(f"cannot read {type(value).__name__} as an extent")


def _zoom_payload(value: ZoomLike) -> Any:
    """Anything zoom-shaped, in the form the wire accepts."""
    if isinstance(value, ZoomRange):
        return {"min": value.min, "max": value.max}
    if isinstance(value, Mapping):
        return dict(value)
    return value


class Extent:
    """An axis-aligned rectangle, in whatever CRS produced it.

    Constructing one validates it: ``Extent("15,51,14,50")`` raises rather
    than becoming a value that is wrong later.
    """

    __slots__ = ("max_x", "max_y", "min_x", "min_y")

    def __init__(
        self,
        min_x: Union[float, str],
        min_y: Optional[float] = None,
        max_x: Optional[float] = None,
        max_y: Optional[float] = None,
    ) -> None:
        request: Any
        if isinstance(min_x, str):
            request = min_x
        else:
            request = {
                "min_x": float(min_x),
                "min_y": float(min_y),  # type: ignore[arg-type]
                "max_x": float(max_x),  # type: ignore[arg-type]
                "max_y": float(max_y),  # type: ignore[arg-type]
            }
        edges = invoke("describe_extent", {"extent": request})["extent"]
        self.min_x = float(edges["min_x"])
        self.min_y = float(edges["min_y"])
        self.max_x = float(edges["max_x"])
        self.max_y = float(edges["max_y"])

    @classmethod
    def _from_wire(cls, edges: Mapping[str, float]) -> "Extent":
        """Wrap edges the engine has already validated, without asking again."""
        extent = object.__new__(cls)
        extent.min_x = float(edges["min_x"])
        extent.min_y = float(edges["min_y"])
        extent.max_x = float(edges["max_x"])
        extent.max_y = float(edges["max_y"])
        return extent

    @classmethod
    def parse(cls, text: str) -> "Extent":
        """Parse ``minx,miny,maxx,maxy``, as ``--extent`` and ``--bounds`` do."""
        return cls(str(text))

    def to_dict(self) -> Dict[str, float]:
        """The wire form: the four edges under their wire names."""
        return {
            "min_x": self.min_x,
            "min_y": self.min_y,
            "max_x": self.max_x,
            "max_y": self.max_y,
        }

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """``(min_x, min_y, max_x, max_y)``."""
        return (self.min_x, self.min_y, self.max_x, self.max_y)

    def describe(self) -> Dict[str, Any]:
        """Everything the engine derives from this extent, in one call."""
        return invoke("describe_extent", {"extent": self.to_dict()})

    def width(self) -> float:
        """Width, as the engine measures it."""
        return float(self.describe()["width"])

    def height(self) -> float:
        """Height, as the engine measures it."""
        return float(self.describe()["height"])

    def is_valid(self) -> bool:
        """Whether the edges are finite and ordered."""
        return bool(self.describe()["is_valid"])

    def contains(self, x: float, y: float) -> bool:
        """Whether this extent contains a point in its own CRS."""
        return bool(
            invoke("extent_contains", {"extent": self.to_dict(), "x": float(x), "y": float(y)})[
                "contains"
            ]
        )

    def intersects(self, other: ExtentLike) -> bool:
        """Whether this extent and another share at least one point."""
        return bool(
            invoke(
                "extent_intersects",
                {"extent": self.to_dict(), "other": _extent_payload(other)},
            )["intersects"]
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Extent):
            return self.to_tuple() == other.to_tuple()
        if isinstance(other, (tuple, list)):
            return self.to_tuple() == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.to_tuple())

    def __str__(self) -> str:
        return f"{self.min_x},{self.min_y},{self.max_x},{self.max_y}"

    def __repr__(self) -> str:
        return f"Extent({self.min_x}, {self.min_y}, {self.max_x}, {self.max_y})"


class Crs:
    """A coordinate reference system, addressed by authority code."""

    __slots__ = ("auth_id",)

    def __init__(self, auth_id: Union[str, "Crs"]) -> None:
        described = invoke("describe_crs", {"text": str(auth_id)})
        self.auth_id = str(described["auth_id"])

    @classmethod
    def _from_wire(cls, described: Mapping[str, Any]) -> "Crs":
        """Wrap a CRS the engine already produced, without asking again.

        A project can carry an authority code this build has no entry for;
        reporting what the project says beats refusing to describe it.
        """
        crs = object.__new__(cls)
        crs.auth_id = str(described["auth_id"])
        return crs

    @classmethod
    def from_auth_id(cls, auth_id: str) -> "Crs":
        """``EPSG:3857`` and friends. Raises on anything else."""
        return cls(auth_id)

    @classmethod
    def from_epsg(cls, code: int) -> "Crs":
        """The CRS with this EPSG code."""
        return cls(f"EPSG:{int(code)}")

    @classmethod
    def wgs84(cls) -> "Crs":
        """``EPSG:4326``."""
        return cls("EPSG:4326")

    @classmethod
    def web_mercator(cls) -> "Crs":
        """``EPSG:3857``."""
        return cls("EPSG:3857")

    def describe(self) -> Dict[str, Any]:
        """Name, units and geography, in one call."""
        return invoke("describe_crs", {"text": self.auth_id})

    def name(self) -> str:
        """Human-readable name, as the engine knows it."""
        return str(self.describe()["name"])

    def units(self) -> str:
        """``degrees``, ``meters`` or ``unknown``."""
        return str(self.describe()["units"])

    def is_geographic(self) -> bool:
        """Whether this CRS measures in degrees."""
        return bool(self.describe()["is_geographic"])

    def is_projected(self) -> bool:
        """Whether this CRS measures in metres."""
        return self.units() == "meters"

    def to_dict(self) -> Dict[str, str]:
        """The wire form of a CRS: its authority id."""
        return {"auth_id": self.auth_id}

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Crs):
            return self.auth_id == other.auth_id
        if isinstance(other, str):
            return self.auth_id == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.auth_id)

    def __str__(self) -> str:
        return self.auth_id

    def __repr__(self) -> str:
        return f"Crs({self.auth_id!r})"


class Tile:
    """One tile in an XYZ pyramid."""

    __slots__ = ("x", "y", "z")

    def __init__(self, z: int, x: int, y: int) -> None:
        self.z = int(z)
        self.x = int(x)
        self.y = int(y)

    @classmethod
    def from_lon_lat(cls, z: int, lon: float, lat: float) -> "Tile":
        """The tile covering a longitude/latitude pair, latitude clamped."""
        tile = invoke("tile_from_lon_lat", {"z": int(z), "lon": float(lon), "lat": float(lat)})["tile"]
        return cls(tile["z"], tile["x"], tile["y"])

    def bounds(self) -> Extent:
        """This tile's extent in EPSG:4326."""
        bounds = invoke("tile_bounds", {"tile": self.to_dict()})["bounds"]
        return Extent._from_wire(bounds)

    def to_dict(self) -> Dict[str, int]:
        """The wire form: ``{"z": …, "x": …, "y": …}``."""
        return {"z": self.z, "x": self.x, "y": self.y}

    def to_tuple(self) -> Tuple[int, int, int]:
        """``(z, x, y)``."""
        return (self.z, self.x, self.y)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Tile):
            return self.to_tuple() == other.to_tuple()
        if isinstance(other, (tuple, list)):
            return self.to_tuple() == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.to_tuple())

    def __str__(self) -> str:
        return f"{self.z}/{self.x}/{self.y}"

    def __repr__(self) -> str:
        return f"Tile({self.z}, {self.x}, {self.y})"


class ZoomRange:
    """An inclusive range of zoom levels."""

    __slots__ = ("max", "min")

    def __init__(self, min: int, max: Optional[int] = None) -> None:  # noqa: A002 - the wire's own names
        described = invoke(
            "describe_zoom_range",
            {"zooms": {"min": int(min), "max": int(min if max is None else max)}},
        )["zooms"]
        self.min = int(described["min"])
        self.max = int(described["max"])

    @classmethod
    def _from_wire(cls, described: Mapping[str, int]) -> "ZoomRange":
        """Wrap a range the engine already validated, without asking again."""
        zooms = object.__new__(cls)
        zooms.min = int(described["min"])
        zooms.max = int(described["max"])
        return zooms

    @classmethod
    def parse(cls, text: str) -> "ZoomRange":
        """Parse ``12`` or ``10-14``."""
        described = invoke("describe_zoom_range", {"zooms": str(text)})["zooms"]
        return cls._from_wire(described)

    def count(self) -> int:
        """How many levels the range covers."""
        return int(
            invoke("describe_zoom_range", {"zooms": {"min": self.min, "max": self.max}})["count"]
        )

    def to_dict(self) -> Dict[str, int]:
        """The wire form: ``{"min": …, "max": …}``."""
        return {"min": self.min, "max": self.max}

    def __iter__(self) -> Iterable[int]:
        return iter(range(self.min, self.max + 1))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ZoomRange):
            return (self.min, self.max) == (other.min, other.max)
        if isinstance(other, (tuple, list)):
            return (self.min, self.max) == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.min, self.max))

    def __str__(self) -> str:
        return f"{self.min}" if self.min == self.max else f"{self.min}-{self.max}"

    def __repr__(self) -> str:
        return f"ZoomRange({self.min}, {self.max})"


class ZoomLevelPlan:
    """The tile columns and rows that cover an extent at one zoom level.

    ``tile_count`` comes from the engine rather than from multiplying the two
    ranges here: that one-line rule has one implementation, and it is in Rust.
    """

    __slots__ = ("_tile_count", "x_max", "x_min", "y_max", "y_min", "zoom")

    def __init__(self, level: Mapping[str, int]) -> None:
        self.zoom = int(level["zoom"])
        self.x_min = int(level["x_min"])
        self.x_max = int(level["x_max"])
        self.y_min = int(level["y_min"])
        self.y_max = int(level["y_max"])
        self._tile_count = int(level["tile_count"])

    def tile_count(self) -> int:
        """How many tiles this level contributes."""
        return self._tile_count

    def to_tuple(self) -> Tuple[int, int, int, int, int, int]:
        """``(zoom, x_min, x_max, y_min, y_max, tile_count)``."""
        return (self.zoom, self.x_min, self.x_max, self.y_min, self.y_max, self._tile_count)

    def to_dict(self) -> Dict[str, int]:
        """The wire form of one level."""
        return {
            "zoom": self.zoom,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "y_min": self.y_min,
            "y_max": self.y_max,
            "tile_count": self._tile_count,
        }

    def __eq__(self, other: object) -> bool:
        if isinstance(other, ZoomLevelPlan):
            return self.to_tuple() == other.to_tuple()
        if isinstance(other, (tuple, list)):
            return self.to_tuple() == tuple(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.to_tuple())

    def __repr__(self) -> str:
        return (
            f"ZoomLevelPlan(zoom={self.zoom}, x={self.x_min}..{self.x_max}, "
            f"y={self.y_min}..{self.y_max}, tiles={self._tile_count})"
        )


class TilePlan:
    """Every tile covering an EPSG:4326 extent between two zoom levels.

    One engine call plans the pyramid; the levels and the total are read off
    that answer rather than asked for again per question. Enumerating the
    tiles is a second, explicit call — a five-level plan over a city is 4568
    of them.
    """

    __slots__ = ("_planned", "bounds", "zooms")

    def __init__(self, bounds: ExtentLike, zooms: ZoomLike) -> None:
        self._planned = invoke(
            "plan_tiles",
            {"bounds": _extent_payload(bounds), "zooms": _zoom_payload(zooms)},
        )
        self.bounds = Extent._from_wire(self._planned["bounds"])
        self.zooms = ZoomRange._from_wire(self._planned["zooms"])

    def levels(self) -> List[ZoomLevelPlan]:
        """Every level of the pyramid, shallowest first."""
        return [ZoomLevelPlan(level) for level in self._planned["levels"]]

    def level(self, zoom: int) -> ZoomLevelPlan:
        """One level of the pyramid.

        :raises ValueError: when the plan does not cover that zoom level.
        """
        for level in self.levels():
            if level.zoom == int(zoom):
                return level
        raise ValueError(f"zoom {zoom} is not in {self.zooms}")

    def tile_count(self) -> int:
        """How many tiles the whole pyramid holds."""
        return int(self._planned["tile_count"])

    def iter_tiles(self) -> List[Tile]:
        """Every tile in the plan — a separate ask, because a plan only counts."""
        enumerated = invoke(
            "plan_tiles",
            {
                "bounds": self.bounds.to_dict(),
                "zooms": self.zooms.to_dict(),
                "include_tiles": True,
            },
        )
        return [Tile(tile["z"], tile["x"], tile["y"]) for tile in enumerated["tiles"]]

    def to_dict(self) -> Dict[str, Any]:
        """The engine's own answer, verbatim."""
        return dict(self._planned)

    def __len__(self) -> int:
        return self.tile_count()

    def __repr__(self) -> str:
        return f"TilePlan(bounds={self.bounds}, zooms={self.zooms}, tiles={self.tile_count()})"


class LayerSummary:
    """One layer of a project, as the engine describes it."""

    __slots__ = ("_wire", "crs", "feature_count", "geometry_type", "name", "provider")

    def __init__(self, layer: Mapping[str, Any]) -> None:
        self._wire = dict(layer)
        self.name = str(layer["name"])
        self.provider = str(layer["provider"])
        self.crs = Crs._from_wire(layer["crs"]) if layer.get("crs") else None
        self.feature_count = layer.get("feature_count")
        self.geometry_type = layer.get("geometry_type")

    def to_dict(self) -> Dict[str, Any]:
        """The engine's own answer, verbatim."""
        return dict(self._wire)

    def __repr__(self) -> str:
        return f"LayerSummary({self.name!r}, provider={self.provider!r})"


class ProjectInfo:
    """What the engine can say about a project file.

    The optional fields — CRS, layer count, extent — need the QGIS backend;
    until it is wired up they are ``None`` and ``note`` says why.
    """

    __slots__ = ("_wire", "crs", "extent", "format", "layer_count", "note", "path", "size_bytes")

    def __init__(self, info: Mapping[str, Any]) -> None:
        self._wire = dict(info)
        self.path = str(info["path"])
        self.format = str(info["format"])
        self.size_bytes = int(info["size_bytes"])
        self.crs = Crs._from_wire(info["crs"]) if info.get("crs") else None
        self.layer_count = info.get("layer_count")
        self.extent = Extent._from_wire(info["extent"]) if info.get("extent") else None
        self.note = info.get("note")

    def to_dict(self) -> Dict[str, Any]:
        """The engine's own answer, verbatim — this is what ``--json`` prints."""
        return dict(self._wire)

    def __repr__(self) -> str:
        return f"ProjectInfo({self.path!r}, format={self.format!r}, size_bytes={self.size_bytes})"


class RenderedMap:
    """An image the engine wrote to disk."""

    __slots__ = ("_wire", "bytes", "format", "height", "path", "width")

    def __init__(self, rendered: Mapping[str, Any]) -> None:
        self._wire = dict(rendered)
        self.path = str(rendered["path"])
        self.format = str(rendered["format"])
        self.bytes = int(rendered["bytes"])
        self.width = int(rendered["width"]) if "width" in rendered else None
        self.height = int(rendered["height"]) if "height" in rendered else None

    def to_dict(self) -> Dict[str, Any]:
        """The engine's own answer, verbatim."""
        return dict(self._wire)

    def __repr__(self) -> str:
        return f"RenderedMap({self.path!r}, format={self.format!r}, bytes={self.bytes})"


class RenderSettings:
    """How to render a project.

    Every field is optional and every default lives in ``qgis-render``: an
    omitted field is a field the engine fills in, not one this client guesses.
    """

    __slots__ = ("crs", "dpi", "extent", "height", "layers", "layout", "output", "width")

    def __init__(
        self,
        output: Any,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        dpi: Optional[float] = None,
        crs: Optional[Union[str, Crs]] = None,
        extent: Optional[ExtentLike] = None,
        layers: Optional[Sequence[str]] = None,
        layout: Optional[str] = None,
    ) -> None:
        self.output = str(output)
        self.width = width
        self.height = height
        self.dpi = dpi
        self.crs = crs
        self.extent = extent
        self.layers = list(layers) if layers else []
        self.layout = layout

    def to_payload(self) -> Dict[str, Any]:
        """The native ``render_map`` payload these settings describe, minus the project path."""
        payload: Dict[str, Any] = {"output": self.output}
        if self.width is not None:
            payload["width"] = int(self.width)
        if self.height is not None:
            payload["height"] = int(self.height)
        if self.dpi is not None:
            payload["dpi"] = float(self.dpi)
        if self.crs is not None:
            payload["crs"] = self.crs.auth_id if isinstance(self.crs, Crs) else str(self.crs)
        if self.extent is not None:
            payload["extent"] = _extent_payload(self.extent)
        if self.layers:
            payload["layers"] = list(self.layers)
        if self.layout is not None:
            payload["layout"] = str(self.layout)
        return payload

    def __repr__(self) -> str:
        return f"RenderSettings({self.output!r}, width={self.width}, height={self.height})"


class Project:
    """A QGIS project on disk."""

    __slots__ = ("_info", "format", "path")

    def __init__(self, info: Mapping[str, Any]) -> None:
        self._info = dict(info)
        self.path = str(info["path"])
        self.format = str(info["format"])

    @classmethod
    def open(cls, path: Any) -> "Project":
        """Open a ``.qgs`` or ``.qgz``.

        :raises ProjectNotFound: when the file does not exist.
        :raises InvalidInput: when it is not a QGIS project.
        """
        return cls(invoke("project_info", {"path": str(path)}))

    def info(self) -> ProjectInfo:
        """Describe the project; the optional fields need the QGIS backend."""
        return ProjectInfo(invoke("project_info", {"path": self.path}))

    def layers(self) -> List[LayerSummary]:
        """List the project's layers.

        :raises Unimplemented: until the project-layer operation is routed through the native manager.
        """
        return [LayerSummary(layer) for layer in invoke("project_layers", {"path": self.path})["layers"]]

    def render(
        self,
        output: Any,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        dpi: Optional[float] = None,
        crs: Optional[Union[str, Crs]] = None,
        extent: Optional[ExtentLike] = None,
        layers: Optional[Sequence[str]] = None,
        layout: Optional[str] = None,
        settings: Optional[RenderSettings] = None,
    ) -> RenderedMap:
        """Render the project to an image.

        The output is written by QGIS and the response contains its path and metadata.
        """
        chosen = settings or RenderSettings(
            output,
            width=width,
            height=height,
            dpi=dpi,
            crs=crs,
            extent=extent,
            layers=layers,
            layout=layout,
        )
        payload = {"project": self.path}
        payload.update(chosen.to_payload())
        return RenderedMap(invoke("render_map", payload))

    def __repr__(self) -> str:
        return f"Project({self.path!r}, format={self.format!r})"


def plan_tiles(bounds: ExtentLike, zooms: ZoomLike) -> Tuple[int, List[ZoomLevelPlan]]:
    """Plan a pyramid and return ``(total, levels)``.

    The plain shape, for callers that want the numbers rather than an object;
    :class:`TilePlan` is the same answer with the tiles reachable.
    """
    planned = invoke(
        "plan_tiles", {"bounds": _extent_payload(bounds), "zooms": _zoom_payload(zooms)}
    )
    return int(planned["tile_count"]), [ZoomLevelPlan(level) for level in planned["levels"]]
