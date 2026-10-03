"""Property tests for the pure value seams exposed by the qgis-rs client."""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

import qgis_rs


finite_coordinates = st.floats(
    min_value=-1_000_000,
    max_value=1_000_000,
    allow_nan=False,
    allow_infinity=False,
)


@settings(max_examples=40, deadline=None)
@given(
    first_x=finite_coordinates,
    second_x=finite_coordinates,
    first_y=finite_coordinates,
    second_y=finite_coordinates,
)
def test_extent_text_round_trip_preserves_ordered_edges(
    first_x: float,
    second_x: float,
    first_y: float,
    second_y: float,
) -> None:
    min_x, max_x = sorted((first_x, second_x))
    min_y, max_y = sorted((first_y, second_y))

    extent = qgis_rs.Extent(min_x, min_y, max_x, max_y)

    assert qgis_rs.Extent.parse(str(extent)) == extent


@settings(max_examples=40, deadline=None)
@given(
    minimum=st.integers(min_value=0, max_value=qgis_rs.MAX_ZOOM),
    span=st.integers(min_value=0, max_value=qgis_rs.MAX_ZOOM),
)
def test_zoom_range_string_round_trip_preserves_inclusive_bounds(
    minimum: int,
    span: int,
) -> None:
    maximum = min(qgis_rs.MAX_ZOOM, minimum + span)
    zooms = qgis_rs.ZoomRange(minimum, maximum)

    assert qgis_rs.ZoomRange.parse(str(zooms)) == zooms
    assert zooms.count() == maximum - minimum + 1


@settings(max_examples=40, deadline=None)
@given(code=st.integers(min_value=1, max_value=999_999))
def test_epsg_auth_ids_normalize_case_and_whitespace(code: int) -> None:
    crs = qgis_rs.Crs.from_auth_id(f" epsg:{code} ")

    assert crs.auth_id == f"EPSG:{code}"
