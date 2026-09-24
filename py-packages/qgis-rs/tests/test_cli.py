"""Python CLI integration tests backed by the qgis-rs Rust extension."""

import json
import subprocess
import sys
from pathlib import Path

def test_cli_import():
    from qgis_rs.cli import build_parser, main
    parser = build_parser()
    assert parser is not None

def test_cli_info(tmp_path, capsys):
    from qgis_rs.cli import main
    p = tmp_path / "map.qgs"
    p.write_text("<qgis></qgis>")

    rc = main(["info", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "path:" in out
    assert "format:" in out

def test_cli_info_json(tmp_path, capsys):
    from qgis_rs.cli import main
    p = tmp_path / "map.qgs"
    p.write_text("<qgis></qgis>")

    rc = main(["info", str(p), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["format"] == "qgs"
    assert "size_bytes" in data

def test_cli_tiles_dry_run(tmp_path, capsys):
    from qgis_rs.cli import main
    p = tmp_path / "map.qgs"
    p.write_text("<qgis></qgis>")

    rc = main([
        "tiles", str(p),
        "-z", "10-14",
        "-b", "14,50,15,51",
        "-o", str(tmp_path / "tiles"),
        "--dry-run"
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Would render 4568 tiles" in out
    assert "z=10" in out

def test_cli_version(capsys):
    from qgis_rs.cli import main
    rc = main(["version"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "qgis-rs" in out

def test_cli_module_entrypoint_displays_help():
    """The installed Python entrypoint should expose the CLI help."""
    result = subprocess.run(
        [sys.executable, "-m", "qgis_rs.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "qgis-cli" in result.stdout or "Render, tile" in result.stdout
