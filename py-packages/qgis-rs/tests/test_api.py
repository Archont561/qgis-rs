"""The Python client, tested across the real FFI boundary.

Geometry and tile arithmetic are tested in the Rust crates; what these checks
own is the boundary itself — that the transport is live, that values survive
the JSON round trip, and that an engine refusal arrives as the Python
exception a caller would try to catch.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import qgis_rs
from qgis_rs import _transport


def test_the_transport_is_the_compiled_extension() -> None:
    # The import of qgis_rs._core is what makes this package work at all: there
    # is no pure-Python fallback behind it, so a missing extension is an
    # ImportError at import time rather than a silently different answer.
    assert _transport.TRANSPORT_VERSION == qgis_rs.TRANSPORT_VERSION
    assert qgis_rs.transport_version() == qgis_rs.TRANSPORT_VERSION
    assert _core_is_compiled()


def _core_is_compiled() -> bool:
    from qgis_rs import _core  # type: ignore[attr-defined]

    return _core.__file__.endswith((".so", ".pyd", ".dylib"))


def test_the_engine_describes_itself() -> None:
    info = qgis_rs.engine_info()

    assert info["engine"] == "qgis-engine"
    assert info["version"] == qgis_rs.version() == qgis_rs.__version__
    assert info["transport_version"] == qgis_rs.TRANSPORT_VERSION
    assert "plan_tiles" in info["operations"]
    assert qgis_rs.MAX_ZOOM == 22


def test_public_types_and_values_cross_the_boundary() -> None:
    for name in ("Extent", "Crs", "Tile", "ZoomRange", "TilePlan", "Project"):
        assert hasattr(qgis_rs, name)

    extent = qgis_rs.Extent.parse("14,50,15,51")
    assert extent.to_tuple() == (14.0, 50.0, 15.0, 51.0)
    assert extent.width() == 1.0
    assert extent.contains(14.5, 50.5)
    assert not extent.intersects("20,20,30,30")

    crs = qgis_rs.Crs.from_epsg(4326)
    assert crs.auth_id == "EPSG:4326"
    assert crs.is_geographic()
    assert crs.units() == "degrees"

    plan = qgis_rs.TilePlan(extent, qgis_rs.ZoomRange.parse("10-14"))
    assert plan.tile_count() == 4568
    assert plan.levels()[0].tile_count() == 24
    assert plan.level(10).to_tuple() == (10, 551, 554, 342, 347, 24)


def test_an_extent_can_be_given_the_way_the_caller_has_it() -> None:
    # Text, a sequence and an Extent all reach the same engine parser, so a
    # caller never has to convert before asking.
    for bounds in ("14,50,15,51", [14, 50, 15, 51], qgis_rs.Extent(14, 50, 15, 51)):
        assert qgis_rs.TilePlan(bounds, 10).tile_count() == 24


def test_tiles_round_trip_through_the_engine() -> None:
    tile = qgis_rs.Tile.from_lon_lat(10, 13.9, 51.1)

    assert (tile.z, tile.x, tile.y) == (10, 551, 342)
    assert tile.bounds().min_x == 13.7109375
    assert str(tile) == "10/551/342"


def test_plan_tiles_tuple_shape_crosses_the_boundary() -> None:
    total, levels = qgis_rs.plan_tiles("14,50,15,51", "10-14")

    assert isinstance(total, int)
    assert total == 4568
    assert len(levels) == 5
    assert levels[0] == (10, 551, 554, 342, 347, 24)


def test_enumerating_tiles_is_a_separate_ask() -> None:
    plan = qgis_rs.TilePlan("14,50,15,51", 10)
    tiles = plan.iter_tiles()

    assert len(tiles) == plan.tile_count()
    assert tiles[0] == qgis_rs.Tile(10, 551, 342)


def test_engine_refusals_arrive_as_python_exceptions() -> None:
    with pytest.raises(ValueError, match="extent"):
        qgis_rs.Extent.parse("not-an-extent")
    with pytest.raises(ValueError, match="zoom range"):
        qgis_rs.ZoomRange.parse("14-10")
    with pytest.raises(ValueError, match="coordinate reference system"):
        qgis_rs.Crs.from_auth_id("3857")
    with pytest.raises(FileNotFoundError, match="project not found"):
        qgis_rs.Project.open("/nope/missing.qgs")

    # Every one of them is also an EngineError carrying the wire `kind`, which
    # is what a caller branches on when the prose is not enough.
    with pytest.raises(qgis_rs.EngineError) as caught:
        qgis_rs.Extent.parse("not-an-extent")
    assert caught.value.kind == "invalid_extent"


def test_work_that_needs_qgis_says_so(tmp_path) -> None:
    path = tmp_path / "map.qgs"
    path.write_text("<qgis></qgis>", encoding="utf-8")
    project = qgis_rs.Project.open(str(path))

    with pytest.raises(NotImplementedError, match="QGIS backend"):
        project.layers()
    with pytest.raises(NotImplementedError, match="QGIS backend"):
        project.render(tmp_path / "map.png")


def test_project_path_and_info_cross_the_boundary(tmp_path) -> None:
    path = tmp_path / "map.qgs"
    path.write_text("<qgis></qgis>", encoding="utf-8")

    project = qgis_rs.Project.open(str(path))
    info = project.info()

    assert project.format == "qgs"
    assert info.format == "qgs"
    assert info.size_bytes > 0
    assert info.note is not None
    assert info.to_dict()["size_bytes"] == info.size_bytes


def test_a_raw_request_can_be_sent_when_a_client_type_is_missing() -> None:
    # The transport is public: an operation this client has no class for is
    # still reachable, which is what keeps a new engine usable from an older
    # wheel.
    echoed = qgis_rs.invoke("ping", {"any": "payload"})

    assert echoed["echo"] == {"any": "payload"}
    assert echoed["engine"] == "qgis-engine"


def _layer_lifecycle_fixture() -> dict:
    fixture = Path(__file__).resolve().parents[3] / "test-fixtures" / "layer-lifecycle.json"
    return json.loads(fixture.read_text(encoding="utf-8"))


def test_layer_lifecycle_golden_values_match_the_shared_wire_fixture() -> None:
    fixture = _layer_lifecycle_fixture()
    operations = qgis_rs.engine_info()["operations"]

    for operation in ("layer_open", "layer_info", "layer_close", "layer_features"):
        assert operation in operations
        request = fixture["operations"][operation]["request"]
        assert request["transport_version"] == qgis_rs.TRANSPORT_VERSION
        assert request["operation"] == operation

    assert fixture["operations"]["layer_open"]["result"] == {
        "layer_id": 7,
        "is_valid": True,
        "name": "points",
    }
    info = fixture["operations"]["layer_info"]["result"]
    assert info["feature_count"] == 3
    assert [field["name"] for field in info["fields"]] == ["fid", "name"]

    page = fixture["operations"]["layer_features"]["result"]
    assert page["limit"] == 2
    assert page["next_offset"] == 2
    assert len(page["features"]) == 2
    assert page["features"][0]["attributes"] == {"fid": 1, "name": "alpha"}
    assert fixture["errors"] == {
        "closed_layer": "invalid_object_id",
        "invalid_layer": "invalid_object_id",
    }
