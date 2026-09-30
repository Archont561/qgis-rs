"""Focused coverage for the declarative SDK APIs."""

from __future__ import annotations

import qgis_sdk.network as network
import qgis_sdk.tasks as tasks
from qgis_sdk.algorithm import Algorithm, algorithm, algorithm_registry, output, parameter
from qgis_sdk.network import NetworkResponse
from qgis_sdk.plugin import Plugin, action, plugin, toolbar


def test_algorithm_decorator_registers_metadata_and_preserves_execution():
    algorithm_id = "tests:decorated_buffer"

    @algorithm(id=algorithm_id, name="Decorated buffer", group="Vector")
    class DecoratedBuffer(Algorithm):
        distance = parameter.number("Distance", default=2.5)
        result = output.sink("Result")

        def process(self, context):
            return {"result": context["distance"]}

    assert algorithm_registry.get(algorithm_id) is DecoratedBuffer
    spec = next(item for item in algorithm_registry.all() if item.id == algorithm_id)
    assert spec.name == "Decorated buffer"
    assert spec.group == "Vector"
    assert DecoratedBuffer.defaults() == {"distance": 2.5}
    assert DecoratedBuffer().run({"distance": 3}) == {"result": 3}


def test_standalone_plugin_decorator_wires_actions_and_preserves_plugin_subclasses():
    class Iface:
        def __init__(self):
            self.toolbar_icons = []

        def addToolBarIcon(self, widget):
            self.toolbar_icons.append(widget)

        def removeToolBarIcon(self, widget):
            self.toolbar_icons.remove(widget)

    class FakeAction:
        def __init__(self, callback):
            self.callback = callback

        def trigger(self):
            self.callback()

    @plugin(name="Standalone test plugin")
    class Standalone:
        action_factory = staticmethod(lambda spec, callback: FakeAction(callback))

        @toolbar("Tests")
        @action(tooltip="Run")
        def run(self, iface):
            iface.called = True

    iface = Iface()
    instance = Standalone(iface)
    instance.init_gui()
    assert len(iface.toolbar_icons) == 1
    iface.toolbar_icons[0].trigger()
    assert iface.called is True
    instance.unload()
    assert iface.toolbar_icons == []

    @plugin(name="Custom init test plugin")
    class CustomInit:
        action_factory = staticmethod(lambda spec, callback: FakeAction(callback))

        def __init__(self, iface):
            self.custom_state = True
            self.iface = iface

        @toolbar("Tests")
        @action(tooltip="Run")
        def run(self, iface):
            iface.called_again = True

    custom = CustomInit(iface)
    custom.init_gui()
    assert custom.custom_state is True
    custom.unload()

    class Existing(Plugin):
        initialized = False

        def __init__(self, iface=None):
            super().__init__(iface)
            self.initialized = True

    Existing = plugin(name="Existing test plugin", version="2.0")(Existing)
    existing = Existing(iface)
    assert Existing.name == "Existing test plugin"
    assert Existing.version == "2.0"
    assert existing.initialized is True
    assert existing.iface is iface


def test_plugin_algorithm_metadata_registers_processing_provider(monkeypatch):
    import qgis_sdk.processing_bridge as bridge

    events = []
    monkeypatch.setattr(bridge, "build_provider", lambda algorithms, **kwargs: (list(algorithms), kwargs))
    monkeypatch.setattr(bridge, "register_provider", lambda provider: events.append(("register", provider)) or True)
    monkeypatch.setattr(bridge, "unregister_provider", lambda provider: events.append(("unregister", provider)) or True)

    @algorithm(id="tests:provider_algorithm", name="Provider algorithm")
    class ProviderAlgorithm(Algorithm):
        def process(self, context):
            return {}

    class Iface:
        pass

    @plugin(name="Processing test plugin", algorithms=[ProviderAlgorithm])
    class ProcessingPlugin:
        pass

    instance = ProcessingPlugin(Iface())
    instance.init_gui()
    assert events[0][0] == "register"
    instance.unload()
    assert events[-1][0] == "unregister"


def test_session_and_http_decorators_build_reusable_requests(monkeypatch):
    monkeypatch.setattr(network, "_get_qgis_network_manager", lambda: None)

    @network.session(base_url="https://api.example", headers={"X-Test": "1"})
    class Client:
        @network.http.get("/items/{item_id}")
        def item(self, item_id):
            raise AssertionError("the endpoint body is not needed for a request")

        @network.http.post("/items", response_handler=True)
        def create(self, response):
            return response.json()

    client = Client()
    calls = []

    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return NetworkResponse(url=url, content=b'{"created": true}')

    client.session.request = request
    response = client.item(7)
    assert response.url == "https://api.example/items/7"
    assert client.create() == {"created": True}
    assert calls[0][0:2] == ("GET", "https://api.example/items/7")
    assert client.session.headers == {"X-Test": "1"}


def test_session_retries_transient_statuses_and_keeps_history(monkeypatch):
    monkeypatch.setattr(network, "_get_qgis_network_manager", lambda: None)

    class Manager:
        def __init__(self):
            self.calls = 0

        def request(self, url, **kwargs):
            self.calls += 1
            status = 503 if self.calls < 3 else 200
            return NetworkResponse(url=url, status_code=status)

    manager = Manager()
    monkeypatch.setattr(
        network.NetworkManager,
        "instance",
        classmethod(lambda cls, **kwargs: manager),
    )

    response = network.Session(retries=2).get("https://example.test")
    assert manager.calls == 3
    assert response.ok
    assert [item.status_code for item in response.history] == [503, 503]


def test_task_signatures_support_fluent_then_and_group_aggregates(monkeypatch):
    @tasks.task
    def add(value, increment=0):
        return value + increment

    @tasks.task
    def double(value):
        return value * 2

    @tasks.task
    def seed():
        return 5

    assert add.s(2, 3).then(double)() == 10
    assert seed.then(double)() == 10
    assert tasks.chain(add.s(2, 3)).then(double)() == 10

    class Result:
        def __init__(self, value):
            self.value = value
            self.revoked = False

        def get(self, **kwargs):
            return self.value

        def ready(self):
            return True

        def successful(self):
            return True

        def failed(self):
            return False

        def revoke(self, **kwargs):
            self.revoked = True

    values = tasks.GroupResult([Result(1), Result(2)])
    assert values.get() == [1, 2]
    assert values.ready() and values.successful() and not values.failed()
    values.revoke()
    assert all(item.revoked for item in values)
