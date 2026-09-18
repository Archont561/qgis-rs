"""Import-resolution helpers — these describe where PyQGIS has to come from."""

from __future__ import annotations

import os

from qgis_sdk import PyQgisImportError, expected_pythonpath
from qgis_sdk.runtime import require_qgis


def test_expected_pythonpath_uses_qgis_prefix_path(monkeypatch):
    monkeypatch.setenv("QGIS_PREFIX_PATH", "/opt/qgis")
    monkeypatch.setenv("CONDA_PREFIX", "/should/not/be/used")

    assert expected_pythonpath() == [
        os.path.join("/opt/qgis", "share/qgis/python"),
        os.path.join("/opt/qgis", "share/qgis/python/plugins"),
    ]


def test_expected_pythonpath_falls_back_to_conda_prefix(monkeypatch):
    monkeypatch.delenv("QGIS_PREFIX_PATH", raising=False)
    monkeypatch.setenv("CONDA_PREFIX", "/env/prefix")

    paths = expected_pythonpath()
    assert paths[0].endswith(os.path.join("share", "qgis", "python"))
    assert paths[1].endswith(os.path.join("share", "qgis", "python", "plugins"))


def test_expected_pythonpath_is_empty_without_a_prefix(monkeypatch):
    monkeypatch.delenv("QGIS_PREFIX_PATH", raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)

    assert expected_pythonpath() == []


def test_require_qgis_explains_how_to_fix_a_missing_binding(monkeypatch):
    monkeypatch.setenv("QGIS_PREFIX_PATH", "/opt/qgis")
    monkeypatch.setenv("CONDA_PREFIX", "/opt/qgis")

    try:
        import qgis.core  # noqa: F401
    except ImportError:
        pass
    else:  # pragma: no cover - only when QGIS really is installed
        return

    try:
        require_qgis()
    except PyQgisImportError as exc:
        message = str(exc)
        assert "pixi run -e sdk" in message
        assert "share/qgis/python" in message
        assert "PYTHONPATH" in message
    else:  # pragma: no cover
        raise AssertionError("require_qgis() should have raised without QGIS")
