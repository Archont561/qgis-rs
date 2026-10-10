"""`qgis-sdk version` reports the package version and the UI surfaces.

Pinned at the public CLI seam (`qgis_sdk.cli.main`). The retired Rust command
printed `qgis-sdk <version> (Rust-native, from qgis-sdk)` and then a fixed UI
line. The version line now drops the "Rust-native" label, because no Rust code
remains in this package. Everything else is unchanged.
"""

from __future__ import annotations

import qgis_sdk
from qgis_sdk import cli

UI_LINE = (
    "  UI: dialogs (.ui + uic.loadUiType) + WebEngine "
    "(QWebChannel, qrc:///qtwebchannel/qwebchannel.js)"
)


def test_version_prints_the_package_version_then_the_ui_line(capsys):
    code = cli.main(["version"])
    lines = capsys.readouterr().out.splitlines()

    assert code == 0
    assert lines[0] == f"qgis-sdk {qgis_sdk.__version__} (Python, from qgis-sdk)"
    assert lines[1] == UI_LINE


def test_version_does_not_claim_a_rust_core(capsys):
    cli.main(["version"])

    assert "Rust" not in capsys.readouterr().out


def test_version_is_a_real_version_string():
    parts = qgis_sdk.__version__.split(".")

    assert len(parts) >= 2
    assert all(part[:1].isdigit() for part in parts[:2])
