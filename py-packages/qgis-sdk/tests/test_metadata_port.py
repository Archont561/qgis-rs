"""The metadata field table and dict renderer ported from the retired Rust module.

`metadata_fields()` and `render_metadata_from_dict()` were pyfunctions in the
removed `crates/qgis-sdk`. The port uses the field table `render_metadata`
already ships (`METADATA_FIELDS`), so there is one table, not two. The Rust
behaviour is kept: fields come out in the table's order, `None` and blank values
are skipped, strings are trimmed, lists are joined with ", " after dropping blank
items, and any other value is str().
"""

from __future__ import annotations

from qgis_sdk.metadata import MetadataField, metadata_fields, render_metadata_from_dict


def test_field_table_keeps_the_rust_order_and_keys():
    fields = metadata_fields()

    assert all(isinstance(field, MetadataField) for field in fields)
    assert [(field.attr, field.key) for field in fields][:3] == [
        ("name", "name"),
        ("qgis_min_version", "qgisMinimumVersion"),
        ("qgis_max_version", "qgisMaximumVersion"),
    ]
    assert len(fields) == 20
    assert ("has_processing_provider", "hasProcessingProvider") in [(f.attr, f.key) for f in fields]


def test_renders_fields_in_table_order_under_the_general_header():
    text = render_metadata_from_dict(
        {"experimental": True, "version": "1.0", "name": "Demo", "tags": ["a", "b"]}
    )

    assert text == "[general]\nname=Demo\nversion=1.0\nexperimental=True\ntags=a, b\n"


def test_an_empty_mapping_renders_only_the_header():
    assert render_metadata_from_dict({}) == "[general]\n"


def test_none_and_blank_values_are_skipped():
    text = render_metadata_from_dict({"name": "  ", "description": None, "tags": ["", "  "]})

    assert text == "[general]\n"


def test_strings_are_trimmed():
    assert render_metadata_from_dict({"name": "  Demo  "}) == "[general]\nname=Demo\n"


def test_blank_list_items_are_dropped_but_others_are_kept_as_written():
    text = render_metadata_from_dict({"tags": ["  gis ", "", "plugin"]})

    assert text == "[general]\ntags=  gis , plugin\n"


def test_other_values_are_written_with_str():
    text = render_metadata_from_dict({"qgis_min_version": 3.44, "server": False})

    assert text == "[general]\nqgisMinimumVersion=3.44\nserver=False\n"


def test_the_snake_case_key_maps_to_the_camel_case_metadata_key():
    text = render_metadata_from_dict({"has_processing_provider": True})

    assert text == "[general]\nhasProcessingProvider=True\n"


def test_unknown_keys_are_ignored():
    assert render_metadata_from_dict({"not_a_field": "x"}) == "[general]\n"
