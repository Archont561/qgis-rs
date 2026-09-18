"""Tests for qgis_sdk CLI — Rust-native when built, Python fallback otherwise."""

from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path

def test_cli_import():
    from qgis_sdk.cli import build_parser, main
    parser = build_parser()
    assert parser is not None

def test_cli_version(capsys):
    from qgis_sdk.cli import main
    rc = main(["version"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "qgis-plugin" in out

def test_cli_new_and_validate(tmp_path, capsys):
    from qgis_sdk.cli import main

    # Scaffold new plugin
    rc = main(["new", "my_test_plugin", "--type", "general", "-o", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Created plugin" in out or "my_test_plugin" in out

    plugin_dir = tmp_path / "my_test_plugin"
    assert plugin_dir.exists()
    assert (plugin_dir / "metadata.txt").exists()
    assert (plugin_dir / "my_test_plugin" / "__init__.py").exists()

    # Validate
    rc = main(["validate", str(plugin_dir)])
    assert rc == 0

    # Info
    rc = main(["info", str(plugin_dir)])
    assert rc == 0

    # Info JSON
    rc = main(["info", str(plugin_dir), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    # Last output should be JSON
    # Find JSON part
    lines = out.strip().splitlines()
    json_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            json_start = i
            break
    if json_start is not None:
        json_text = "\n".join(lines[json_start:])
        data = json.loads(json_text)
        assert "name" in data or "qgisMinimumVersion" in data or "my_test_plugin" in str(data)

def test_cli_new_with_rust(tmp_path, capsys):
    from qgis_sdk.cli import main
    rc = main(["new", "my_rust_plugin", "--rust", "-o", str(tmp_path)])
    assert rc == 0
    plugin_dir = tmp_path / "my_rust_plugin"
    assert (plugin_dir / "Cargo.toml").exists()
    assert (plugin_dir / "src" / "lib.rs").exists()

def test_cli_build_and_package(tmp_path, capsys):
    from qgis_sdk.cli import main
    # Create minimal plugin dir
    plugin_dir = tmp_path / "test_pkg"
    plugin_dir.mkdir()
    (plugin_dir / "metadata.txt").write_text("[general]\nname=test_pkg\nversion=0.1.0\n")

    # Need to chdir to plugin dir for build/package that uses current dir
    orig = Path.cwd()
    try:
        import os
        os.chdir(plugin_dir)
        rc = main(["build", "-o", "dist"])
        assert rc == 0

        rc = main(["package", "-o", "dist"])
        assert rc == 0
        assert (plugin_dir / "dist").exists()
    finally:
        os.chdir(orig)

def test_cli_rust_init(tmp_path, capsys):
    from qgis_sdk.cli import main
    plugin_dir = tmp_path / "rust_init_test"
    plugin_dir.mkdir()

    rc = main(["rust", "init", str(plugin_dir)])
    assert rc == 0
    assert (plugin_dir / "Cargo.toml").exists()

def test_cli_binary_exists():
    """If maturin built the binary, qgis-plugin should be invocable."""
    result = subprocess.run(
        [sys.executable, "-m", "qgis_sdk.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "qgis-plugin" in result.stdout or "QGIS plugin SDK" in result.stdout

def test_has_rust_flag():
    import qgis_sdk
    # Should have HAS_RUST attribute now
    assert hasattr(qgis_sdk, "HAS_RUST")
    assert hasattr(qgis_sdk, "__version__")
