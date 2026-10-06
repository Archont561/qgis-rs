"""Builders for the pure data a processing test needs.

Features, geometries and field sets, with no QGIS type behind them. They carry
exactly the surface the SDK's own code touches — anything more would be a
reimplementation of QGIS, which doc-5 rules out: "fakes expose only the
behavior consumed by production code".
"""

from __future__ import annotations


class FakeFeature:
    """Fake QgsFeature."""

    def __init__(self, fid=0, attributes=None, geometry=None):
        self.id = fid
        self._attributes = attributes or {"name": f"feature_{fid}"}
        self._geometry = geometry or FakeGeometry()

    def __getitem__(self, key):
        return self._attributes.get(key)

    @property
    def geometry(self):
        return self._geometry

    @geometry.setter
    def geometry(self, geom):
        self._geometry = geom

    def clone(self):
        return FakeFeature(self.id, dict(self._attributes), self._geometry)


class FakeGeometry:
    """Fake QgsGeometry."""

    def __init__(self, wkt="POINT(0 0)", area=1.0):
        self._wkt = wkt
        self._area = area

    @property
    def area(self):
        return self._area

    def buffer(self, distance, segments=8, end_cap_style=None):
        return FakeGeometry(f"BUFFER({self._wkt}, {distance})", area=self._area + distance)

    def to_wkt(self):
        return self._wkt


class FakeFields:
    """Fake QgsFields."""

    def __init__(self, names=None):
        self.names = names or ["name", "id"]


def mock_features(count=10, geometry_type="Point"):
    """Create list of fake features."""
    return [FakeFeature(fid=i) for i in range(count)]


__all__ = ["FakeFeature", "FakeGeometry", "FakeFields", "mock_features"]
