"""The wheel must not ship bytecode caches, whichever tree the build ran in."""

import tomllib
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def _excludes(pyproject: Path) -> list[str]:
    return tomllib.loads(pyproject.read_text(encoding="utf-8"))["tool"]["maturin"].get("exclude", [])


def test_maturin_excludes_bytecode_caches_from_the_wheel():
    patterns = _excludes(PKG / "pyproject.toml")

    assert "**/__pycache__/**" in patterns
    assert "**/*.pyc" in patterns
