"""qgis-sdk is pure Python. No native extension and no Rust flags remain.

The Rust core (`qgis_sdk._core`) and its pure-Python stand-in
(`qgis_sdk._fallback_cli`) are retired together with `crates/qgis-sdk`. These
tests pin that at the public import surface, so a stale build artifact or a
re-added fallback cannot quietly change which code path runs.
"""

from __future__ import annotations

import importlib.util

import pytest

import qgis_sdk

RETIRED_MODULES = ["qgis_sdk._core", "qgis_sdk._fallback_cli"]
RETIRED_NAMES = ["HAS_RUST", "RUST_VERSION"]


@pytest.mark.parametrize("module_name", RETIRED_MODULES)
def test_retired_native_module_is_not_importable(module_name):
    assert importlib.util.find_spec(module_name) is None


@pytest.mark.parametrize("name", RETIRED_NAMES)
def test_package_does_not_expose_rust_flags(name):
    assert not hasattr(qgis_sdk, name)
    assert name not in qgis_sdk.__all__


def test_styles_does_not_expose_rust_flag():
    from qgis_sdk import styles

    assert not hasattr(styles, "HAS_RUST")
    assert "HAS_RUST" not in styles.__all__
