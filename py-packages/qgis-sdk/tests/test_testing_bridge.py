"""The Python bridge harness, judged by the cross-language fixtures.

``tests/test_bridge_contract.py`` reads `test-fixtures/bridge/` and asserts
the *files* say what the contract says. This suite puts the same files through
:class:`~qgis_sdk.testing.BridgeHarness` and asserts the *router* behaves the
way `.knowledge/bridge-test-contract.md` §2–§5 requires — same vectors, same
stated error kinds as ``crates/qgis-protocol``'s ``validate_request``, no
shared code between the two.

That is the difference AC#5 asks for: the old ``FakeBridge`` exposed four
arbitrary methods and proved nothing about routing, validation, correlation
or permissions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings

from qgis_sdk.testing import (
    BridgeContractError,
    BridgeHarness,
    HostError,
    validate_value,
)
from qgis_sdk.testing import strategies as qst

FIXTURES = Path(__file__).resolve().parents[3] / "test-fixtures" / "bridge"


def read(relative: str) -> Any:
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


CASES = read("cases.json")
SESSION_ID = CASES["session_id"]
MANIFESTS = {entry["target"]: read(entry["file"]) for entry in CASES["descriptions"]}


def answers() -> dict:
    """A handler per covered method, answering the recorded success result."""
    handlers = {}
    for case in CASES["requests"]:
        result = read(case["response"])["result"] if case["response"] else True
        handlers[(case["target"], case["method"])] = lambda args, value=result: value
    return handlers


@pytest.fixture
def harness() -> BridgeHarness:
    return BridgeHarness(
        descriptions=MANIFESTS, handlers=answers(), session_id=SESSION_ID
    )


# ── the happy path ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES["requests"], ids=[c["file"] for c in CASES["requests"]])
def test_every_recorded_request_is_answered_with_its_own_request_id(
    harness: BridgeHarness, case: dict
) -> None:
    request = read(case["file"])

    response = harness.invoke(request)

    assert response["ok"] is True, response
    assert response["request_id"] == request["request_id"]
    assert response["bridge_version"] == 1
    assert "error" not in response
    if case["response"]:
        assert response["result"] == read(case["response"])["result"]


def test_a_request_may_arrive_as_text(harness: BridgeHarness) -> None:
    """A QWebChannel endpoint is handed strings; a host that behaved
    differently for text and objects would be hiding a decode bug."""
    request = read("requests/qgis-layers-list.json")

    decoded = json.loads(harness.invoke_json(json.dumps(request)))

    assert decoded == harness.invoke(request)


def test_the_harness_records_each_call_once(harness: BridgeHarness) -> None:
    harness.invoke(read("requests/qgis-layers-list.json"))
    harness.invoke(read("requests/qgis-layers-add-vector.json"))

    assert harness.calls.paths() == ["qgis.layers.list", "qgis.layers.add_vector"]
    assert harness.calls.assert_called_once("qgis", "layers.add_vector").args["name"] == "Roads"


# ── the refusals, vector by vector ──────────────────────────────────────────


@pytest.mark.parametrize("case", CASES["malformed"], ids=[c["file"] for c in CASES["malformed"]])
def test_every_malformed_vector_is_refused_with_the_kind_the_catalogue_states(
    harness: BridgeHarness, case: dict
) -> None:
    """Parity with the Rust validator, proven on the same files.

    The order of the checks is part of the contract, not an implementation
    detail: a typo'd method on an absent target must be ``unknown_target``,
    because the host cannot know what the method would have meant.
    """
    response = harness.invoke(read(case["file"]))

    assert response["ok"] is False
    assert response["error"]["kind"] == case["error_kind"], case["why"]
    assert response["error"]["message"]
    assert "result" not in response


def test_a_request_whose_id_cannot_be_read_is_answered_without_one(
    harness: BridgeHarness,
) -> None:
    """There is nothing to correlate to, and inventing an id would be a lie."""
    response = harness.invoke(read("malformed/missing-request-id.json"))

    assert response["ok"] is False
    assert "request_id" not in response


def test_text_that_is_not_json_is_an_invalid_request(harness: BridgeHarness) -> None:
    response = harness.invoke("{not json")

    assert response["error"]["kind"] == "invalid_request"


# ── permissions, hosts and handlers ─────────────────────────────────────────


def test_a_revoked_permission_is_refused_before_the_arguments_are_read() -> None:
    harness = BridgeHarness(
        descriptions=MANIFESTS, handlers=answers(), session_id=SESSION_ID, permissions=[]
    )

    response = harness.invoke(read("requests/qgis-layers-list.json"))

    assert response["error"]["kind"] == "permission_denied"
    assert response["error"]["details"]["permission"] == "layer.read"

    harness.grant("layer.read")
    assert harness.invoke(read("requests/qgis-layers-list.json"))["ok"] is True


def test_a_qgis_call_with_no_host_is_host_unavailable_not_a_fake_answer() -> None:
    """The kind that lets a pure suite say "not answerable here" honestly."""
    harness = BridgeHarness(descriptions=MANIFESTS, session_id=SESSION_ID, host_available=False)

    response = harness.invoke(read("requests/qgis-layers-list.json"))

    assert response["error"]["kind"] == "host_unavailable"


def test_an_unhandled_method_in_a_host_that_claims_to_be_there_is_the_tests_own_gap() -> None:
    harness = BridgeHarness(descriptions=MANIFESTS, session_id=SESSION_ID, host_available=True)

    response = harness.invoke(read("requests/qgis-layers-list.json"))

    assert response["error"]["kind"] == "internal_error"
    assert "no handler registered" in response["error"]["message"]


def test_a_handler_may_choose_its_error_kind(harness: BridgeHarness) -> None:
    harness.set_handler(
        "qgis",
        "layers.feature_count",
        lambda args: (_ for _ in ()).throw(HostError("unknown_object", "that layer is gone")),
    )

    response = harness.invoke(read("requests/qgis-layers-feature-count.json"))

    assert response["error"] == {"kind": "unknown_object", "message": "that layer is gone"}


def test_a_handler_that_raises_anything_else_becomes_internal_error(
    harness: BridgeHarness,
) -> None:
    def explode(args):
        raise ZeroDivisionError("division by zero")

    harness.set_handler("qgis", "layers.list", explode)
    response = harness.invoke(read("requests/qgis-layers-list.json"))

    assert response["error"]["kind"] == "internal_error"
    assert response["error"]["details"]["type"] == "ZeroDivisionError"


def test_a_result_the_wire_cannot_carry_is_caught_here_not_at_the_endpoint(
    harness: BridgeHarness,
) -> None:
    """Serialisation is part of the contract: a handler returning a Python
    object the JSON encoder cannot take is a host bug, and the harness has to
    say so rather than raising inside the test's own assert."""
    harness.set_handler("qgis", "layers.list", lambda args: {"layer": object()})

    response = harness.invoke(read("requests/qgis-layers-list.json"))

    assert response["error"]["kind"] == "internal_error"
    assert "cannot carry" in response["error"]["message"]


def test_a_handler_for_a_method_no_manifest_declares_is_refused(
    harness: BridgeHarness,
) -> None:
    """§5: the manifest is the single source of methods. A handler for an
    undeclared method is the second spelling table the contract forbids."""
    with pytest.raises(BridgeContractError, match="no method layers.teleport"):
        harness.set_handler("qgis", "layers.teleport", lambda args: None)


def test_a_decorator_registers_a_handler(harness: BridgeHarness) -> None:
    @harness.handle("qgis", "layers.feature_count")
    def count(args):
        return 12

    assert harness.invoke(read("requests/qgis-layers-feature-count.json"))["result"] == 12


# ── events ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES["events"], ids=[c["file"] for c in CASES["events"]])
def test_a_recorded_event_can_be_replayed_through_the_harness(case: dict) -> None:
    harness = BridgeHarness(descriptions=MANIFESTS, session_id=SESSION_ID)
    recorded = read(case["file"])
    seen: list[dict] = []
    harness.on_event(seen.append)

    emitted = harness.emit(
        case["target"],
        case["event"],
        recorded["payload"],
        request_id=recorded.get("request_id"),
    )

    assert emitted == recorded
    assert seen == [recorded]
    assert "ok" not in emitted, "an event is announced, not answered"
    assert ("request_id" in emitted) is case["correlated"]


def test_unsubscribing_stops_the_listener_hearing_events() -> None:
    harness = BridgeHarness(descriptions=MANIFESTS, session_id=SESSION_ID)
    seen: list[dict] = []
    unsubscribe = harness.on_event(seen.append)

    harness.emit("ui", "theme.changed", {"theme": "dark"})
    unsubscribe()
    harness.emit("ui", "theme.changed", {"theme": "light"})

    assert [event["payload"]["theme"] for event in seen] == ["dark"]
    assert len(harness.events) == 2


def test_an_undeclared_event_is_a_broken_test_not_an_error_envelope() -> None:
    harness = BridgeHarness(descriptions=MANIFESTS, session_id=SESSION_ID)

    with pytest.raises(BridgeContractError, match="declares no event"):
        harness.emit("ui", "dialog.exploded", {})


def test_an_event_payload_is_validated_against_its_manifest() -> None:
    harness = BridgeHarness(descriptions=MANIFESTS, session_id=SESSION_ID)

    with pytest.raises(BridgeContractError, match="payload"):
        harness.emit("qgis", "task.progress", {"task_id": "task-3"})


# ── properties ──────────────────────────────────────────────────────────────


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(request=qst.bridge_requests(MANIFESTS["engine"], session_id=SESSION_ID))
def test_any_well_formed_request_is_answered_with_the_id_it_carried(request: dict) -> None:
    """Request ids are opaque and echoed — the property every client relies on."""
    harness = BridgeHarness(
        descriptions=MANIFESTS,
        handlers={
            ("engine", method["name"]): (lambda args: None)
            for method in MANIFESTS["engine"]["methods"]
        },
        session_id=SESSION_ID,
    )

    response = harness.invoke(request)

    assert response["ok"] is True, response
    assert response["request_id"] == request["request_id"]


@settings(max_examples=50, deadline=None)
@given(request=qst.bridge_requests(MANIFESTS["qgis"], session_id=SESSION_ID))
def test_generated_arguments_satisfy_the_schema_that_generated_them(request: dict) -> None:
    """The strategy and the validator are inverses; this is where they meet."""
    spec = next(
        method
        for method in MANIFESTS["qgis"]["methods"]
        if method["name"] == request["method"]
    )

    assert validate_value(spec["args"], request["args"], SESSION_ID) is None


@settings(max_examples=50, deadline=None)
@given(request_id=qst.request_ids())
def test_an_unknown_method_fails_predictably_whatever_the_id(request_id: str) -> None:
    harness = BridgeHarness(descriptions=MANIFESTS, session_id=SESSION_ID)

    response = harness.invoke(
        {
            "bridge_version": 1,
            "request_id": request_id,
            "target": "qgis",
            "method": "layers.teleport",
            "args": {},
        }
    )

    assert response["error"]["kind"] == "unknown_method"
    assert response["request_id"] == request_id


@settings(max_examples=50, deadline=None)
@given(handle=qst.object_handles("qgis.layer", session_id="another-session"))
def test_a_handle_from_another_session_is_unknown_whatever_its_id(handle: dict) -> None:
    harness = BridgeHarness(descriptions=MANIFESTS, session_id=SESSION_ID)

    response = harness.invoke(
        {
            "bridge_version": 1,
            "request_id": "req-1",
            "target": "qgis",
            "method": "layers.feature_count",
            "args": {"handle": handle},
        }
    )

    assert response["error"]["kind"] == "unknown_object"
