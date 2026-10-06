"""The Hypothesis strategies generate pure values — and only pure values.

doc-5 is explicit that a strategy may not produce a live QGIS object: a
generator that can is a generator that will, somewhere, in a suite that was
supposed to be pure. So these tests assert the *shape* of what comes out, and
pair each strategy with the code that consumes it, which is the only way a
strategy stays honest as the consumer changes.
"""

from __future__ import annotations

import keyword
import re

from hypothesis import given, settings
from hypothesis import strategies as st

from qgis_sdk.testing import ERROR_KINDS, validate_value
from qgis_sdk.testing import strategies as qst

PURE_TYPES = (type(None), bool, int, float, str, list, dict, tuple)

#: One schema exercising every construct the subset has: scalars, an enum, a
#: handle, required members and a closed property set.
ADD_VECTOR_ARGS = {
    "type": "object",
    "properties": {
        "uri": {"type": "string"},
        "count": {"type": "integer"},
        "provider": {"type": "string", "enum": ["ogr", "memory"]},
        "handle": {"$handle": "qgis.layer"},
    },
    "required": ["uri", "handle"],
    "additional_properties": False,
}


@settings(max_examples=100, deadline=None)
@given(extent=qst.extents())
def test_an_extent_is_ordered_and_inside_its_bounds(extent: dict) -> None:
    assert set(extent) == {"xmin", "ymin", "xmax", "ymax"}
    assert extent["xmin"] < extent["xmax"]
    assert extent["ymin"] < extent["ymax"]
    assert -180.0 <= extent["xmin"] <= 180.0


@settings(max_examples=50, deadline=None)
@given(extent=qst.extents(min_value=-20_037_508.0, max_value=20_037_508.0))
def test_an_extent_can_be_asked_for_in_another_unit(extent: dict) -> None:
    """Web Mercator metres, not just degrees — the bounds are a parameter."""
    assert extent["xmax"] <= 20_037_508.0


@settings(max_examples=100, deadline=None)
@given(zoom=qst.zoom_ranges())
def test_a_zoom_range_is_ordered_and_bounded(zoom: tuple) -> None:
    low, high = zoom
    assert 0 <= low <= high <= 24


@settings(max_examples=100, deadline=None)
@given(auth_id=qst.crs_auth_ids())
def test_a_crs_auth_id_splits_into_an_authority_and_a_code(auth_id: str) -> None:
    authority, code = auth_id.split(":")
    assert authority in qst.CRS_AUTHORITIES
    assert code.isdigit()


@settings(max_examples=100, deadline=None)
@given(name=qst.plugin_names())
def test_a_plugin_name_is_a_legal_python_module_name(name: str) -> None:
    """Scaffolding writes a directory and an import with this name, so a
    strategy that can produce ``for`` or ``my-plugin`` is not testing
    scaffolding, it is breaking it."""
    assert re.fullmatch(r"[a-z][a-z0-9_]*", name)
    assert not keyword.iskeyword(name)
    assert name.isidentifier()


@settings(max_examples=100, deadline=None)
@given(spec=qst.field_specs())
def test_a_field_spec_is_a_dict_the_ui_constructor_accepts(spec: dict) -> None:
    """Dicts, not ``FieldSpec`` objects: importing the UI module drags in Qt."""
    assert spec["field_type"] in qst.FIELD_TYPES
    assert spec["name"].isidentifier()
    assert isinstance(spec["label"], str)
    if spec["field_type"] == "spin":
        assert spec["min"] <= spec["max"]
    if spec["field_type"] == "combo":
        assert spec["default"] in spec["options"]


@settings(max_examples=50, deadline=None)
@given(spec=qst.field_specs(field_types=["text"]))
def test_the_field_types_can_be_narrowed(spec: dict) -> None:
    assert spec["field_type"] == "text"


@settings(max_examples=50, deadline=None)
@given(response=qst.network_responses())
def test_a_generated_response_round_trips_its_own_body(response) -> None:
    assert b"".join(response.iter_content(chunk_size=7)) == response.content
    assert response.ok == (200 <= response.status_code < 400)


@settings(max_examples=50, deadline=None)
@given(envelope=qst.bridge_responses(request_id="req-42"))
def test_a_generated_response_envelope_obeys_the_ok_split(envelope: dict) -> None:
    assert envelope["request_id"] == "req-42"
    if envelope["ok"]:
        assert "result" in envelope and "error" not in envelope
    else:
        assert "error" in envelope and "result" not in envelope
        assert envelope["error"]["kind"] in ERROR_KINDS


@settings(max_examples=50, deadline=None)
@given(
    envelope=st.builds(
        dict,
        bridge_version=st.just(1),
        request_id=qst.request_ids(),
        target=st.just("qgis"),
        method=st.just("layers.list"),
        args=st.just({}),
    )
)
def test_request_ids_are_opaque_strings_nothing_parses(envelope: dict) -> None:
    assert isinstance(envelope["request_id"], str)
    assert envelope["request_id"]


@settings(max_examples=100, deadline=None)
@given(value=qst.values_for_schema(ADD_VECTOR_ARGS))
def test_a_generated_value_satisfies_the_schema_it_was_drawn_from(value: dict) -> None:
    assert validate_value(ADD_VECTOR_ARGS, value, "sess-1") is None


@settings(max_examples=100, deadline=None)
@given(
    extent=qst.extents(),
    spec=qst.field_specs(),
    handle=qst.object_handles(),
    path=qst.task_transitions(),
)
def test_nothing_a_strategy_draws_is_a_live_object(
    extent: dict, spec: dict, handle: dict, path: list
) -> None:
    """The rule doc-5 states and this suite has to keep: pure data only."""
    for drawn in (extent, spec, handle, path):
        assert _is_pure(drawn), drawn


def _is_pure(value) -> bool:
    if isinstance(value, (list, tuple)):
        return all(_is_pure(item) for item in value)
    if isinstance(value, dict):
        return all(_is_pure(key) and _is_pure(item) for key, item in value.items())
    return isinstance(value, PURE_TYPES)
