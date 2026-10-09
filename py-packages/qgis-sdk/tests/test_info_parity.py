"""`qgis-sdk info` behaves as the retired Rust `cmd_info` did.

Pinned at the public CLI seam (`qgis_sdk.cli.main`). The Rust binary is the
reference: there was one Rust implementation of `info`, and it is what the
Python port replaces.

* the metadata file is `metadata.txt` at the root, else `src/metadata.txt`;
* plain output prints a header and the file content verbatim;
* `--json` prints sorted keys (serde_json's default map), skipping section
  headers and blank lines, splitting each line on the first `=`, and keeping
  non-ASCII characters unescaped;
* a missing metadata file is reported on stdout with exit status 0.
"""

from __future__ import annotations

import json
from pathlib import Path

from qgis_sdk import cli


def _run(argv, capsys) -> tuple[int, str, str]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_plain_output_prints_header_and_content(tmp_path, capsys):
    metadata = tmp_path / "metadata.txt"
    metadata.write_text("[general]\nname=demo\nversion=0.1.0\n", encoding="utf-8")

    code, out, _err = _run(["info", str(tmp_path)], capsys)

    assert code == 0
    assert out.splitlines()[0] == f"Plugin info from {metadata}:"
    assert "name=demo" in out
    assert "version=0.1.0" in out


def test_src_metadata_is_used_when_root_has_none(tmp_path, capsys):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "metadata.txt").write_text("[general]\nname=nested\n", encoding="utf-8")

    code, out, _err = _run(["info", str(tmp_path)], capsys)

    assert code == 0
    assert "name=nested" in out


def test_json_keys_are_sorted_like_the_rust_map(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text(
        "[general]\nname=demo\nversion=0.1.0\nauthor=Ada\n", encoding="utf-8"
    )

    code, out, _err = _run(["info", str(tmp_path), "--json"], capsys)

    assert code == 0
    assert list(json.loads(out)) == ["author", "name", "version"]


def test_json_skips_sections_and_blank_lines_and_splits_on_first_equals(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text(
        "[general]\n\nname=demo\ndescription=a=b\n", encoding="utf-8"
    )

    code, out, _err = _run(["info", str(tmp_path), "--json"], capsys)

    assert code == 0
    assert json.loads(out) == {"description": "a=b", "name": "demo"}


def test_json_keeps_non_ascii_unescaped(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text("[general]\nname=Zażółć\n", encoding="utf-8")

    code, out, _err = _run(["info", str(tmp_path), "--json"], capsys)

    assert code == 0
    assert "Zażółć" in out
    assert "\\u" not in out


def test_missing_metadata_is_reported_on_stdout_with_exit_zero(tmp_path, capsys):
    code, out, err = _run(["info", str(tmp_path)], capsys)

    assert code == 0
    assert err == ""
    assert f"No metadata.txt found in {tmp_path}" in out
    assert "This might be a qgis-sdk Plugin class" in out
    assert "  print(MyPlugin.metadata_txt())" in out


def test_info_defaults_to_the_current_directory(tmp_path, capsys, monkeypatch):
    (tmp_path / "metadata.txt").write_text("[general]\nname=here\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    code, out, _err = _run(["info"], capsys)

    assert code == 0
    assert "name=here" in out


def test_path_is_a_directory_not_required_to_exist_for_missing_message(tmp_path, capsys):
    missing = Path(tmp_path) / "nowhere"

    code, out, _err = _run(["info", str(missing)], capsys)

    assert code == 0
    assert f"No metadata.txt found in {missing}" in out
