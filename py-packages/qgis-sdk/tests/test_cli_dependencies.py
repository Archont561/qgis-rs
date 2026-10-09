"""The qgis-sdk CLI runtime is typer and questionary, declared in both manifests.

pyproject.toml is what a wheel installs. pixi.toml is what the development
environment carries, so `pixi run` tasks can call the CLI without an install.
The two must name the same packages (D15 §5).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CLI_DEPENDENCIES = ("typer", "questionary")


def _project_dependencies() -> list[str]:
    data = tomllib.loads((REPO / "py-packages/qgis-sdk/pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["dependencies"]


def _pixi_pypi_dependencies() -> dict:
    data = tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))
    return data["feature"]["py-runtime"]["pypi-dependencies"]


def _name(requirement: str) -> str:
    for sep in ("<", ">", "=", "~", "!", "[", " ", ";"):
        requirement = requirement.split(sep)[0]
    return requirement.strip()


def test_wheel_requires_typer_and_questionary():
    names = {_name(req) for req in _project_dependencies()}

    assert set(CLI_DEPENDENCIES) <= names


def test_pixi_environment_carries_typer_and_questionary():
    pypi = _pixi_pypi_dependencies()

    for name in CLI_DEPENDENCIES:
        assert name in pypi, pypi
