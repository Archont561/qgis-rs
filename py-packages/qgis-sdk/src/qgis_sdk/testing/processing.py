"""Fake processing context, source and sink for Algorithm tests.

The seam an ``Algorithm`` sees: parameter values in, progress and features
out. No QGIS processing framework, no providers, no temporary GeoPackages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .data import FakeFields, mock_features


class FakeContext:
    """Fake processing context for Algorithm tests."""

    def __init__(self, values: Optional[Dict[str, Any]] = None):
        self.values = values or {}
        self.progress: List[float] = []
        self._canceled = False

    def get(self, name, default=None):
        key = getattr(name, "name", name)
        return self.values.get(key, default)

    def set_progress(self, fraction: float):
        self.progress.append(fraction)

    @property
    def is_canceled(self):
        return self._canceled

    def create_sink(self, output, fields=None, geometry_type=None, crs=None):
        return FakeSink()

    def source_path(self, param):
        return f"/tmp/{getattr(param, 'name', param)}.gpkg"

    def sink_path(self, param):
        return f"/tmp/{getattr(param, 'name', param)}_out.gpkg"


class FakeSink:
    """Fake sink for algorithm outputs."""

    def __init__(self):
        self.features_list: List[Any] = []
        self.fields = []
        self.geometry_type = "Point"

    def add_feature(self, feature):
        self.features_list.append(feature)

    @property
    def feature_count(self):
        return len(self.features_list)

    def features(self):
        return iter(self.features_list)

    def dissolve(self):
        if self.features_list:
            self.features_list = self.features_list[:1]


def mock_source(features=None, fields=None, geometry_type="Point", feature_count=None, crs=None):
    """Create fake source (vector layer)."""

    class FakeSource:
        def __init__(self):
            self._features = (
                features
                if features is not None
                else mock_features(10 if feature_count is None else feature_count, geometry_type)
            )
            self._fields = fields or FakeFields()
            self.geometry_type = geometry_type
            self.crs = crs

        @property
        def feature_count(self):
            return len(self._features)

        def features(self, bbox=None, limit=None, filter=None):
            feats = self._features
            if limit:
                feats = feats[:limit]
            return iter(feats)

        @property
        def fields(self):
            return self._fields

    return FakeSource()


def mock_context(values=None):
    """Create fake processing context."""
    return FakeContext(values)


__all__ = ["FakeContext", "FakeSink", "mock_source", "mock_context"]
