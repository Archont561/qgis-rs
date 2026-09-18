"""qgis-sdk — a Python SDK for building QGIS plugins on top of PyQGIS.

The SDK is importable without QGIS installed: only :mod:`qgis_sdk.runtime`
touches PyQGIS, and it does so lazily. That is what makes unit-testing plugin
logic possible on a plain developer machine.

Now with Rust-native CLI and acceleration:
- `pip install qgis-sdk` gives you `qgis-plugin` binary + Python API at native speed
- `qgis-plugin new my_plugin --rust` scaffolds a plugin with Rust acceleration
- `import qgis_sdk` tries to load Rust extension `_core` for native speed, falls back to Python
"""

from __future__ import annotations

from .algorithm import Algorithm, OutputSpec, ParamSpec, output, parameter
from .metadata import METADATA_FIELDS, render_metadata, write_metadata
from .plugin import ActionSpec, Plugin, action, class_factory, menu, toolbar, plugin, setting, registry, task as plugin_task
from .plugin import task as task_decorator  # declarative @task
from .runtime import PyQgisImportError, expected_pythonpath, qgis_core, qgis_gui

# New bridge API
try:
    from .bridge import (
        BridgeDescription,
        MethodDescription,
        BridgeRuntime,
        BridgeWindow,
        QgisApi,
        bridge as bridge_decorator,
        method,
        signal,
        slot,
        load_bridge_description,
    )
except ImportError:
    BridgeDescription = MethodDescription = BridgeRuntime = BridgeWindow = QgisApi = None
    bridge_decorator = method = signal = slot = load_bridge_description = None

# Bootstrap / installer
try:
    from .bootstrap import ensure_qgis_sdk, is_qgis_sdk_installed, bootstrap_plugin
    from .installer import Installer
except ImportError:
    ensure_qgis_sdk = is_qgis_sdk_installed = bootstrap_plugin = Installer = None

# Try Rust extension for native speed
try:
    from ._core import version as _rust_version, __version__ as _core_version  # type: ignore

    __version__ = _core_version
    HAS_RUST = True
    RUST_VERSION = _rust_version()
except ImportError:
    __version__ = "0.1.0"
    HAS_RUST = False
    RUST_VERSION = None

# CLI is available via qgis_sdk.cli
try:
    from . import cli as _cli  # noqa: F401

    HAS_CLI = True
except ImportError:
    HAS_CLI = False

# UI module — declarative dialogs + WebEngine, always available (fallback without Qt)
try:
    from . import ui as _ui  # noqa: F401

    HAS_UI = True
except ImportError:
    HAS_UI = False

# Expose ui symbols at top level for convenience
try:
    from .ui import Button, Dialog, FieldSpec, WebDialog, dialog, field, layout, web_bridge
except ImportError:
    Button = Dialog = FieldSpec = WebDialog = None  # type: ignore
    dialog = web_bridge = field = layout = None  # type: ignore

# Testing fixtures — always available (no QGIS needed)
try:
    from . import testing as _testing  # noqa: F401

    HAS_TESTING = True
except ImportError:
    HAS_TESTING = False

# Bridge generation — always available
try:
    from . import bridge as _bridge  # noqa: F401

    HAS_BRIDGE = True
except ImportError:
    HAS_BRIDGE = False

# Network manager — always available (fallback without QGIS)
try:
    from . import network as _network  # noqa: F401

    HAS_NETWORK = True
except ImportError:
    HAS_NETWORK = False

# Task manager — always available (fallback without QGIS)
try:
    from . import tasks as _tasks  # noqa: F401

    HAS_TASKS = True
except ImportError:
    HAS_TASKS = False

try:
    from .testing import (
        FakeAction,
        FakeAsyncResult,
        FakeBridge,
        FakeContentFetcher,
        FakeContext,
        FakeDialog,
        FakeFeature,
        FakeFields,
        FakeGeometry,
        FakeIface,
        FakeNetworkManager,
        FakeNetworkResponse,
        FakeSession,
        FakeSignature,
        FakeSink,
        FakeTask,
        FakeTaskManager,
        FakeTaskWrapper,
        FakeWebChannel,
        FakeWebPage,
        FakeWebView,
        fake_action_factory,
        fake_bridge_factory,
        fake_content_fetcher_factory,
        fake_dialog_factory,
        fake_network_manager_factory,
        fake_network_response_factory,
        fake_session_factory,
        fake_task_factory,
        fake_task_manager_factory,
        fake_webview_factory,
        mock_context,
        mock_features,
        mock_source,
    )
except ImportError:
    FakeAction = FakeBridge = FakeContentFetcher = FakeContext = FakeDialog = None  # type: ignore
    FakeFeature = FakeFields = FakeGeometry = FakeIface = None  # type: ignore
    FakeNetworkManager = FakeNetworkResponse = FakeSession = FakeSink = FakeTask = FakeTaskManager = None  # type: ignore
    FakeAsyncResult = FakeSignature = FakeTaskWrapper = FakeWebChannel = FakeWebPage = FakeWebView = None  # type: ignore
    fake_action_factory = fake_bridge_factory = fake_content_fetcher_factory = fake_dialog_factory = None  # type: ignore
    fake_network_manager_factory = fake_network_response_factory = fake_session_factory = fake_task_factory = fake_task_manager_factory = None  # type: ignore
    fake_webview_factory = mock_context = mock_features = mock_source = None  # type: ignore

try:
    from .bridge import generate_js_wrapper, generate_package, generate_ts_bridge, load_bridge_class
except ImportError:
    generate_js_wrapper = generate_package = generate_ts_bridge = load_bridge_class = None  # type: ignore

try:
    from .network import (
        ConnectionError,
        ContentFetcher,
        HTTPError,
        NetworkAccessManager,
        NetworkError,
        NetworkManager,
        NetworkResponse,
        RequestException,
        Session,
        Timeout,
        TooManyRedirects,
        delete,
        download,
        fetch,
        fetch_json,
        fetch_text,
        get,
        head,
        options,
        patch,
        post,
        put,
        request,
    )
except ImportError:
    ContentFetcher = NetworkAccessManager = NetworkError = NetworkManager = NetworkResponse = None  # type: ignore
    RequestException = HTTPError = ConnectionError = Timeout = TooManyRedirects = Session = None  # type: ignore
    download = fetch = fetch_json = fetch_text = get = post = put = patch = delete = head = options = request = None  # type: ignore

try:
    from .tasks import (
        AsyncResult,
        Chain,
        ProcessingAlgRunnerTask,
        Signature,
        Task,
        TaskManager,
        TaskWrapper,
        add_task,
        app,
        cancel_all,
        celery_app,
        celery_task,
        chain,
        group,
        run_task,
        shared_task,
        task as celery_task_decorator,
    )
    # Keep celery task available as shared_task/celery_task, but top-level `task` is declarative
    task = task_decorator  # declarative @task from plugin
except ImportError:
    ProcessingAlgRunnerTask = Task = TaskManager = TaskWrapper = AsyncResult = Signature = Chain = None  # type: ignore
    add_task = cancel_all = run_task = shared_task = celery_task = app = celery_app = chain = group = celery_task_decorator = None  # type: ignore
    # task stays as declarative if available
    try:
        task = task_decorator
    except NameError:
        task = None  # type: ignore

__all__ = [
    "METADATA_FIELDS",
    "ActionSpec",
    "Algorithm",
    "OutputSpec",
    "ParamSpec",
    "Plugin",
    "PyQgisImportError",
    "__version__",
    "HAS_RUST",
    "HAS_CLI",
    "HAS_UI",
    "HAS_TESTING",
    "HAS_BRIDGE",
    "HAS_NETWORK",
    "HAS_TASKS",
    "RUST_VERSION",
    "action",
    "class_factory",
    "expected_pythonpath",
    "menu",
    "output",
    "parameter",
    "qgis_core",
    "qgis_gui",
    "render_metadata",
    "toolbar",
    "write_metadata",
    # new declarative
    "plugin",
    "setting",
    "registry",
    # bridge new API
    "BridgeDescription",
    "MethodDescription",
    "BridgeRuntime",
    "BridgeWindow",
    "QgisApi",
    "bridge_decorator",
    "method",
    "signal",
    "slot",
    "load_bridge_description",
    # bootstrap / installer
    "ensure_qgis_sdk",
    "is_qgis_sdk_installed",
    "bootstrap_plugin",
    "Installer",
    # ui
    "Dialog",
    "WebDialog",
    "dialog",
    "web_bridge",
    "field",
    "layout",
    "Button",
    "FieldSpec",
    # testing
    "FakeAction",
    "FakeBridge",
    "FakeContentFetcher",
    "FakeContext",
    "FakeDialog",
    "FakeFeature",
    "FakeFields",
    "FakeGeometry",
    "FakeIface",
    "FakeNetworkManager",
    "FakeNetworkResponse",
    "FakeSession",
    "FakeSink",
    "FakeTask",
    "FakeAsyncResult",
    "FakeSignature",
    "FakeTaskWrapper",
    "FakeTaskManager",
    "FakeWebChannel",
    "FakeWebPage",
    "FakeWebView",
    "fake_action_factory",
    "fake_bridge_factory",
    "fake_content_fetcher_factory",
    "fake_dialog_factory",
    "fake_network_manager_factory",
    "fake_network_response_factory",
    "fake_session_factory",
    "fake_task_factory",
    "fake_task_manager_factory",
    "fake_webview_factory",
    "mock_context",
    "mock_features",
    "mock_source",
    # bridge
    "generate_ts_bridge",
    "generate_js_wrapper",
    "generate_package",
    "load_bridge_class",
    # network — requests-like
    "NetworkManager",
    "NetworkAccessManager",
    "ContentFetcher",
    "NetworkResponse",
    "NetworkError",
    "RequestException",
    "HTTPError",
    "ConnectionError",
    "Timeout",
    "TooManyRedirects",
    "Session",
    "request",
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "head",
    "options",
    "fetch",
    "fetch_json",
    "fetch_text",
    "download",
    # tasks — celery-like
    "Task",
    "TaskManager",
    "TaskWrapper",
    "AsyncResult",
    "Signature",
    "Chain",
    "ProcessingAlgRunnerTask",
    "task",
    "shared_task",
    "celery_task",
    "app",
    "celery_app",
    "run_task",
    "add_task",
    "cancel_all",
    "chain",
    "group",
]
