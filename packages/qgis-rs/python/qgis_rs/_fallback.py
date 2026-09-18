"""
Pure-Python fallback for qgis_rs when Rust extension is not built.

This mirrors the Rust API but runs in Python — slower, but allows development
and testing without cargo. When the Rust extension is available, _core is used
for native speed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

MAX_LATITUDE = 85.0511287798066
MAX_ZOOM = 22


class Extent:
    def __init__(self, min_x: float, min_y: float, max_x: float, max_y: float):
        if not all(math.isfinite(v) for v in (min_x, min_y, max_x, max_y)):
            raise ValueError(f"invalid extent: {min_x},{min_y},{max_x},{max_y} — not finite")
        if min_x > max_x or min_y > max_y:
            raise ValueError(f"invalid extent: {min_x},{min_y},{max_x},{max_y} — must be ordered min<=max")
        self._min_x = min_x
        self._min_y = min_y
        self._max_x = max_x
        self._max_y = max_y

    @staticmethod
    def parse(text: str) -> "Extent":
        parts = [p.strip() for p in text.split(",")]
        if len(parts) != 4:
            raise ValueError(f"invalid extent: {text!r} — expected minx,miny,maxx,maxy")
        try:
            values = [float(p) for p in parts]
        except ValueError:
            raise ValueError(f"invalid extent: {text!r} — not numbers")
        return Extent(*values)

    @property
    def min_x(self) -> float: return self._min_x
    @property
    def min_y(self) -> float: return self._min_y
    @property
    def max_x(self) -> float: return self._max_x
    @property
    def max_y(self) -> float: return self._max_y

    def width(self) -> float: return self._max_x - self._min_x
    def height(self) -> float: return self._max_y - self._min_y
    def is_valid(self) -> bool: return self._min_x <= self._max_x and self._min_y <= self._max_y
    def contains(self, x: float, y: float) -> bool: return self._min_x <= x <= self._max_x and self._min_y <= y <= self._max_y
    def intersects(self, other: "Extent") -> bool:
        return self._min_x <= other._max_x and other._min_x <= self._max_x and self._min_y <= other._max_y and other._min_y <= self._max_y

    def to_tuple(self) -> Tuple[float, float, float, float]: return (self._min_x, self._min_y, self._max_x, self._max_y)
    def to_list(self) -> List[float]: return [self._min_x, self._min_y, self._max_x, self._max_y]

    def __str__(self) -> str: return f"{self._min_x},{self._min_y},{self._max_x},{self._max_y}"
    def __repr__(self) -> str: return f"Extent({self._min_x},{self._min_y},{self._max_x},{self._max_y})"
    def __eq__(self, other) -> bool: return isinstance(other, Extent) and self.to_tuple() == other.to_tuple()


class Crs:
    KNOWN = {
        "EPSG:4326": ("WGS 84", "degrees", True),
        "EPSG:4258": ("ETRS89", "degrees", True),
        "EPSG:3857": ("WGS 84 / Pseudo-Mercator", "meters", False),
        "EPSG:32633": ("WGS 84 / UTM zone 33N", "meters", False),
        "EPSG:2180": ("ETRS89 / Poland CS92", "meters", False),
    }

    def __init__(self, auth_id: str):
        self._auth_id = self._validate(auth_id)

    @staticmethod
    def _validate(auth_id: str) -> str:
        trimmed = auth_id.strip()
        if ":" not in trimmed:
            raise ValueError(f"unknown CRS: {auth_id!r} — expected AUTHORITY:CODE e.g. EPSG:3857")
        authority, code = trimmed.split(":", 1)
        if not authority or not authority.isalpha() or not code.isdigit():
            raise ValueError(f"unknown CRS: {auth_id!r}")
        return trimmed.upper()

    @staticmethod
    def from_auth_id(auth_id: str) -> "Crs": return Crs(auth_id)
    @staticmethod
    def from_epsg(code: int) -> "Crs": return Crs(f"EPSG:{code}")
    @staticmethod
    def wgs84() -> "Crs": return Crs("EPSG:4326")
    @staticmethod
    def web_mercator() -> "Crs": return Crs("EPSG:3857")

    @property
    def auth_id(self) -> str: return self._auth_id
    def name(self) -> Optional[str]: return self.KNOWN.get(self._auth_id, (None,))[0]
    def is_geographic(self) -> bool:
        info = self.KNOWN.get(self._auth_id)
        return info[2] if info else False
    def is_projected(self) -> bool:
        info = self.KNOWN.get(self._auth_id)
        if info:
            return not info[2]
        # Unknown CRS — assume projected if not 4326-like
        return self._auth_id != "EPSG:4326"

    def __str__(self): return self._auth_id
    def __repr__(self): return f"Crs({self._auth_id})"
    def __eq__(self, other): return isinstance(other, Crs) and self._auth_id == other._auth_id


def _tiles_per_side(z: int) -> int: return 1 << z

def _lat_to_y(z: int, lat: float) -> float:
    side = _tiles_per_side(z)
    clamped = max(min(lat, MAX_LATITUDE), -MAX_LATITUDE)
    rad = math.radians(clamped)
    merc = math.log(math.tan(rad) + 1.0 / math.cos(rad))
    return (1.0 - merc / math.pi) / 2.0 * side

def _x_to_lon(x: int, side: float) -> float: return x / side * 360.0 - 180.0
def _y_to_lat(y: int, side: float) -> float:
    n = math.pi * (1.0 - 2.0 * y / side)
    return math.degrees(math.atan(math.sinh(n)))

def _clamp_index(v: float, side: float) -> float: return max(0.0, min(v, side - 1.0))


class Tile:
    def __init__(self, z: int, x: int, y: int):
        self._z = z
        self._x = x
        self._y = y

    @staticmethod
    def from_lon_lat(z: int, lon: float, lat: float) -> "Tile":
        side = _tiles_per_side(z)
        x = math.floor((lon + 180.0) / 360.0 * side)
        y = _lat_to_y(z, lat)
        return Tile(z, int(_clamp_index(x, side)), int(_clamp_index(y, side)))

    @property
    def z(self): return self._z
    @property
    def x(self): return self._x
    @property
    def y(self): return self._y

    def bounds(self) -> Extent:
        side = float(_tiles_per_side(self._z))
        return Extent(
            _x_to_lon(self._x, side),
            _y_to_lat(self._y + 1, side),
            _x_to_lon(self._x + 1, side),
            _y_to_lat(self._y, side),
        )

    def __str__(self): return f"{self._z}/{self._x}/{self._y}"
    def __repr__(self): return f"Tile(z={self._z}, x={self._x}, y={self._y})"
    def __eq__(self, other): return isinstance(other, Tile) and (self._z, self._x, self._y) == (other._z, other._x, other._y)
    def __hash__(self): return hash((self._z, self._x, self._y))


class ZoomRange:
    def __init__(self, min: int, max: int):
        if min > max or max > MAX_ZOOM:
            raise ValueError(f"invalid zoom range: {min}-{max}")
        self._min = min
        self._max = max

    @staticmethod
    def parse(text: str) -> "ZoomRange":
        t = text.strip()
        if "-" in t:
            low, high = t.split("-", 1)
            try:
                mn = int(low.strip())
                mx = int(high.strip())
            except ValueError:
                raise ValueError(f"invalid zoom range: {text!r}")
            return ZoomRange(mn, mx)
        else:
            try:
                v = int(t)
            except ValueError:
                raise ValueError(f"invalid zoom range: {text!r}")
            return ZoomRange(v, v)

    @property
    def min(self): return self._min
    @property
    def max(self): return self._max
    def count(self): return self._max - self._min + 1
    def __str__(self): return f"{self._min}" if self._min == self._max else f"{self._min}-{self._max}"
    def __repr__(self): return f"ZoomRange({self._min}-{self._max})"
    def __eq__(self, other): return isinstance(other, ZoomRange) and (self._min, self._max) == (other._min, other._max)


@dataclass
class ZoomLevelPlan:
    zoom: int
    x_min: int
    x_max: int
    y_min: int
    y_max: int
    def tile_count(self): return (self.x_max - self.x_min + 1) * (self.y_max - self.y_min + 1)


class TilePlan:
    def __init__(self, bounds: Extent, zooms: ZoomRange):
        if not bounds.is_valid():
            raise ValueError(f"invalid extent: {bounds}")
        self._bounds = bounds
        self._zooms = zooms

    @property
    def bounds(self): return self._bounds
    @property
    def zooms(self): return self._zooms

    def level(self, zoom: int) -> ZoomLevelPlan:
        side = float(_tiles_per_side(zoom))
        x_min = int(_clamp_index(math.floor((self._bounds.min_x + 180.0) / 360.0 * side), side))
        x_max = int(_clamp_index(math.floor((self._bounds.max_x + 180.0) / 360.0 * side), side))
        y_min = int(_clamp_index(_lat_to_y(zoom, self._bounds.max_y), side))
        y_max = int(_clamp_index(_lat_to_y(zoom, self._bounds.min_y), side))
        return ZoomLevelPlan(zoom, x_min, x_max, y_min, y_max)

    def levels(self) -> List[ZoomLevelPlan]:
        return [self.level(z) for z in range(self._zooms.min, self._zooms.max + 1)]

    def tile_count(self) -> int:
        return sum(l.tile_count() for l in self.levels())

    def iter_tiles(self) -> List[Tile]:
        tiles = []
        for lvl in self.levels():
            for y in range(lvl.y_min, lvl.y_max + 1):
                for x in range(lvl.x_min, lvl.x_max + 1):
                    tiles.append(Tile(lvl.zoom, x, y))
        return tiles

    def __repr__(self):
        return f"TilePlan(bounds={self._bounds}, zooms={self._zooms.min}-{self._zooms.max}, tiles={self.tile_count()})"


def plan_tiles(bounds: str, zoom: str):
    extent = Extent.parse(bounds)
    zooms = ZoomRange.parse(zoom)
    plan = TilePlan(extent, zooms)
    total = plan.tile_count()
    levels = [(l.zoom, l.x_min, l.x_max, l.y_min, l.y_max, l.tile_count()) for l in plan.levels()]
    return total, levels


# Project handling (pure path check, no QGIS)

class ProjectFormat:
    Qgs = "qgs"
    Qgz = "qgz"

class ProjectInfo:
    def __init__(self, path: Path, fmt: str, size_bytes: int, note: Optional[str] = None):
        self._path = path
        self._format = fmt
        self._size_bytes = size_bytes
        self._note = note
        self._crs = None
        self._layer_count = None
        self._extent = None

    @property
    def path(self): return str(self._path)
    @property
    def format(self): return self._format
    @property
    def size_bytes(self): return self._size_bytes
    @property
    def crs(self): return self._crs
    @property
    def layer_count(self): return self._layer_count
    @property
    def extent(self): return self._extent
    @property
    def note(self): return self._note

    def to_dict(self):
        return {
            "path": self.path,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "crs": None,
            "layer_count": None,
            "extent": None,
            "note": self._note,
        }

    def __repr__(self):
        return f"ProjectInfo(path={self._path}, format={self._format}, size={self._size_bytes})"

class LayerSummary:
    def __init__(self, name: str, provider: str):
        self._name = name
        self._provider = provider
    @property
    def name(self): return self._name
    @property
    def provider(self): return self._provider
    @property
    def crs(self): return None
    @property
    def feature_count(self): return None
    @property
    def geometry_type(self): return None

class RenderedMap:
    def __init__(self, path: str, bytes: int):
        self._path = path
        self._bytes = bytes
    @property
    def path(self): return self._path
    @property
    def bytes(self): return self._bytes

class Project:
    def __init__(self, path: Path, fmt: str):
        self._path = path
        self._fmt = fmt

    @staticmethod
    def open(path: str) -> "Project":
        p = Path(path)
        if not p.exists():
            raise ValueError(f"project not found: {path}")
        ext = p.suffix.lstrip(".").lower()
        if ext not in ("qgs", "qgz"):
            raise ValueError(f"unsupported project: {path} — expected .qgs or .qgz")
        return Project(p, ext)

    @property
    def path(self): return str(self._path)
    @property
    def format(self): return self._fmt

    def info(self) -> ProjectInfo:
        size = self._path.stat().st_size
        return ProjectInfo(self._path, self._fmt, size, note="CRS, layer count and extent need the QGIS backend, which is not wired up yet")

    def layers(self):
        raise ValueError("listing project layers: needs the QGIS backend, which is not wired up yet")

    def render(self, output: str, width=None, height=None, extent=None, crs=None, dpi=None):
        raise ValueError("rendering a project: needs the QGIS backend, which is not wired up yet")

    def __repr__(self): return f"Project(path={self._path})"

class RenderSettings:
    def __init__(self, output: str, width: int = 1024, height: int = 768, dpi: float = 96.0):
        if "." not in output or output.endswith("-"):
            # simplistic check
            if not any(output.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".svg", ".pdf"]):
                raise ValueError(f"unknown image format: {output}")
        self._output = output
        self._width = width
        self._height = height
        self._dpi = dpi
        self._extent = None
        self._crs = None
        self._layers: List[str] = []

    @property
    def width(self): return self._width
    @property
    def height(self): return self._height
    @property
    def dpi(self): return self._dpi

    def with_extent(self, extent: Extent): 
        self._extent = extent
        return self
    def with_crs(self, crs: Crs):
        self._crs = crs
        return self
    def with_dpi(self, dpi: float):
        self._dpi = dpi
        return self
    def with_layers(self, layers: List[str]):
        self._layers = layers
        return self
    def __repr__(self):
        return f"RenderSettings(width={self._width}, height={self._height}, dpi={self._dpi})"

def version() -> str:
    return "0.1.0-fallback"
