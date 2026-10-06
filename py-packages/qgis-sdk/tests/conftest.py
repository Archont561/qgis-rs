"""Session-wide Qt setup for the qgis-sdk test suite.

The suite is written to pass whether or not PyQt/QGIS are importable, because
CI runs it in a bare virtualenv that has neither: everything in qgis_sdk
degrades to a pure-Python fallback and the tests assert that surface. That
made the suite environment-dependent in the other direction — run it inside a
QGIS-bearing Pixi environment and two code paths that CI never reaches abort
the interpreter:

  * qgis_sdk.ui builds real QWidgets, and Qt aborts ("must construct a
    QApplication before a QWidget") when no QApplication exists;
  * qgis_sdk.network calls QgsNetworkAccessManager.instance(), a QGIS singleton
    that segfaults unless a QgsApplication has been constructed.

``QT_QPA_PLATFORM`` is therefore pinned here, before any binding is imported.
The ``qt_app`` fixture itself lives in ``qgis_sdk.testing.plugin`` and is *not*
redefined here: this file used to carry a second copy, which meant the suite
exercised a fixture no downstream plugin ever gets — the local one shadowed
the shipped one. One definition, used by this suite and by every plugin that
installs the SDK, is the only way the fixture is actually under test.
"""

from __future__ import annotations

import os

# qgis_sdk.ui reads this; set it before any binding is imported so the platform
# plugin is chosen while the interpreter is still single-threaded.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_configure(config):
    """Register the SDK plugin for source checkouts without double-loading it."""
    if config.pluginmanager.get_plugin("qgis_sdk") is None:
        import qgis_sdk.testing as sdk_testing

        config.pluginmanager.register(sdk_testing, "qgis_sdk")
        sdk_testing.pytest_configure(config)
