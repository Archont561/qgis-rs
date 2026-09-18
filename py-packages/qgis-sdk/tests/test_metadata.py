"""metadata.txt generation, with no QGIS involved."""

from __future__ import annotations

from qgis_sdk import Plugin, render_metadata
from qgis_sdk.metadata import as_mapping, write_metadata


class Transit(Plugin):
    name = "Transit Tools"
    version = "1.2.3"
    description = "Tools for transit networks"
    about = "Buffers stops and measures headways."
    author = "A. Cartographer"
    email = "a@example.org"
    category = "Vector"
    tags = ("transit", "vector")
    qgis_min_version = "3.34"
    experimental = True


def test_metadata_starts_with_general_section():
    assert render_metadata(Transit).splitlines()[0] == "[general]"


def test_metadata_contains_declared_fields():
    text = render_metadata(Transit)
    assert "name=Transit Tools" in text
    assert "version=1.2.3" in text
    assert "qgisMinimumVersion=3.34" in text
    assert "email=a@example.org" in text


def test_tags_are_joined_with_commas():
    assert "tags=transit, vector" in render_metadata(Transit)


def test_booleans_render_as_python_literals():
    assert "experimental=True" in render_metadata(Transit)
    assert "deprecated=False" in render_metadata(Transit)


def test_unset_fields_are_omitted():
    text = render_metadata(Transit)
    assert "homepage=" not in text
    assert "repository=" not in text
    assert "tracker=" not in text


def test_field_order_matches_qgis_expectations():
    keys = list(as_mapping(Transit))
    assert keys.index("name") < keys.index("qgisMinimumVersion") < keys.index("version")


def test_write_metadata_creates_file(tmp_path):
    path = write_metadata(Transit, tmp_path)
    assert path.endswith("metadata.txt")
    written = (tmp_path / "metadata.txt").read_text(encoding="utf-8")
    assert written == render_metadata(Transit)


def test_base_plugin_still_renders():
    text = render_metadata(Plugin)
    assert text.startswith("[general]\n")
    assert "version=0.0.0" in text
