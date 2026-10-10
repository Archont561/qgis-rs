"""The wheel must not ship bytecode caches, whichever tree the build ran in.

setuptools ships only the modules and the package data it is told about, so
caches stay out by construction. These checks pin that configuration: no
implicit inclusion of package data, and no pattern that could reach a cache.
"""

import tomllib
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def _setuptools_config():
    data = tomllib.loads((PKG / "pyproject.toml").read_text(encoding="utf-8"))
    return data["tool"]["setuptools"]


def test_package_data_is_not_implicitly_included():
    assert _setuptools_config().get("include-package-data", False) is False


def test_no_package_data_pattern_reaches_bytecode_caches():
    for patterns in _setuptools_config().get("package-data", {}).values():
        for pattern in patterns:
            assert "__pycache__" not in pattern
            assert not pattern.endswith(".pyc")
