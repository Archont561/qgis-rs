"""The pytest plugin: fixtures, markers, and the four execution layers.

Registered either by the ``pytest11`` entry point or by
``pytest_plugins = ["qgis_sdk.testing"]``; the fixtures are re-exported from
the package, so both spellings see the same objects.

The marker rules are the ones doc-5 makes non-negotiable: a test marked for a
layer this process cannot reach is **skipped before its body runs**, never
quietly handed a fake. ``pure_python`` is the inverse — a test that asserts
the no-QGIS fallback is skipped when QGIS *is* importable, because there the
fallback is not what runs.
"""

from __future__ import annotations

import os

from .bridge import BridgeHarness, FakeBridge
from .calls import CallLog
from .environment import detect_qgis_environment
from .iface import FakeIface, fake_action_factory
from .network import (
    FakeContentFetcher,
    FakeNetworkManager,
    FakeNetworkResponse,
    FakeNetworkTransport,
    FakeSession,
)
from .processing import FakeContext, mock_context, mock_features, mock_source
from .qgis_api import (
    FakeLayersAPI,
    FakeMessageAPI,
    FakeNetworkAPI,
    FakeProjectAPI,
    FakeQgisAPI,
    FakeTasksAPI,
)
from .tasks import FakeAsyncResult, FakeTask, FakeTaskManager, FakeTaskWrapper
from .ui import FakeDialog, FakeWebView, fake_dialog_factory, fake_webview_factory

#: The markers this plugin registers, and what each one needs to be true.
MARKERS = {
    "qgis": "mark test as requiring QGIS",
    "pure_python": "mark test as requiring no QGIS bindings",
    "qt": "mark test as requiring PyQt",
    "webengine": "mark test as requiring QWebEngine",
    "network": "mark test as requiring network",
    "tasks": "mark test as requiring QgsTaskManager",
}

try:
    import pytest
except ImportError:  # pragma: no cover - the SDK is importable without pytest
    pytest = None  # type: ignore[assignment]


def pytest_configure(config):
    """Register markers for qgis_sdk tests."""
    for name, description in MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {description}")


def pytest_collection_modifyitems(config, items):
    """Skip environment-specific tests before their bodies can touch QGIS."""
    import pytest as _pytest

    environment = detect_qgis_environment()
    skips = {
        "qgis": _pytest.mark.skip(reason="requires an importable qgis.core runtime"),
        "qt": _pytest.mark.skip(reason="requires an importable PyQt5 runtime"),
        "webengine": _pytest.mark.skip(reason="requires PyQt5.QtWebEngineWidgets"),
    }
    pure_python_skip = _pytest.mark.skip(
        reason="requires a pure-Python runtime without qgis.core"
    )
    for item in items:
        for layer, skip in skips.items():
            if item.get_closest_marker(layer) and not environment.supports(layer):
                item.add_marker(skip)
        if item.get_closest_marker("pure_python") and not environment.pure_python:
            item.add_marker(pure_python_skip)


if pytest is not None:

    # ── execution layers ────────────────────────────────────────────────────

    @pytest.fixture(scope="session")
    def qgis_environment():
        """Return the detected pure-Python/QGIS runtime for this test session."""
        return detect_qgis_environment()

    @pytest.fixture(scope="session")
    def qgis_available(qgis_environment):
        """Boolean fixture: whether ``qgis.core`` imports."""
        return qgis_environment.qgis_available

    @pytest.fixture(scope="session")
    def pure_python(qgis_environment):
        """Boolean fixture: whether tests run without PyQGIS."""
        return qgis_environment.pure_python

    @pytest.fixture(scope="session")
    def qt_app():
        """A QApplication, or a skip when Qt is unavailable.

        ``QT_QPA_PLATFORM`` is forced to ``offscreen`` before the binding is
        imported: a session that picks a platform plugin later picks the wrong
        one, and a headless runner then dies instead of skipping.
        """
        if not detect_qgis_environment().qt_available:
            pytest.skip("Qt is not installed in this environment")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        yield app

    @pytest.fixture(scope="session")
    def qgis_app(qgis_environment):
        """Return the host's live QgsApplication, or skip safely.

        A plain pytest process may import PyQGIS without being a QGIS host.
        This fixture intentionally does not construct or tear down a native
        ``QgsApplication``: some QGIS/Qt builds abort during pytest shutdown.
        Use it from a QGIS-hosted test runner, while pure-Python tests continue
        to use the SDK fakes and fallback implementations.
        """
        qgis_environment.require_qgis()
        from qgis.core import QgsApplication

        app = QgsApplication.instance()
        if app is None:
            pytest.skip("qgis.core is installed, but no QgsApplication is running")
        return app

    @pytest.fixture(scope="session")
    def webengine_app(qgis_environment, qt_app):
        """A QApplication with QtWebEngine imported, or a skip.

        WebEngine is its own layer: the import must happen before any
        application object exists in some builds, and its startup cost does
        not belong in an ordinary Qt test.
        """
        qgis_environment.require_webengine()
        from PyQt5 import QtWebEngineWidgets  # noqa: F401 - imported for its side effect

        return qt_app

    # ── the shared recorder ─────────────────────────────────────────────────

    @pytest.fixture
    def shared_calls():
        """An empty :class:`~qgis_sdk.testing.calls.CallLog` for this test.

        Hand it to several fakes — ``FakeIface(calls=shared_calls)``,
        ``FakeNetworkTransport(calls=shared_calls)`` — to read their calls
        interleaved in the order they really happened.
        """
        return CallLog()

    # ── fakes ───────────────────────────────────────────────────────────────

    @pytest.fixture
    def fake_iface():
        return FakeIface()

    @pytest.fixture(name="fake_action_factory")
    def _fixture_fake_action_factory():
        return fake_action_factory

    @pytest.fixture
    def fake_context():
        return FakeContext()

    @pytest.fixture(name="fake_dialog_factory")
    def _fixture_fake_dialog_factory():
        return fake_dialog_factory

    @pytest.fixture(name="fake_webview_factory")
    def _fixture_fake_webview_factory():
        return fake_webview_factory

    @pytest.fixture
    def fake_bridge():
        return FakeBridge()

    @pytest.fixture(name="bridge_harness_factory")
    def _fixture_bridge_harness_factory():
        """Build a :class:`BridgeHarness` from manifests the test supplies."""
        return BridgeHarness

    @pytest.fixture(name="fake_dialog")
    def _fixture_fake_dialog():
        return FakeDialog()

    @pytest.fixture(name="fake_webview")
    def _fixture_fake_webview():
        return FakeWebView()

    @pytest.fixture
    def mock_features_fixture():
        return mock_features

    @pytest.fixture
    def mock_source_fixture():
        return mock_source

    @pytest.fixture
    def mock_context_fixture():
        return mock_context

    @pytest.fixture(name="mock_features")
    def _fixture_mock_features():
        return mock_features

    @pytest.fixture(name="mock_source")
    def _fixture_mock_source():
        return mock_source

    @pytest.fixture(name="mock_context")
    def _fixture_mock_context():
        return mock_context

    @pytest.fixture
    def fake_network_response():
        return FakeNetworkResponse()

    @pytest.fixture(name="fake_network_manager")
    def _fixture_fake_network_manager():
        return FakeNetworkManager()

    @pytest.fixture(name="fake_network_transport")
    def _fixture_fake_network_transport():
        """A scripted transport: nothing answers until the test says so."""
        return FakeNetworkTransport()

    @pytest.fixture(name="fake_content_fetcher")
    def _fixture_fake_content_fetcher():
        return FakeContentFetcher()

    @pytest.fixture(name="fake_session")
    def _fixture_fake_session():
        return FakeSession()

    @pytest.fixture
    def fake_task():
        return FakeTask()

    @pytest.fixture(name="fake_task_manager")
    def _fixture_fake_task_manager():
        return FakeTaskManager()

    @pytest.fixture(name="manual_task_manager")
    def _fixture_manual_task_manager():
        """A task manager that runs nothing until ``run_next()`` is called."""
        return FakeTaskManager(auto_run=False)

    @pytest.fixture(name="fake_async_result")
    def _fixture_fake_async_result():
        t = FakeTask("Test", lambda: 42)
        return FakeAsyncResult(t)

    @pytest.fixture(name="fake_task_wrapper")
    def _fixture_fake_task_wrapper():
        def my_func(x, y):
            return x + y

        return FakeTaskWrapper(my_func, description="Test task")

    @pytest.fixture(name="fake_qgis_api")
    def _fixture_fake_qgis_api(fake_iface, fake_network_manager, fake_task_manager):
        return FakeQgisAPI(
            iface=fake_iface, network_manager=fake_network_manager, task_manager=fake_task_manager
        )

    @pytest.fixture(name="fake_layers_api")
    def _fixture_fake_layers_api():
        return FakeLayersAPI()

    @pytest.fixture(name="fake_project_api")
    def _fixture_fake_project_api():
        return FakeProjectAPI()

    @pytest.fixture(name="fake_message_api")
    def _fixture_fake_message_api():
        return FakeMessageAPI()

    @pytest.fixture(name="fake_tasks_api")
    def _fixture_fake_tasks_api(fake_task_manager):
        return FakeTasksAPI(task_manager=fake_task_manager)

    @pytest.fixture(name="fake_network_api")
    def _fixture_fake_network_api(fake_network_manager):
        return FakeNetworkAPI(network_manager=fake_network_manager)
