"""Session-wide Qt setup for the qgis-sdk test suite.

The suite is written to pass whether or not PyQt/QGIS are importable, because CI
runs it in a bare virtualenv that has neither: everything in qgis_sdk degrades
to a pure-Python fallback and the tests assert that surface. That made the suite
environment-dependent in the other direction — run it inside a QGIS-bearing Pixi
environment and two code paths that CI never reaches abort the interpreter:

  * qgis_sdk.ui builds real QWidgets, and Qt aborts ("must construct a
    QApplication before a QWidget") when no QApplication exists;
  * qgis_sdk.network calls QgsNetworkAccessManager.instance(), a QGIS singleton
    that segfaults unless a QgsApplication has been constructed.

So the application object is created here, once per session, and only when the
binding is actually importable. In CI's bare virtualenv neither exists and this
file does nothing.
"""

from __future__ import annotations

import os
from typing import Any, Iterator

import pytest

# qgis_sdk.ui reads this; set it before any binding is imported so the platform
# plugin is chosen while the interpreter is still single-threaded.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qt_app() -> Iterator[Any]:
    """A QApplication for the session, or skip when PyQt is not installed."""
    try:
        from PyQt5.QtWidgets import QApplication
    except ImportError:  # pragma: no cover - depends on the environment
        pytest.skip("PyQt5 is not installed in this environment")

    app = QApplication.instance() or QApplication([])
    yield app
