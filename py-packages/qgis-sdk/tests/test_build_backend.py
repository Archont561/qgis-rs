"""qgis-sdk builds with setuptools. Maturin and the `_core` extension are gone.

These are static checks on the packaging config, so they run in the pure suite
without building a wheel. The real build is exercised by the gates.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_build_backend_is_setuptools():
    build = _pyproject()["build-system"]

    assert build["build-backend"] == "setuptools.build_meta"
    assert any(req.startswith("setuptools") for req in build["requires"])


def test_maturin_is_not_a_build_or_dev_dependency():
    data = _pyproject()
    requires = data["build-system"]["requires"]
    dev = data["project"]["optional-dependencies"]["dev"]

    assert not any("maturin" in req for req in requires)
    assert not any("maturin" in req for req in dev)
    assert "maturin" not in data.get("tool", {})


def test_package_data_ships_the_bridge_assets():
    package_data = _pyproject()["tool"]["setuptools"]["package-data"]

    assert "assets/bridge/*" in package_data["qgis_sdk"]
    assert (ROOT / "src" / "qgis_sdk" / "assets" / "bridge" / "qgis-sdk.js").is_file()


def test_packages_are_found_under_src():
    setuptools = _pyproject()["tool"]["setuptools"]

    assert setuptools["package-dir"] == {"": "src"}
    assert setuptools["packages"]["find"]["where"] == ["src"]


def test_package_json_build_does_not_compile_or_import_a_native_core():
    scripts = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["scripts"]

    assert "maturin" not in scripts["build"]
    assert "_core" not in scripts["build"]
    assert "cargo" not in scripts["build"]
