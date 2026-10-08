"""What a test run says about the runtime it ran on.

The header is the only place a CI log states which QGIS backed the run. Two
things must hold for it to be worth reading: the release it prints is the one
QGIS reports (not a constant the bindings do not export, which used to make the
field silently ``None``), and the line names the backend and the layers, so a
pure-Python fallback can never be mistaken for a QGIS run.
"""

from __future__ import annotations

import sys
import types

import pytest

from qgis_sdk.testing import detect_qgis_environment, pytest_report_header


def _fake_qgis_core(**attributes):
    """A stand-in for ``qgis.core``, so the detector can be tested without QGIS."""
    core = types.ModuleType("qgis.core")
    for name, value in attributes.items():
        setattr(core, name, value)
    return core


def test_the_release_is_read_from_qgis_version(monkeypatch) -> None:
    class Qgis:
        @staticmethod
        def version() -> str:
            return "3.44.14-Solothurn"

    monkeypatch.setitem(sys.modules, "qgis.core", _fake_qgis_core(Qgis=Qgis))

    environment = detect_qgis_environment()

    assert environment.qgis_available
    assert environment.qgis_version == "3.44.14-Solothurn"


def test_a_legacy_version_constant_is_still_honoured(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules, "qgis.core", _fake_qgis_core(QGIS_VERSION="3.34.0-Prizren")
    )

    assert detect_qgis_environment().qgis_version == "3.34.0-Prizren"


def test_a_runtime_that_reports_no_version_says_so(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "qgis.core", _fake_qgis_core())

    environment = detect_qgis_environment()

    assert environment.qgis_available
    assert environment.qgis_version is None


def test_the_header_names_backend_version_layers_and_gate() -> None:
    class Config:
        stash: dict = {}

    header = pytest_report_header(Config())

    environment = detect_qgis_environment()
    assert header.startswith("qgis-sdk runtime: backend=")
    assert f"backend={environment.backend}" in header
    assert f"qgis={environment.qgis_version or 'unavailable'}" in header
    assert "layers: " in header
    assert "gate: all (skips allowed)" in header


@pytest.mark.qgis
def test_the_detector_reports_the_running_qgis_release(qgis_environment) -> None:
    qgis_environment.require_qgis()
    from qgis.core import Qgis

    assert qgis_environment.qgis_version == Qgis.version()
    assert qgis_environment.qgis_version[0].isdigit(), qgis_environment.qgis_version
