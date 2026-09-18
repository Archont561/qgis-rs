"""Tests for qgis_sdk.testing — pytest fixtures and fakes."""

from __future__ import annotations


def test_fake_iface():
    from qgis_sdk.testing import FakeIface, fake_action_factory
    from qgis_sdk.plugin import ActionSpec

    iface = FakeIface()
    assert iface.toolbar_icons == []
    assert iface.menu_entries == []
    assert iface.messages == []

    spec = ActionSpec(func_name="run", tooltip="Run", icon=None, toolbar="Test", menu=())

    def cb():
        iface.messageBar().pushMessage("hello")

    action = fake_action_factory(spec, cb)
    assert action.tooltip == "Run"
    assert action.triggered == 0
    action.trigger()
    assert action.triggered == 1
    assert "hello" in iface.messages

    iface.addToolBarIcon(action)
    assert len(iface.toolbar_icons) == 1
    iface.removeToolBarIcon(action)
    assert len(iface.toolbar_icons) == 0


def test_fake_context():
    from qgis_sdk.testing import FakeContext

    ctx = FakeContext(values={"input": "test.gpkg", "threshold": 0.5})
    assert ctx.get("input") == "test.gpkg"
    assert ctx.get("threshold") == 0.5
    assert ctx.get("missing", "default") == "default"

    ctx.set_progress(0.5)
    assert ctx.progress == [0.5]
    assert not ctx.is_canceled

    sink = ctx.create_sink(None)
    assert sink is not None


def test_fake_sink():
    from qgis_sdk.testing import FakeSink, FakeFeature

    sink = FakeSink()
    assert sink.feature_count == 0
    f = FakeFeature(fid=1)
    sink.add_feature(f)
    assert sink.feature_count == 1
    assert list(sink.features())[0].id == 1


def test_mock_features():
    from qgis_sdk.testing import mock_features, mock_source, mock_context

    feats = mock_features(count=5)
    assert len(feats) == 5
    assert feats[0].id == 0

    src = mock_source(feature_count=3)
    assert src.feature_count == 3
    assert len(list(src.features())) == 3

    ctx = mock_context(values={"a": 1})
    assert ctx.get("a") == 1


def test_fake_dialog():
    from qgis_sdk.testing import FakeDialog, FakeDialogWidget

    dlg = FakeDialog(values={"name": "test", "threshold": 0.5})
    assert dlg.exec() == FakeDialog.Accepted
    dlg.reject()
    assert dlg.exec() == FakeDialog.Rejected
    dlg.accept()
    assert dlg.exec() == FakeDialog.Accepted

    w = FakeDialogWidget(value=42, text="42")
    assert w.value() == 42
    assert w.text() == "42"
    w.setText("hello")
    assert w.text() == "hello"


def test_fake_webview():
    from qgis_sdk.testing import FakeWebView, FakeWebPage, FakeWebChannel, FakeBridge

    view = FakeWebView()
    assert view.page() is not None
    view.setHtml("<html>test</html>")
    assert "test" in view.html

    page = FakeWebPage()
    page.runJavaScript("console.log('hi')")
    assert len(page.js_calls) == 1
    assert "console.log" in page.js_calls[0]

    channel = FakeWebChannel()
    bridge = FakeBridge()
    channel.registerObject("bridge", bridge)
    assert "bridge" in channel.objects

    assert bridge.get_layer()["name"] == "test_layer"
    assert bridge.get_extent()["xmin"] == -180
    assert "logged" in bridge.log("hi")


def test_fake_bridge_process():
    from qgis_sdk.testing import FakeBridge
    import json

    b = FakeBridge()
    result = b.process(json.dumps({"action": "buffer"}))
    assert result["action"] == "buffer"
    assert result["status"] == "ok"


def test_pytest_fixtures_via_plugin():
    """Test that fixtures are discoverable via pytest_plugins."""
    # Simulate what pytest does — import testing and check fixtures exist
    import qgis_sdk.testing as testing_module

    assert hasattr(testing_module, "fake_iface")
    assert hasattr(testing_module, "fake_action_factory")
    assert hasattr(testing_module, "fake_context")
    assert hasattr(testing_module, "fake_dialog_factory")
    assert hasattr(testing_module, "fake_webview_factory")
    assert hasattr(testing_module, "fake_bridge")

    # Check Fake classes
    assert hasattr(testing_module, "FakeIface")
    assert hasattr(testing_module, "FakeBridge")
    assert hasattr(testing_module, "FakeDialog")


def test_plugin_with_fake_iface():
    """Integration test: plugin lifecycle with fake iface."""
    from qgis_sdk.testing import FakeIface, fake_action_factory
    from qgis_sdk import Plugin, action, toolbar

    class TestPlugin(Plugin):
        name = "test_plugin"
        version = "0.1.0"

        @toolbar("Test")
        @action(tooltip="Run test")
        def run(self, iface):
            iface.messageBar().pushMessage("run triggered")

    TestPlugin.action_factory = staticmethod(fake_action_factory)

    iface = FakeIface()
    plugin = TestPlugin(iface)
    plugin.init_gui()

    assert len(iface.toolbar_icons) == 1
    assert iface.toolbar_icons[0].tooltip == "Run test"

    # Trigger action
    iface.toolbar_icons[0].trigger()
    assert "run triggered" in iface.messages

    plugin.unload()
    assert len(iface.toolbar_icons) == 0


def test_fixture_usage_as_pytest_plugins():
    """Test conftest.py style usage."""
    # This is what a user would put in conftest.py
    # pytest_plugins = ["qgis_sdk.testing"]
    # Then in tests they can use fake_iface etc.
    # We simulate by checking the module can be imported as plugin

    import importlib

    mod = importlib.import_module("qgis_sdk.testing")
    # Should have pytest_configure
    assert hasattr(mod, "pytest_configure")

    # Should have fixtures defined (they are functions with pytest.fixture decorator)
    # At least check they are callable
    assert callable(mod.FakeIface)
    assert callable(mod.mock_features)
    assert callable(mod.mock_source)
    assert callable(mod.mock_context)
