"""The four execution layers, as separately runnable gates.

A suite that answers a QGIS question with a fake has reported a green it did
not earn, and so has a *gate* that passes because every test in it skipped.
These tests cover both halves: which tests a gate selects, and the refusal to
call an unreachable layer a pass.

The selection policy itself is pure data — :mod:`qgis_sdk.testing.gates` imports
neither pytest nor Qt — so most of this file needs no runtime at all.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest

from qgis_sdk.testing import gates
from qgis_sdk.testing.environment import detect_qgis_environment

# ── AC#1: a marker selects one layer, and nothing selects a layer by accident ──


def test_the_gate_names_are_the_four_execution_layers():
    assert gates.GATES == ("pure", "qt", "qgis", "webengine")


def test_every_plugin_fixture_is_reachable_from_the_package():
    """A fixture that plugin.py defines but the package does not re-export is
    invisible to every consumer, and nothing else notices.

    This is not hypothetical: adding a ``qgis_lifecycle`` submodule while a
    ``qgis_runtime`` fixture existed made the package attribute resolve to the
    module, and the fixture vanished with no error until a test asked for it.
    """
    from qgis_sdk import testing
    from qgis_sdk.testing import plugin

    missing = [
        name
        for name, value in vars(plugin).items()
        if not name.startswith("_")
        and testing._is_fixture(value)
        and not testing._is_fixture(getattr(testing, name, None))
    ]
    assert not missing, f"fixtures defined in plugin.py but not re-exported: {missing}"


@pytest.mark.parametrize(
    ("markers", "expected"),
    [
        (set(), frozenset()),
        ({"qt"}, frozenset({"qt"})),
        ({"qgis"}, frozenset({"qgis"})),
        ({"webengine"}, frozenset({"webengine"})),
        # Non-layer markers say nothing about which runtime is needed.
        ({"network", "tasks"}, frozenset()),
        ({"pure_python"}, frozenset()),
        ({"qt", "webengine"}, frozenset({"qt", "webengine"})),
    ],
)
def test_only_layer_markers_demand_a_runtime(markers, expected):
    assert gates.layers_required(markers) == expected


@pytest.mark.parametrize(
    ("gate", "markers", "selected"),
    [
        # The pure gate is everything that demands no runtime at all.
        ("pure", set(), True),
        ("pure", {"pure_python"}, True),
        ("pure", {"network"}, True),
        ("pure", {"qt"}, False),
        ("pure", {"qgis"}, False),
        ("pure", {"webengine"}, False),
        # A layer gate is exactly the tests that asked for that layer.
        ("qt", {"qt"}, True),
        ("qt", set(), False),
        ("qt", {"qgis"}, False),
        ("qgis", {"qgis"}, True),
        ("qgis", {"qt"}, False),
        ("webengine", {"webengine"}, True),
        ("webengine", {"qt"}, False),
        # A test needing two layers belongs to both gates.
        ("qt", {"qt", "webengine"}, True),
        ("webengine", {"qt", "webengine"}, True),
    ],
)
def test_each_gate_selects_exactly_its_own_layer(gate, markers, selected):
    assert gates.selected_by(gate, markers) is selected


def test_the_gates_partition_nothing_and_overlap_only_on_purpose():
    """Every test lands in at least one gate, so no test is unreachable."""
    for markers in (set(), {"qt"}, {"qgis"}, {"webengine"}, {"network"}):
        reached = [gate for gate in gates.GATES if gates.selected_by(gate, markers)]
        assert reached, f"a test marked {markers or '{}'} is in no gate at all"


def test_an_unknown_gate_is_refused_rather_than_silently_matching_nothing():
    with pytest.raises(ValueError, match="unknown"):
        gates.selected_by("gtk", set())


def test_the_requested_gate_comes_from_the_environment():
    assert gates.requested_gate({}) is None
    assert gates.requested_gate({gates.LAYER_ENV_VAR: "qgis"}) == "qgis"
    assert gates.requested_gate({gates.LAYER_ENV_VAR: "  QT "}) == "qt"
    assert gates.requested_gate({gates.LAYER_ENV_VAR: ""}) is None
    with pytest.raises(ValueError, match="unknown"):
        gates.requested_gate({gates.LAYER_ENV_VAR: "gtk"})


# ── AC#1 + AC#4: an unreachable gate fails, it does not skip ──────────────────


def _run_pytest(tmp_path, body, env_extra):
    """Run a one-test suite in a subprocess and return the completed process."""
    # No `pytest_plugins` here: the SDK installs a `pytest11` entry point, so
    # the plugin is already loaded and registering it again is an error.
    (tmp_path / "test_sample.py").write_text(textwrap.dedent(body))
    env = {**os.environ}
    # The child must not inherit the gate this suite is itself running under,
    # or "no gate requested" becomes untestable from inside a gated run.
    env.pop(gates.LAYER_ENV_VAR, None)
    env.update(env_extra)
    env["QT_QPA_PLATFORM"] = "offscreen"
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(tmp_path), "-p", "no:cacheprovider", "-q"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )


def test_a_gate_whose_layer_is_missing_fails_instead_of_skipping(tmp_path):
    """The whole point: an unreachable gate must not report success.

    WebEngine is the honest case to assert on, because it is the one layer
    this environment genuinely does not have.
    """
    if detect_qgis_environment().webengine_available:
        pytest.skip("this environment has WebEngine, so it cannot demonstrate the refusal")

    result = _run_pytest(
        tmp_path,
        """
        import pytest

        @pytest.mark.webengine
        def test_needs_webengine():
            assert True
        """,
        {gates.LAYER_ENV_VAR: "webengine"},
    )
    assert result.returncode != 0, result.stdout
    assert "webengine" in (result.stdout + result.stderr)


def test_a_gate_runs_only_its_own_layer(tmp_path):
    """The pure gate must not drag a Qt test in behind it."""
    result = _run_pytest(
        tmp_path,
        """
        import pytest

        def test_pure():
            assert True

        @pytest.mark.qt
        def test_qt():
            raise AssertionError("the pure gate must not run a qt test")
        """,
        {gates.LAYER_ENV_VAR: "pure"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_without_a_gate_the_whole_suite_still_runs_with_skips(tmp_path):
    """The default command keeps its old behaviour: skip, do not fail."""
    if detect_qgis_environment().webengine_available:
        pytest.skip("this environment has WebEngine")

    result = _run_pytest(
        tmp_path,
        """
        import pytest

        def test_pure():
            assert True

        @pytest.mark.webengine
        def test_webengine():
            raise AssertionError("must be skipped, not run")
        """,
        {},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout
    assert "1 skipped" in result.stdout


# ── AC#2: Qt is initialised once, offscreen, before any widget ────────────────


@pytest.mark.qt
def test_the_qt_gate_runs_offscreen(qt_app):
    assert os.environ["QT_QPA_PLATFORM"] == "offscreen"
    assert qt_app is not None


@pytest.mark.qt
def test_one_qapplication_exists_and_the_fixture_returns_it(qt_app):
    from PyQt5.QtWidgets import QApplication

    assert QApplication.instance() is qt_app


@pytest.mark.qt
def test_a_widget_is_only_built_after_the_application_exists(qt_app):
    from PyQt5.QtWidgets import QApplication, QWidget

    assert QApplication.instance() is not None, "Qt aborts if a QWidget precedes the app"
    widget = QWidget()
    try:
        assert widget is not None
    finally:
        widget.deleteLater()


def test_detection_never_constructs_an_application():
    """``detect_qgis_environment`` is called before a test may run, so it has
    to be free of side effects — including the big one."""
    environment = detect_qgis_environment()
    if not environment.qt_available:
        pytest.skip("requires an importable PyQt5 runtime")

    from PyQt5.QtWidgets import QApplication

    before = QApplication.instance()
    detect_qgis_environment()
    assert QApplication.instance() is before


# ── AC#3: QGIS initialises and shuts down deterministically ───────────────────


def test_a_qgis_application_initialises_and_exits_cleanly():
    """Proven out of process, because this is a claim about interpreter exit.

    An in-process assertion could not tell a clean shutdown from one that
    aborts after pytest has already printed its summary.
    """
    if not detect_qgis_environment().qgis_available:
        pytest.skip("requires an importable qgis.core runtime")

    program = textwrap.dedent(
        """
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from qgis_sdk.testing.qgis_lifecycle import qgis_application

        with qgis_application() as app:
            assert app is not None
            from qgis.core import QgsApplication
            assert QgsApplication.instance() is app
        print("CLEAN")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, env=os.environ
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "CLEAN" in result.stdout


@pytest.mark.qgis
def test_the_qgis_gate_runs_serialized(request):
    """Parallel QGIS tests share one native singleton, so the gate refuses
    xdist rather than producing a flake nobody can reproduce."""
    assert gates.parallelism_of(request.config) == 1


# ── AC#6: no global fixture leaks ─────────────────────────────────────────────

_SEEN_CALL_LOGS: list[int] = []


def test_the_shared_call_log_is_fresh_per_test_first(shared_calls):
    shared_calls.record("iface", "message", text="hi")
    _SEEN_CALL_LOGS.append(id(shared_calls))
    assert len(shared_calls) == 1


def test_the_shared_call_log_is_fresh_per_test_second(shared_calls):
    assert len(shared_calls) == 0, "a function-scoped fake leaked between tests"
    assert id(shared_calls) not in _SEEN_CALL_LOGS or len(shared_calls) == 0


def test_fake_network_transport_does_not_leak_scripted_routes_first(fake_network_transport):
    fake_network_transport.reply("GET", "https://example.test/leak", json_data={"ok": True})
    assert fake_network_transport.get("https://example.test/leak").json() == {"ok": True}


def test_fake_network_transport_does_not_leak_scripted_routes_second(fake_network_transport):
    from qgis_sdk.testing.network import NoScriptedReply

    with pytest.raises(NoScriptedReply):
        fake_network_transport.get("https://example.test/leak")


def test_the_environment_fixture_is_a_value_not_a_live_handle(qgis_environment):
    """Session-scoped, so it must be immutable — a mutable session fixture is
    exactly how one test's state reaches another."""
    with pytest.raises((AttributeError, TypeError)):
        qgis_environment.qgis_available = not qgis_environment.qgis_available
