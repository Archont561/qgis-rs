"""qgis-py is a thin FFI API over the Rust engine. It ships no command-line interface."""

import importlib.util
import tomllib
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def test_pyproject_declares_no_console_scripts():
    project = tomllib.loads((PKG / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert "scripts" not in project
    assert "gui-scripts" not in project


def test_no_cli_module_or_bundled_binary_remains():
    assert importlib.util.find_spec("qgis_py.cli") is None
    assert not (PKG / "python" / "qgis_py" / "_bin").exists()
