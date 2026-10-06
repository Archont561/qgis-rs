"""The shared call recorder, and the fakes that record through it.

What this suite is really asserting is that there is now *one* answer to "was
this called, with what" — a question that previously had a different answer
per fake (``iface.messages``, ``manager.requests``, ``added_tasks``, and
nothing at all for the bridge).
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from qgis_sdk.testing import (
    Call,
    CallLog,
    FakeIface,
    FakeNetworkTransport,
    FakeTaskManager,
    FakeDialog,
)


def test_a_call_is_a_target_a_method_and_named_arguments() -> None:
    call = Call(target="qgis", method="layers.add_vector", args={"uri": "/roads.gpkg"})

    assert call.path == "qgis.layers.add_vector"
    assert call.matches("qgis", "layers.add_vector")
    assert call.matches(method="layers.add_vector", uri="/roads.gpkg")
    assert not call.matches("engine", "layers.add_vector")


def test_arguments_match_as_a_subset() -> None:
    """A test names the arguments it cares about, not every argument there is.

    The alternative — exact matching — makes every assertion fail the day an
    unrelated argument is added, which trains people to stop asserting.
    """
    call = Call("qgis", "layers.add_vector", {"uri": "/roads.gpkg", "name": "Roads"})

    assert call.matches(uri="/roads.gpkg")
    assert not call.matches(uri="/rivers.gpkg")


def test_the_log_keeps_order_and_can_be_queried_three_ways() -> None:
    log = CallLog()
    log.record("iface", "message.push", text="one")
    log.record("network", "get", url="https://example.test")
    log.record("iface", "message.push", text="two")

    assert log.paths() == ["iface.message.push", "network.get", "iface.message.push"]
    assert len(log.for_target("iface")) == 2
    assert len(log.for_method("message.push", target="iface")) == 2
    assert len(log.for_method("iface.message.push")) == 2
    assert log.last().args["text"] == "two"


def test_assertions_name_what_was_recorded_when_they_fail() -> None:
    """A failed call assertion has to print the calls, or it is a guessing game."""
    log = CallLog()
    log.record("iface", "message.push", text="hello")

    log.assert_called_once("iface", "message.push", text="hello")
    log.assert_not_called("iface", "message.push", text="goodbye")

    with pytest.raises(AssertionError) as failure:
        log.assert_called_once("iface", "toolbar.add")
    assert "iface.message.push" in str(failure.value)
    assert "{'text': 'hello'}" in str(failure.value)

    with pytest.raises(AssertionError, match="nothing was recorded"):
        CallLog().assert_called("iface", "toolbar.add")


def test_one_log_reads_several_fakes_in_the_order_things_happened() -> None:
    """The point of a shared recorder: cross-fake ordering becomes assertable.

    A plugin that posts a message *after* its request came back is a different
    plugin from one that posts it before, and no per-fake list can tell them
    apart.
    """
    calls = CallLog()
    iface = FakeIface(calls=calls)
    transport = FakeNetworkTransport(calls=calls)
    tasks = FakeTaskManager(calls=calls)
    dialog = FakeDialog(values={"name": "Roads"}, calls=calls)

    transport.reply("GET", "https://example.test/layers", json_data={"layers": []})

    dialog.accept()
    transport.get("https://example.test/layers")
    tasks.submit(lambda: 42, description="count")
    iface.pushMessage("done")

    assert calls.paths() == [
        "ui.dialog.accept",
        "network.get",
        "tasks.submit",
        "iface.message.push",
    ]
    assert calls.assert_called_once("network", "get").args["url"].endswith("/layers")


def test_the_old_per_fake_lists_still_exist() -> None:
    """AC#1: recording through a CallLog is an addition, not a replacement."""
    iface = FakeIface()
    iface.pushMessage("hello")

    assert iface.messages == ["hello"]
    assert iface.calls.assert_called_once("iface", "message.push").args["text"] == "hello"


def test_reset_clears_the_log_without_replacing_it() -> None:
    iface = FakeIface()
    log = iface.calls
    iface.pushMessage("hello")
    log.reset()

    assert len(log) == 0
    iface.pushMessage("again")
    assert iface.calls is log
    assert len(log) == 1


@settings(max_examples=50, deadline=None)
@given(
    messages=st.lists(st.text(min_size=1, max_size=12), min_size=1, max_size=8),
)
def test_every_recorded_call_is_findable_by_its_arguments(messages: list[str]) -> None:
    """The recorder's one invariant: what went in can be asked for by name."""
    iface = FakeIface()
    for message in messages:
        iface.pushMessage(message)

    assert len(iface.calls) == len(messages)
    for message in messages:
        assert iface.calls.assert_called("iface", "message.push", text=message)
