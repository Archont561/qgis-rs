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

from . import gates
from .bridge import BridgeHarness, FakeBridge
from .calls import CallLog
from .environment import detect_qgis_environment
from .qgis_lifecycle import qgis_application as _qgis_application
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

#: Where the resolved gate is stashed between `pytest_configure` and
#: collection. A `StashKey` rather than a module global so two pytest sessions
#: in one interpreter — which is exactly what this package's own tests do —
#: cannot read each other's state.
if pytest is not None:  # pragma: no branch - pytest is present wherever tests run
    _GATE_KEY = pytest.StashKey()
else:  # pragma: no cover - the SDK is importable without pytest
    _GATE_KEY = None  # type: ignore[assignment]


def pytest_configure(config):
    """Register markers, and refuse a gate this environment cannot run.

    The refusal happens here rather than during collection because it is not
    a property of any single test: asking for the ``qgis`` gate on a machine
    without QGIS is a wrong *command*, and a wrong command should fail before
    it has collected anything.
    """
    import pytest as _pytest

    for name, description in MARKERS.items():
        config.addinivalue_line("markers", f"{name}: {description}")

    try:
        gate = gates.requested_gate(os.environ)
    except ValueError as exc:
        raise _pytest.UsageError(str(exc)) from exc
    if gate is None:
        return

    reason = gates.unreachable_reason(gate, detect_qgis_environment())
    if reason is not None:
        raise _pytest.UsageError(reason)

    if gate == "qgis" and gates.parallelism_of(config) > 1:
        raise _pytest.UsageError(
            "the qgis gate must run serialized: QgsApplication is a process-wide "
            "singleton and parallel workers would share it"
        )

    config.stash[_GATE_KEY] = gate


def pytest_report_header(config):
    """Say which runtime backs this run, which layers exist, and which gate runs.

    One line, printed once at the top, so a CI log answers "which QGIS was this
    run against, and was it the QGIS path or the pure-Python fallback" without
    anyone re-running the suite.
    """
    environment = detect_qgis_environment()
    gate = config.stash.get(_GATE_KEY, None) if hasattr(config, "stash") else None
    layers = ", ".join(sorted(environment.layers))
    version = environment.qgis_version or "unavailable"
    return (
        f"qgis-sdk runtime: backend={environment.backend}, qgis={version}; "
        f"layers: {layers}; gate: {gate or 'all (skips allowed)'}"
    )


def pytest_collection_modifyitems(config, items):
    """Narrow the run to the requested gate, or skip unreachable layers.

    Two modes, and the difference between them is the whole point of the
    gates. Without a gate the suite is permissive: a test whose layer is
    missing is skipped before its body runs, never handed a fake. With a gate
    the suite is narrow and strict: only that layer's tests are kept, and a
    skip for a missing runtime cannot occur because ``pytest_configure``
    already refused the run.
    """
    import pytest as _pytest

    environment = detect_qgis_environment()
    gate = config.stash.get(_GATE_KEY, None) if hasattr(config, "stash") else None

    if gate is not None:
        selected, deselected = [], []
        for item in items:
            markers = {mark.name for mark in item.iter_markers()}
            (selected if gates.selected_by(gate, markers) else deselected).append(item)
        if deselected:
            config.hook.pytest_deselected(items=deselected)
        items[:] = selected

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
    def qgis_app(request, qgis_environment):
        """The live QgsApplication these tests should run against.

        Three cases, in order, and the order is the whole design:

        1. **A host is already running one** — a plugin's tests inside QGIS.
           Adopt it; never construct or tear down someone else's singleton.
        2. **The ``qgis`` gate is active** — the caller asserted this layer
           works, so construct one through :func:`qgis_runtime` rather than
           skipping. A gate that skipped here would be a green that proved
           nothing, which is the exact failure the gates exist to prevent.
        3. **Neither** — a plain pytest process that merely happens to have
           PyQGIS importable. Skip, as before: constructing a native
           application nobody asked for is how a suite starts aborting at
           interpreter shutdown.
        """
        qgis_environment.require_qgis()
        from qgis.core import QgsApplication

        app = QgsApplication.instance()
        if app is not None:
            return app
        if request.config.stash.get(_GATE_KEY, None) == "qgis":
            return request.getfixturevalue("qgis_runtime")
        pytest.skip("qgis.core is installed, but no QgsApplication is running")

    @pytest.fixture(scope="session")
    def qgis_runtime(qgis_environment):
        """A real ``QgsApplication``, constructed and shut down by this fixture.

        The difference from :func:`qgis_app` is ownership. ``qgis_app`` adopts
        the host's application and skips when there is none, which is what a
        plugin's own tests want. This fixture is what the ``qgis`` gate wants:
        it *creates* the application in a plain pytest process, so the gate
        proves the QGIS layer works rather than proving it was absent.

        Session-scoped because ``QgsApplication`` is a process-wide singleton,
        and torn down with ``exitQgis()`` before interpreter shutdown — see
        :mod:`qgis_sdk.testing.qgis_lifecycle`.
        """
        qgis_environment.require_qgis()
        with _qgis_application() as application:
            yield application

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
