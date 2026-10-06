"""
qgis_sdk.testing — pytest fixtures and fakes for testing QGIS plugins without QGIS.

This package is importable without QGIS/Qt. It provides:
- Fake QGIS interface (QgisInterface) and actions
- Fake contexts for Algorithms
- Fake dialogs and web views
- A protocol-faithful bridge harness, plus the older fake bridge
- Fake network (requests-like), a scripted transport, and tasks (celery-like)
- Hypothesis strategies for pure values
- pytest fixtures (auto-discovered if you add `pytest_plugins = ["qgis_sdk.testing"]` or via entry point)

Usage in tests:

    # conftest.py
    pytest_plugins = ["qgis_sdk.testing"]

    # test_my_plugin.py
    def test_toolbar(fake_iface, fake_action_factory):
        from my_plugin import MyPlugin
        MyPlugin.action_factory = staticmethod(fake_action_factory)
        plugin = MyPlugin(fake_iface)
        plugin.init_gui()
        assert len(fake_iface.toolbar_icons) == 1
        fake_iface.toolbar_icons[0].trigger()
        assert "hello" in fake_iface.messages

    def test_dialog(fake_dialog_factory, fake_webview_factory):
        from qgis_sdk.ui import Dialog, field, layout, Button
        dlg = Dialog(title="Test", layout=[field.text("name", default="hi")])
        dlg._qdialog = fake_dialog_factory()
        assert dlg.get("name") == "hi"

    def test_bridge(fake_bridge):
        assert fake_bridge.get_layer() == {"name": "test"}

    def test_network(fake_network_manager):
        resp = fake_network_manager.get("https://example.com/api")
        assert resp.ok
        assert resp.json()["mock"] is True

    def test_scripted_network(fake_network_transport):
        fake_network_transport.reply("GET", "https://example.test/api", json_data={"ok": True})
        assert fake_network_transport.get("https://example.test/api").json() == {"ok": True}

    def test_tasks_celery_like(fake_task_manager):
        from qgis_sdk.tasks import task

        @task(bind=True)
        def add(self, x, y):
            self.set_progress(50)
            return x + y

        result = add(4, 4)  # sync
        assert result == 8

        async_result = add.delay(4, 4)  # async via FakeTaskManager
        assert async_result.get() == 8
        assert async_result.ready()
        assert async_result.successful()
        assert async_result.state == "SUCCESS"

    def test_tasks_deterministically(manual_task_manager):
        task = manual_task_manager.submit(lambda: 42)
        assert task.state == "PENDING"
        manual_task_manager.run_next()
        assert task.state == "SUCCESS"

Layout (TASK-32, doc-5). One module per concern, and this file is the
compatibility facade: every name that used to live in `qgis_sdk/testing.py`
is still importable from `qgis_sdk.testing`, and every fixture keeps its name.

    environment.py   pure / Qt / QGIS / WebEngine detection
    calls.py         Call and CallLog — one shape for every recorded call
    iface.py         FakeIface, FakeAction
    ui.py            FakeDialog, FakeWebView, FakeWebChannel
    bridge.py        BridgeHarness (the protocol), FakeBridge (the old toy)
    qgis_api.py      window.qgis — the browser-facing façade
    network.py       FakeNetworkTransport (scripted) and the requests-like fakes
    tasks.py         the PENDING/RUNNING/SUCCESS/FAILURE/CANCELED machine
    processing.py    FakeContext, FakeSink, mock_source, mock_context
    data.py          FakeFeature, FakeGeometry, FakeFields, mock_features
    strategies.py    Hypothesis strategies for pure values (needs hypothesis)
    plugin.py        the pytest plugin: fixtures and markers
"""

from __future__ import annotations

from .bridge import (
    BRIDGE_VERSION,
    ERROR_KINDS,
    BridgeContractError,
    BridgeHarness,
    FakeBridge,
    HostError,
    fake_bridge_factory,
    validate_value,
)
from .calls import Call, CallLog, call_log
from .data import FakeFeature, FakeFields, FakeGeometry, mock_features
from .environment import QgisTestEnvironment, detect_qgis_environment
from .iface import FakeAction, FakeIface, fake_action_factory
from .network import (
    FakeContentFetcher,
    FakeNetworkManager,
    FakeNetworkResponse,
    FakeNetworkTransport,
    FakeResponse,
    FakeSession,
    NoScriptedReply,
    RedirectLoop,
    fake_content_fetcher_factory,
    fake_network_manager_factory,
    fake_network_response_factory,
    fake_network_transport_factory,
    fake_session_factory,
)
from .processing import FakeContext, FakeSink, mock_context, mock_source
from .qgis_api import (
    FakeIfaceAPI,
    FakeLayersAPI,
    FakeMessageAPI,
    FakeNetworkAPI,
    FakeProcessingAPI,
    FakeProjectAPI,
    FakeQgisAPI,
    FakeSettingsAPI,
    FakeTasksAPI,
    fake_qgis_api_factory,
)
from .tasks import (
    CANCELED,
    CELERY_STATE_ALIASES,
    FAILURE,
    LEGAL_TRANSITIONS,
    PENDING,
    RUNNING,
    SUCCESS,
    TASK_STATES,
    TERMINAL_STATES,
    FakeAsyncResult,
    FakeSignature,
    FakeTask,
    FakeTaskManager,
    FakeTaskWrapper,
    IllegalTransition,
    ScheduledTask,
    TaskChain,
    TaskGroup,
    canonical_state,
    fake_task_factory,
    fake_task_manager_factory,
)
from .ui import (
    FakeDialog,
    FakeDialogWidget,
    FakeWebChannel,
    FakeWebPage,
    FakeWebView,
    fake_dialog_factory,
    fake_webview_factory,
)

# The pytest plugin. Its hooks and fixtures are re-exported here because the
# `pytest11` entry point and `pytest_plugins = ["qgis_sdk.testing"]` both name
# *this* module, and pytest reads a plugin's fixtures out of its namespace.
from . import plugin as _plugin
from .plugin import MARKERS, pytest_collection_modifyitems, pytest_configure

def _is_fixture(value: object) -> bool:
    """Whether ``value`` is a pytest fixture, in either of pytest's shapes.

    Up to pytest 8.3 a fixture was the decorated function carrying
    ``_pytestfixturefunction``; 8.4 replaced it with a
    ``FixtureFunctionDefinition`` carrying ``_fixture_function_marker``. The
    facade has to recognise both, or the fixtures silently stop being
    discoverable on one of them — which is a green suite that tests nothing.
    """
    return hasattr(value, "_pytestfixturefunction") or hasattr(
        value, "_fixture_function_marker"
    )


# Fixtures declared under a private name (`@pytest.fixture(name="fake_dialog")`
# on `_fixture_fake_dialog`) are skipped by `import *`, so they are copied in
# here. A loop rather than a 25-line import list: a fixture added to
# plugin.py should not need a second edit here to be discoverable.
for _name, _value in vars(_plugin).items():
    if _name.startswith("_fixture_") and _is_fixture(_value):
        globals()[_name] = _value
    elif not _name.startswith("_") and _is_fixture(_value):
        globals().setdefault(_name, _value)
del _name, _value

try:  # Hypothesis is a test-only dependency; the SDK itself must import without it.
    from . import strategies
except ImportError:  # pragma: no cover - depends on the environment
    strategies = None  # type: ignore[assignment]


__all__ = [
    # window.qgis
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
    # host and UI fakes
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
    # bridge
    "FakeBridge",
    "BridgeHarness",
    "BridgeContractError",
    "HostError",
    "BRIDGE_VERSION",
    "ERROR_KINDS",
    "validate_value",
    # network
    "FakeNetworkResponse",
    "FakeResponse",
    "FakeNetworkTransport",
    "FakeNetworkManager",
    "FakeSession",
    "FakeContentFetcher",
    "NoScriptedReply",
    "RedirectLoop",
    # tasks
    "FakeTask",
    "FakeAsyncResult",
    "FakeSignature",
    "FakeTaskWrapper",
    "FakeTaskManager",
    "ScheduledTask",
    "TaskChain",
    "TaskGroup",
    "IllegalTransition",
    "canonical_state",
    "PENDING",
    "RUNNING",
    "SUCCESS",
    "FAILURE",
    "CANCELED",
    "TASK_STATES",
    "TERMINAL_STATES",
    "LEGAL_TRANSITIONS",
    "CELERY_STATE_ALIASES",
    # calls
    "Call",
    "CallLog",
    "call_log",
    # factories
    "fake_action_factory",
    "fake_dialog_factory",
    "fake_webview_factory",
    "fake_bridge_factory",
    "fake_network_manager_factory",
    "fake_network_response_factory",
    "fake_content_fetcher_factory",
    "fake_session_factory",
    "fake_network_transport_factory",
    "fake_task_manager_factory",
    "fake_task_factory",
    # environment
    "QgisTestEnvironment",
    "detect_qgis_environment",
    "MARKERS",
    # data builders
    "mock_features",
    "mock_source",
    "mock_context",
    # pytest plugin hooks
    "pytest_configure",
    "pytest_collection_modifyitems",
    "strategies",
]
