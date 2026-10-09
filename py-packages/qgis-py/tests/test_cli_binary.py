"""The qgis-cli console script runs the prebuilt Rust binary shipped in the wheel."""

import sys
from pathlib import Path

import pytest

from qgis_py import cli

PKG = Path(__file__).resolve().parents[1]

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="the fixture is a POSIX shell script")


def _fake_binary(directory: Path, body: str) -> Path:
    exe = directory / "qgis-cli"
    exe.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    exe.chmod(0o755)
    return exe


@posix_only
def test_binary_main_returns_the_binary_status_and_forwards_argv(tmp_path, monkeypatch, capfd):
    monkeypatch.setattr(cli, "BUNDLED_BIN_DIR", tmp_path)
    _fake_binary(tmp_path, 'echo "argv: $*"; exit 7')

    assert cli.binary_main(["info", "project.qgz"]) == 7
    assert "argv: info project.qgz" in capfd.readouterr().out


@posix_only
def test_binary_main_reports_a_missing_binary_as_a_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "BUNDLED_BIN_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        cli.cli_binary_path()
    assert cli.binary_main(["info"]) != 0


def test_qgis_cli_console_script_points_at_the_binary_shim():
    text = (PKG / "pyproject.toml").read_text(encoding="utf-8")

    assert 'qgis-cli = "qgis_py.cli:binary_main"' in text
    assert 'qgis-py = "qgis_py.cli:main"' in text
