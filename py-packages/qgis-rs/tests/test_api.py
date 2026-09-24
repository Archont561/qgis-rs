"""Python-side smoke tests for the qgis-rs PyO3 boundary.

Core geometry and tile-planning logic is tested in the Rust qgis-render crate;
these checks keep the language binding's public surface and conversions honest.
"""

from __future__ import annotations

import os

import pytest

import qgis_rs


def test_native_extension_is_used_in_ci() -> None:
    assert isinstance(qgis_rs._USING_FALLBACK, bool)
    if os.environ.get("QGIS_REQUIRE_NATIVE") == "1":
        assert qgis_rs._USING_FALLBACK is False


def test_public_types_and_values_cross_the_pyo3_boundary() -> None:
    assert qgis_rs.version() == qgis_rs.__version__
    for name in ("Extent", "Crs", "Tile", "ZoomRange", "TilePlan", "Project"):
        assert hasattr(qgis_rs, name)

    extent = qgis_rs.Extent.parse("14,50,15,51")
    assert extent.to_tuple() == (14.0, 50.0, 15.0, 51.0)

    crs = qgis_rs.Crs.from_epsg(4326)
    assert crs.auth_id == "EPSG:4326"

    plan = qgis_rs.TilePlan(extent, qgis_rs.ZoomRange.parse("10-14"))
    assert isinstance(plan.tile_count(), int)
    assert plan.tile_count() == 4568


def test_plan_tiles_tuple_shape_crosses_the_boundary() -> None:
    total, levels = qgis_rs.plan_tiles("14,50,15,51", "10-14")

    assert isinstance(total, int)
    assert len(levels) == 5
    assert levels[0] == (10, 551, 554, 342, 347, 24)


def test_rust_errors_become_python_value_errors() -> None:
    with pytest.raises(ValueError, match="extent"):
        qgis_rs.Extent.parse("not-an-extent")


def test_project_path_and_info_cross_the_boundary(tmp_path) -> None:
    path = tmp_path / "map.qgs"
    path.write_text("<qgis></qgis>", encoding="utf-8")

    project = qgis_rs.Project.open(str(path))
    info = project.info()

    assert project.format == "qgs"
    assert info.format == "qgs"
    assert info.size_bytes > 0
    assert info.note is not None
