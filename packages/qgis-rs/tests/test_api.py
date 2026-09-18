"""Tests for qgis_rs Python API — pure Rust, no QGIS needed."""

import pytest

def test_import():
    import qgis_rs
    assert hasattr(qgis_rs, "__version__")
    assert hasattr(qgis_rs, "Extent")
    assert hasattr(qgis_rs, "Crs")
    assert hasattr(qgis_rs, "TilePlan")

def test_extent_parse():
    from qgis_rs import Extent
    e = Extent.parse("14,50,15,51")
    assert e.min_x == 14.0
    assert e.min_y == 50.0
    assert e.max_x == 15.0
    assert e.max_y == 51.0
    assert e.width() == 1.0
    assert e.height() == 1.0
    assert e.is_valid()
    assert e.contains(14.5, 50.5)
    assert not e.contains(13.0, 50.5)
    assert e.to_tuple() == (14.0, 50.0, 15.0, 51.0)

    e2 = Extent(14.0, 50.0, 15.0, 51.0)
    assert e == e2

def test_extent_invalid():
    from qgis_rs import Extent
    with pytest.raises(ValueError):
        Extent.parse("14,50,15")  # incomplete
    with pytest.raises(ValueError):
        Extent.parse("15,50,14,51")  # reversed
    with pytest.raises(ValueError):
        Extent(15.0, 50.0, 14.0, 51.0)  # invalid ordered

def test_crs():
    from qgis_rs import Crs
    crs = Crs.from_epsg(4326)
    assert crs.auth_id == "EPSG:4326"
    assert crs.is_geographic()
    assert not crs.is_projected()

    crs2 = Crs.from_auth_id("EPSG:3857")
    assert crs2.auth_id == "EPSG:3857"
    assert crs2.is_projected()

    assert Crs.wgs84().auth_id == "EPSG:4326"
    assert Crs.web_mercator().auth_id == "EPSG:3857"

    with pytest.raises(ValueError):
        Crs.from_auth_id("invalid")

def test_tile():
    from qgis_rs import Tile
    t = Tile(10, 551, 342)
    assert t.z == 10
    assert t.x == 551
    assert t.y == 342

    # from lon/lat
    t2 = Tile.from_lon_lat(10, 0.0, 0.0)
    assert t2 == Tile(10, 512, 512)

    bounds = t.bounds()
    assert bounds.is_valid()

def test_zoom_range():
    from qgis_rs import ZoomRange
    zr = ZoomRange.parse("10-14")
    assert zr.min == 10
    assert zr.max == 14
    assert zr.count() == 5

    single = ZoomRange.parse("12")
    assert single.min == 12
    assert single.max == 12

    with pytest.raises(ValueError):
        ZoomRange.parse("14-10")

def test_tile_plan():
    from qgis_rs import Extent, ZoomRange, TilePlan
    extent = Extent.parse("14,50,15,51")
    zooms = ZoomRange.parse("10-14")
    plan = TilePlan(extent, zooms)
    assert plan.tile_count() == 4568
    levels = plan.levels()
    assert len(levels) == 5
    assert levels[0].zoom == 10
    assert levels[0].tile_count() == 24

    tiles = plan.iter_tiles()
    assert len(tiles) == 4568
    assert tiles[0].z == 10

def test_plan_tiles_function():
    from qgis_rs import plan_tiles
    total, levels = plan_tiles("14,50,15,51", "10-14")
    assert total == 4568
    assert len(levels) == 5
    # each level: (zoom, x_min, x_max, y_min, y_max, count)
    assert levels[0][0] == 10
    assert levels[0][5] == 24

def test_project_open(tmp_path):
    from qgis_rs import Project
    # Create dummy .qgs file
    p = tmp_path / "map.qgs"
    p.write_text("<qgis></qgis>")

    proj = Project.open(str(p))
    assert proj.format == "qgs"
    assert "map.qgs" in proj.path

    info = proj.info()
    assert info.format == "qgs"
    assert info.size_bytes > 0
    assert info.note is not None  # QGIS backend not wired

    # Missing file should error
    with pytest.raises(ValueError):
        Project.open(str(tmp_path / "nonexistent.qgs"))

def test_version():
    from qgis_rs import version
    v = version()
    assert isinstance(v, str)
    assert len(v) > 0
