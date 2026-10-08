"""Subprocess-backed integration test for a real QGIS runtime.

The subprocess mirrors the binary-crate fixture pattern: native QGIS startup and
shutdown are isolated from pytest, while the fixture plugin is committed and
imported like a small downstream plugin would be.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qgis_subprocess import run_in_subprocess, tree_digest


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "simple_plugin"


@pytest.mark.qgis
def test_simple_plugin_loads_calls_action_and_registers_algorithm(qgis_environment):
    """Load the fixture plugin in a QGIS process and exercise its public surface."""
    qgis_environment.require_qgis()

    script = r'''
from pathlib import Path
from tempfile import TemporaryDirectory

from PyQt5.QtWidgets import QApplication
from qgis.core import QgsApplication, QgsProcessingContext, QgsProcessingFeedback

from simple_plugin import SimplePlugin


class FixtureAction:
    def __init__(self, callback):
        self._callback = callback

    def trigger(self):
        self._callback()


class FixtureIface:
    def __init__(self):
        self.messages = []
        self.toolbar_icons = []

    def addToolBarIcon(self, action):
        self.toolbar_icons.append(action)

    def removeToolBarIcon(self, action):
        self.toolbar_icons.remove(action)

    def addPluginToMenu(self, path, action):
        pass

    def removePluginMenu(self, path, action):
        pass


qt_app = QApplication.instance() or QApplication([])
qgis_app = QgsApplication([], False)
qgis_app.initQgis()

try:
    SimplePlugin.action_factory = staticmethod(lambda spec, callback: FixtureAction(callback))
    iface = FixtureIface()
    plugin = SimplePlugin(iface)
    plugin.init_gui()

    assert len(iface.toolbar_icons) == 1
    iface.toolbar_icons[0].trigger()
    assert plugin.calls == 1
    assert iface.messages == ["fixture action called"]

    processing = QgsApplication.processingRegistry()
    provider = processing.providerById("fixture")
    assert provider is not None
    algorithm = processing.algorithmById("fixture:echo")
    assert algorithm is not None
    assert algorithm.name() == "echo"

    with TemporaryDirectory() as directory:
        destination = str(Path(directory) / "echo.txt")
        result = algorithm.processAlgorithm(
            {"value": 7, "result": destination},
            QgsProcessingContext(),
            QgsProcessingFeedback(),
        )
        assert result["result"] == destination
        assert Path(destination).read_text(encoding="utf-8") == "7"

    plugin.unload()
    assert processing.providerById("fixture") is None
finally:
    qgis_app.exitQgis()
'''

    before = tree_digest(FIXTURE_DIR)
    run = run_in_subprocess(script, cwd=FIXTURE_DIR, pythonpath=[FIXTURE_DIR])
    assert run.succeeded, run.diagnostics(qgis_version=qgis_environment.qgis_version)

    # The fixture is committed, read-only input: the subprocess imports it and
    # writes only into its own temporary directory.
    assert tree_digest(FIXTURE_DIR) == before, "the simple_plugin fixture was modified"
