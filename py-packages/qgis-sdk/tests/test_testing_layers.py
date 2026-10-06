"""The facade and the four execution layers.

Two promises are checked here, and they are the ones a refactor breaks
quietly. **AC#1**: every name and every fixture that existed before the split
is still reachable through ``qgis_sdk.testing``. **AC#7**: a pure test
initialises neither Qt nor QGIS, and a test that needs a layer this process
cannot reach is skipped with a reason rather than handed a fake.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import qgis_sdk.testing as testing
from qgis_sdk.testing import detect_qgis_environment

#: The surface `qgis_sdk/testing.py` exported before TASK-32 split it up.
#: Frozen here on purpose: a name that disappears from the facade has to fail
#: this list, not somebody's plugin suite a release later.
LEGACY_EXPORTS = (
    "FakeLayersAPI",
    "FakeProjectAPI",
    "FakeMessageAPI",
    "FakeTasksAPI",
    "FakeNetworkAPI",
    "FakeIfaceAPI",
    "FakeSettingsAPI",
    "FakeProcessingAPI",
    "FakeQgisAPI",
    "fake_qgis_api_factory",
    "FakeAction",
    "FakeIface",
    "FakeContext",
    "FakeSink",
    "FakeFeature",
    "FakeGeometry",
    "FakeFields",
    "FakeDialog",
    "FakeDialogWidget",
    "FakeWebView",
    "FakeWebPage",
    "FakeWebChannel",
    "FakeBridge",
    "FakeNetworkResponse",
    "FakeNetworkManager",
    "FakeSession",
    "FakeContentFetcher",
    "FakeTask",
    "FakeAsyncResult",
    "FakeSignature",
    "FakeTaskWrapper",
    "FakeTaskManager",
    "fake_action_factory",
    "fake_dialog_factory",
    "fake_webview_factory",
    "fake_bridge_factory",
    "fake_network_manager_factory",
    "fake_network_response_factory",
    "fake_content_fetcher_factory",
    "fake_session_factory",
    "fake_task_manager_factory",
    "fake_task_factory",
    "QgisTestEnvironment",
    "detect_qgis_environment",
    "mock_features",
    "mock_source",
    "mock_context",
    "pytest_configure",
)

#: Fixture names plugin suites already use. The entry point advertises them,
#: so they are API as much as any class is.
LEGACY_FIXTURES = (
    "qgis_environment",
    "qgis_available",
    "pure_python",
    "qt_app",
    "qgis_app",
    "fake_iface",
    "fake_action_factory",
    "fake_context",
    "fake_dialog",
    "fake_dialog_factory",
    "fake_webview",
    "fake_webview_factory",
    "fake_bridge",
    "mock_features",
    "mock_source",
    "mock_context",
    "mock_features_fixture",
    "mock_source_fixture",
    "mock_context_fixture",
    "fake_network_response",
    "fake_network_manager",
    "fake_content_fetcher",
    "fake_session",
    "fake_task",
    "fake_task_manager",
    "fake_async_result",
    "fake_task_wrapper",
    "fake_qgis_api",
    "fake_layers_api",
    "fake_project_api",
    "fake_message_api",
    "fake_tasks_api",
    "fake_network_api",
)

NEW_FIXTURES = (
    "shared_calls",
    "fake_network_transport",
    "manual_task_manager",
    "bridge_harness_factory",
    "webengine_app",
)


@pytest.mark.parametrize("name", LEGACY_EXPORTS)
def test_every_legacy_export_still_resolves(name: str) -> None:
    assert hasattr(testing, name), f"{name} disappeared from the qgis_sdk.testing facade"


@pytest.mark.parametrize("name", LEGACY_FIXTURES + NEW_FIXTURES)
def test_every_fixture_is_registered_under_its_public_name(name: str, request) -> None:
    """Asked of pytest itself, not of the module: a fixture that is importable
    but not registered is the exact failure a facade split causes."""
    assert name in request._fixturemanager._arg2fixturedefs, f"{name} is not a fixture"


def test_the_package_is_still_a_pytest_plugin_module() -> None:
    assert callable(testing.pytest_configure)
    assert callable(testing.pytest_collection_modifyitems)
    assert "qgis" in testing.MARKERS and "webengine" in testing.MARKERS


def test_no_fixture_module_reaches_for_a_binding_at_import_time() -> None:
    """AC#7, read off the source rather than off a lucky process.

    ``import qgis_sdk`` itself pulls in the Qt funnel and the PyQGIS runtime
    probe, so "did Qt end up in sys.modules" cannot answer this question. What
    can: no module under ``qgis_sdk/testing/`` names a binding at module
    scope. ``detect_qgis_environment`` imports inside the function, where a
    pure test never reaches it, and ``strategies`` is the one module allowed
    its own test-only dependency.
    """
    package = Path(testing.__file__).parent
    offenders: dict[str, list[str]] = {}

    for module in sorted(package.glob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        named = []
        for node in tree.body:  # module scope only — function-level is fine
            if isinstance(node, ast.Import):
                named += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                named.append(node.module)
        forbidden = [
            name
            for name in named
            if name.split(".")[0] in {"PyQt5", "PyQt6", "PySide6", "qgis"}
            or (name.split(".")[0] == "hypothesis" and module.name != "strategies.py")
        ]
        if forbidden:
            offenders[module.name] = forbidden

    assert offenders == {}


def test_importing_the_fakes_constructs_no_application() -> None:
    """Importing is not initialising: neither application singleton exists.

    Checked in a fresh interpreter, because this suite's own ``conftest.py``
    deliberately builds a QApplication when PyQt is installed.
    """
    probe = (
        "import qgis_sdk.testing\n"
        "from qgis_sdk.testing import detect_qgis_environment\n"
        "environment = detect_qgis_environment()\n"
        "qt = qgis = None\n"
        "if environment.qt_available:\n"
        "    from PyQt5.QtWidgets import QApplication\n"
        "    qt = QApplication.instance()\n"
        "if environment.qgis_available:\n"
        "    from qgis.core import QgsApplication\n"
        "    qgis = QgsApplication.instance()\n"
        "print(qt is None, qgis is None)\n"
    )
    finished = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )

    no_qt_app, no_qgis_app = finished.stdout.split()
    assert no_qt_app == "True", "importing the fakes must not construct a QApplication"
    assert no_qgis_app == "True", "importing the fakes must not construct a QgsApplication"


def test_detection_reports_the_layers_this_process_can_reach() -> None:
    environment = detect_qgis_environment()

    assert "pure" in environment.layers
    assert environment.supports("qgis") is environment.qgis_available
    assert environment.supports("qt") is environment.qt_available
    assert environment.supports("webengine") is environment.webengine_available
    assert environment.layers <= {"pure", "qt", "qgis", "webengine"}


def test_a_missing_layer_is_a_skip_with_a_reason_not_a_fake() -> None:
    """``require_*`` raises pytest's own Skipped, carrying the prerequisite.

    Caught as ``pytest.skip.Exception`` rather than ``Exception``: ``Skipped``
    derives from ``BaseException``, so a ``pytest.raises(Exception)`` here
    would let the skip escape and mark *this* test skipped — a green that
    asserted nothing, which is the failure mode AC#7 is about.
    """
    absent = type(detect_qgis_environment())(
        qgis_available=False,
        qt_available=False,
        qgis_application_available=False,
        webengine_available=False,
    )

    for require, reason in (
        (absent.require_qgis, "qgis.core"),
        (absent.require_qt, "PyQt5"),
        (absent.require_webengine, "QtWebEngineWidgets"),
    ):
        with pytest.raises(pytest.skip.Exception) as skipped:
            require()
        assert reason in str(skipped.value)


def test_a_present_layer_does_not_skip() -> None:
    present = type(detect_qgis_environment())(
        qgis_available=True,
        qt_available=True,
        qgis_application_available=True,
        webengine_available=True,
    )

    present.require_qgis()
    present.require_qt()
    present.require_webengine()


class _Item:
    """The two methods ``pytest_collection_modifyitems`` uses on an item."""

    def __init__(self, *markers: str):
        self.markers = set(markers)
        self.added: list = []

    def get_closest_marker(self, name: str):
        return SimpleNamespace(name=name) if name in self.markers else None

    def add_marker(self, marker) -> None:
        self.added.append(marker)


def test_marked_tests_are_skipped_before_their_bodies_run() -> None:
    """Collection-time, not call-time: a QGIS test whose body starts running
    in a pure process has already imported what it was supposed to skip."""
    environment = detect_qgis_environment()
    items = {name: _Item(name) for name in ("qgis", "qt", "webengine", "pure_python")}
    plain = _Item()

    testing.pytest_collection_modifyitems(None, [*items.values(), plain])

    for layer in ("qgis", "qt", "webengine"):
        skipped = bool(items[layer].added)
        assert skipped is not environment.supports(layer), (
            f"a {layer} test must be skipped exactly when {layer} is unreachable"
        )
        if skipped:
            assert items[layer].added[0].kwargs["reason"]
    assert bool(items["pure_python"].added) is not environment.pure_python
    assert plain.added == [], "an unmarked test is never touched"
