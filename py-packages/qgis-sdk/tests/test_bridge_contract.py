"""The cross-language bridge contract, read from the shared fixture tree.

Pure Python: no QGIS, no Qt, no bridge runtime. What this suite owns is the
host's half of the contract in `.knowledge/bridge-test-contract.md` — the rules
a `BridgeRouter` has to honour before it ever calls a handler: request-id
correlation, the `ok`/`result`/`error` split, the closed error-kind set,
snake_case wire names, and handles that are opaque and session-scoped.

The files come from `test-fixtures/bridge/`, the same ones the Rust suite
(`crates/qgis-protocol/tests/bridge_contract.rs`) and the TypeScript suite
(`ts-packages/qgis-sdk-bridge/tests/bridge-contract.test.ts`) read. What the
three share is the observable contract and nothing else: no fake implementation
class crosses a language boundary here, because two sides that agree by being
the same code have not agreed about anything.

`cases.json` is the only list of files, so a vector added there is checked by
this suite with no edit to it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st

FIXTURES = Path(__file__).resolve().parents[3] / "test-fixtures" / "bridge"
BRIDGE_VERSION = 1

SNAKE_CASE_DOTTED = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")


def read(relative: str) -> Any:
    return json.loads((FIXTURES / relative).read_text(encoding="utf-8"))


CASES = read("cases.json")
SESSION_ID = CASES["session_id"]
MANIFESTS = {
    entry["target"]: read(entry["file"]) for entry in CASES["descriptions"]
}


def method_spec(target: str, name: str) -> dict[str, Any] | None:
    for method in MANIFESTS[target]["methods"]:
        if method["name"] == name:
            return method
    return None


def ids(cases: list[dict[str, Any]]) -> list[str]:
    return [case["file"] for case in cases]


# ── the manifest is the single source of methods ────────────────────────────


def test_the_catalogue_describes_all_four_call_kinds() -> None:
    kinds = {manifest["kind"] for manifest in MANIFESTS.values()}
    assert kinds == set(CASES["call_kinds"]), (
        "engine, qgis host, plugin and ui calls are four different things to a "
        "test, and each needs a manifest to be told apart"
    )


@pytest.mark.parametrize("target", sorted(MANIFESTS))
def test_every_manifest_entry_is_snake_case_and_unique(target: str) -> None:
    manifest = MANIFESTS[target]
    assert manifest["bridge_version"] == BRIDGE_VERSION
    assert SNAKE_CASE_DOTTED.match(target)

    names = [method["name"] for method in manifest["methods"]]
    assert len(names) == len(set(names)), f"{target} lists a method twice"
    for name in names:
        assert SNAKE_CASE_DOTTED.match(name), f"{target}.{name} is not snake_case"
    for event in manifest.get("events", []):
        assert SNAKE_CASE_DOTTED.match(event["name"])


@pytest.mark.parametrize("target", sorted(MANIFESTS))
def test_each_method_declares_the_kind_its_target_promises(target: str) -> None:
    manifest = MANIFESTS[target]
    for method in manifest["methods"]:
        assert method["call_kind"] == manifest["kind"]
        # Permissions are a list even when empty: a router reads it, it does not
        # ask whether the key is there.
        assert isinstance(method["permissions"], list)


# ── envelopes ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES["requests"], ids=ids(CASES["requests"]))
def test_every_listed_request_names_a_method_its_target_has(case: dict[str, Any]) -> None:
    request = read(case["file"])

    assert request["bridge_version"] == BRIDGE_VERSION
    assert request["request_id"], "a request without an id cannot be answered"
    assert request["target"] == case["target"]
    assert request["method"] == case["method"]
    assert isinstance(request["args"], dict), "args is an object, never positional"
    assert method_spec(case["target"], case["method"]) is not None


@pytest.mark.parametrize("case", CASES["responses"], ids=ids(CASES["responses"]))
def test_ok_decides_which_field_is_present(case: dict[str, Any]) -> None:
    response = read(case["file"])

    assert response["bridge_version"] == BRIDGE_VERSION
    assert response["ok"] is case["ok"]
    assert response["request_id"] == case["request_id"]

    if response["ok"]:
        assert "result" in response
        assert "error" not in response
    else:
        assert "error" in response
        assert "result" not in response
        error = response["error"]
        assert error["kind"] == case["error_kind"]
        assert error["kind"] in CASES["error_kinds"], "the kind set is closed"
        assert error["message"], "a failure a human cannot read is half an answer"


@pytest.mark.parametrize("case", CASES["requests"], ids=ids(CASES["requests"]))
def test_a_success_carries_the_request_id_it_answers(case: dict[str, Any]) -> None:
    if case["response"] is None:
        pytest.skip("this request has no recorded answer")

    request = read(case["file"])
    response = read(case["response"])
    assert response["request_id"] == request["request_id"]


@pytest.mark.parametrize("case", CASES["events"], ids=ids(CASES["events"]))
def test_an_event_is_not_a_response(case: dict[str, Any]) -> None:
    event = read(case["file"])

    assert "ok" not in event, "an event is announced, not answered"
    assert "result" not in event
    assert event["event"] == case["event"]
    assert event["target"] == case["target"]
    assert ("request_id" in event) is case["correlated"], (
        "an event correlates only when it belongs to a call in flight"
    )

    declared = {entry["name"] for entry in MANIFESTS[case["target"]]["events"]}
    assert event["event"] in declared


# ── refusals ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("case", CASES["malformed"], ids=ids(CASES["malformed"]))
def test_every_malformed_vector_is_refused_for_a_reason_a_router_can_reach(
    case: dict[str, Any],
) -> None:
    """The kinds themselves are proven by the Rust validator; what this asserts
    is that each vector really is the thing its catalogue entry claims, so the
    three languages are refusing the same input for the same stated reason."""
    envelope = read(case["file"])
    kind = case["error_kind"]
    assert kind in CASES["error_kinds"]
    assert case["why"], "a refusal without a reason is a rule nobody can apply"

    if kind == "invalid_request":
        broken = (
            "request_id" not in envelope
            or envelope["bridge_version"] != BRIDGE_VERSION
            or not isinstance(envelope.get("args"), dict)
        )
        assert broken, f"{case['file']} looks well-formed"
        return

    if kind == "unknown_target":
        assert envelope["target"] not in MANIFESTS
        return

    spec = method_spec(envelope["target"], envelope["method"])
    if kind == "unknown_method":
        assert spec is None
        return

    assert spec is not None, f"{case['file']} must name a real method"
    schema = spec["args"]

    if kind == "invalid_arguments":
        assert _violates(schema, envelope["args"]), f"{case['file']} satisfies its schema"
    elif kind == "unknown_object":
        assert _has_foreign_handle(schema, envelope["args"])
    else:  # pragma: no cover - a kind no malformed vector uses yet
        pytest.fail(f"unexpected kind {kind}")


def _violates(schema: dict[str, Any], args: dict[str, Any]) -> bool:
    properties = schema.get("properties", {})
    if any(name not in args for name in schema.get("required", [])):
        return True
    if schema.get("additional_properties") is False and any(
        name not in properties for name in args
    ):
        return True
    for name, value in args.items():
        member = properties.get(name)
        if member is None or "$handle" in member:
            continue
        if "enum" in member and value not in member["enum"]:
            return True
        if not _is_type(member.get("type"), value):
            return True
    return False


def _is_type(type_name: str | None, value: Any) -> bool:
    if type_name is None:
        return True
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "object":
        return isinstance(value, dict)
    if type_name == "array":
        return isinstance(value, list)
    return True


def _has_foreign_handle(schema: dict[str, Any], args: dict[str, Any]) -> bool:
    for name, member in schema.get("properties", {}).items():
        expected = member.get("$handle")
        handle = args.get(name)
        if expected is None or not isinstance(handle, dict):
            continue
        if handle["object_type"] != expected or handle["session_id"] != SESSION_ID:
            return True
    return False


# ── handles ─────────────────────────────────────────────────────────────────


def test_a_handle_carries_its_type_and_its_session() -> None:
    listed = read("responses/qgis-layers-list-success.json")["result"]
    handle = listed[0]["handle"]

    assert set(handle) == {"object_id", "object_type", "session_id"}
    assert handle["session_id"] == SESSION_ID
    assert SNAKE_CASE_DOTTED.match(handle["object_type"])


@given(
    object_id=st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        min_size=1,
        max_size=24,
    )
)
@settings(max_examples=50)
def test_nothing_in_the_contract_reads_inside_an_object_id(object_id: str) -> None:
    """Opacity, stated as the only property that can be tested: identity is the
    whole of a handle's meaning, so any id at all works as long as it is echoed
    unchanged within one session."""
    handle = {
        "object_id": object_id,
        "object_type": "qgis.layer",
        "session_id": SESSION_ID,
    }
    round_tripped = json.loads(json.dumps(handle))

    assert round_tripped == handle
    assert round_tripped["object_id"] == object_id
