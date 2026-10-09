"""`qgis-sdk validate` applies the union of the two retired Rust rule sets.

Pinned at the public CLI seam (`qgis_sdk.cli.main`):

* the path must exist;
* a plugin needs `metadata.txt` (at the root or under `src/`), or at least one
  `.py` file at the root;
* a metadata file must contain `[general]`, `name=` and `version=`
  (from the `qgis-sdk` crate);
* every `.html` file under `web/` (or `<name>/web/`) must reference qwebchannel
  (from `qgis-sdk-core`);
* on success it reports the UI and Web surfaces it found;
* on failure it exits non-zero and names each error.
"""

from __future__ import annotations

from pathlib import Path

from qgis_sdk import cli

VALID_METADATA = "[general]\nname=demo\nversion=0.1.0\n"


def _run(path: Path, capsys) -> tuple[int, str, str]:
    code = cli.main(["validate", str(path)])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_missing_path_is_an_error(tmp_path, capsys):
    code, _out, err = _run(tmp_path / "does-not-exist", capsys)

    assert code != 0
    assert "path does not exist" in err


def test_missing_metadata_and_no_python_is_an_error(tmp_path, capsys):
    code, _out, err = _run(tmp_path, capsys)

    assert code != 0
    assert "missing metadata.txt" in err


def test_valid_metadata_at_root_passes(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text(VALID_METADATA, encoding="utf-8")

    code, out, _err = _run(tmp_path, capsys)

    assert code == 0
    assert "Plugin structure looks valid" in out


def test_valid_metadata_under_src_passes(tmp_path, capsys):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "metadata.txt").write_text(VALID_METADATA, encoding="utf-8")

    code, out, _err = _run(tmp_path, capsys)

    assert code == 0
    assert "Plugin structure looks valid" in out


def test_a_python_file_stands_in_for_metadata_presence(tmp_path, capsys):
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")

    code, out, _err = _run(tmp_path, capsys)

    assert code == 0
    assert "Plugin structure looks valid" in out


def test_metadata_without_general_section_is_an_error(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text("name=demo\nversion=0.1.0\n", encoding="utf-8")

    code, _out, err = _run(tmp_path, capsys)

    assert code != 0
    assert "metadata.txt missing [general] section" in err


def test_metadata_without_name_is_an_error(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text("[general]\nversion=0.1.0\n", encoding="utf-8")

    code, _out, err = _run(tmp_path, capsys)

    assert code != 0
    assert "metadata.txt missing name" in err


def test_metadata_without_version_is_an_error(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text("[general]\nname=demo\n", encoding="utf-8")

    code, _out, err = _run(tmp_path, capsys)

    assert code != 0
    assert "metadata.txt missing version" in err


def test_web_html_without_qwebchannel_is_an_error(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text(VALID_METADATA, encoding="utf-8")
    web = tmp_path / "web"
    web.mkdir()
    page = web / "index.html"
    page.write_text("<html><body>no bridge</body></html>", encoding="utf-8")

    code, _out, err = _run(tmp_path, capsys)

    assert code != 0
    assert "missing qwebchannel.js reference" in err
    assert str(page) in err


def test_web_html_with_qwebchannel_is_reported_ready(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text(VALID_METADATA, encoding="utf-8")
    web = tmp_path / "web"
    web.mkdir()
    (web / "index.html").write_text(
        '<script src="qwebchannel.js"></script>', encoding="utf-8"
    )

    code, out, _err = _run(tmp_path, capsys)

    assert code == 0
    assert "Web: HTML files found, QWebChannel bridge ready" in out


def test_ui_directory_is_reported(tmp_path, capsys):
    (tmp_path / "metadata.txt").write_text(VALID_METADATA, encoding="utf-8")
    (tmp_path / "ui").mkdir()

    code, out, _err = _run(tmp_path, capsys)

    assert code == 0
    assert "UI: .ui files found" in out


def test_nested_package_directory_is_checked_too(tmp_path, capsys):
    """Both Rust rule sets also look in `<dirname>/web`, the `ui add-web` layout."""
    plugin = tmp_path / "my_plugin"
    plugin.mkdir()
    (plugin / "metadata.txt").write_text(VALID_METADATA, encoding="utf-8")
    nested_web = plugin / "my_plugin" / "web"
    nested_web.mkdir(parents=True)
    (nested_web / "index.html").write_text("<p>no bridge</p>", encoding="utf-8")

    code, _out, err = _run(plugin, capsys)

    assert code != 0
    assert "missing qwebchannel.js reference" in err


def test_validate_prints_the_path_it_checked(tmp_path, capsys):
    _code, out, _err = _run(tmp_path, capsys)

    assert f"Validating plugin in {tmp_path}" in out
