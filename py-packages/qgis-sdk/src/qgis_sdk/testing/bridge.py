"""The bridge seam, tested as a protocol rather than as a bag of methods.

:class:`BridgeHarness` is a host-side router: it takes the same manifests the
cross-language fixtures use, validates a request envelope against them, calls
a handler, and answers with a response envelope. It is the Python half of what
``createBridgeHarness`` is in ``@qgis/test-utils`` — same contract, no shared
code, which is the rule in `.knowledge/bridge-test-contract.md` §7.

The checks happen in the order a host must make them — envelope, version,
target, method, permissions, arguments — because the order *is* part of the
contract: a typo'd method on an absent target is ``unknown_target``, since the
host cannot know what the method would have meant. ``crates/qgis-protocol``'s
``validate_request`` makes the same moves in the same order, and
``tests/test_testing_bridge.py`` replays the shared malformed vectors through
this harness to prove the two agree.

:class:`FakeBridge` is the older toy object (``get_layer``, ``log``, …) that
``fake_bridge`` still hands out; it is kept for compatibility, and new tests
should route through the harness instead.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple

from .calls import CallLog, call_log

#: Version 1 of the bridge wire — the only one this harness speaks.
BRIDGE_VERSION = 1

#: The closed set of error kinds, from the contract's §3.
ERROR_KINDS = (
    "invalid_request",
    "unknown_target",
    "unknown_method",
    "invalid_arguments",
    "permission_denied",
    "unknown_object",
    "host_unavailable",
    "internal_error",
)


class BridgeContractError(AssertionError):
    """Raised when a *test* misuses the harness — not when a request fails.

    A malformed request is answered with an error envelope, because that is
    what a host does. Handing the harness a manifest it cannot read, or
    emitting an event no manifest declares, is a broken test instead.
    """


class HostError(Exception):
    """Raise this from a handler to answer with a chosen error kind.

    Anything else a handler raises becomes ``internal_error``; this is how a
    handler says "the thing you asked for is not here" in the contract's own
    vocabulary.
    """

    def __init__(
        self, kind: str, message: str, details: Optional[Mapping[str, Any]] = None
    ) -> None:
        if kind not in ERROR_KINDS:
            raise BridgeContractError(f"{kind} is not one of {ERROR_KINDS}")
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.details = details


class BridgeHarness:
    """A protocol-faithful bridge host for tests.

    ::

        harness = BridgeHarness(
            descriptions={"qgis": qgis_manifest},
            handlers={("qgis", "layers.list"): lambda args: []},
        )
        response = harness.invoke(
            {
                "bridge_version": 1,
                "request_id": "req-1",
                "target": "qgis",
                "method": "layers.list",
                "args": {},
            }
        )
        assert response["ok"] and response["request_id"] == "req-1"

    ``permissions=None`` grants everything the manifests declare, so a test
    that is not about permissions does not have to enumerate them; pass an
    explicit collection to make ``permission_denied`` reachable.
    """

    def __init__(
        self,
        descriptions: Mapping[str, Mapping[str, Any]],
        handlers: Optional[Mapping[Tuple[str, str], Callable[[Mapping[str, Any]], Any]]] = None,
        session_id: str = "sess-1",
        permissions: Optional[Iterable[str]] = None,
        calls: Optional[CallLog] = None,
        host_available: bool = True,
    ):
        self.descriptions: Dict[str, Mapping[str, Any]] = dict(descriptions)
        for target, manifest in self.descriptions.items():
            if "methods" not in manifest:
                raise BridgeContractError(f"the manifest for {target} lists no methods")
        self.handlers: Dict[Tuple[str, str], Callable[[Mapping[str, Any]], Any]] = dict(
            handlers or {}
        )
        self.session_id = session_id
        self.granted = (
            self._declared_permissions() if permissions is None else set(permissions)
        )
        self.calls = call_log(calls)
        #: Whether a ``qgis_host`` method with no handler can be answered at
        #: all. False is how a pure test states "QGIS is not here".
        self.host_available = host_available
        #: Every event emitted, newest last.
        self.events: List[Dict[str, Any]] = []
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    # ── wiring ──────────────────────────────────────────────────────────────

    def handle(self, target: str, method: str) -> Callable:
        """Register a handler with a decorator: ``@harness.handle("qgis", …)``."""

        def register(function: Callable[[Mapping[str, Any]], Any]):
            self.set_handler(target, method, function)
            return function

        return register

    def set_handler(
        self, target: str, method: str, function: Callable[[Mapping[str, Any]], Any]
    ) -> None:
        """Register (or replace) the handler for one method.

        The method has to exist in the manifest: a handler for a method no
        manifest declares is a second spelling table, which §5 of the contract
        exists to prevent.
        """
        if self.method_spec(target, method) is None:
            raise BridgeContractError(f"{target} has no method {method} in its manifest")
        self.handlers[(target, method)] = function

    def grant(self, *permissions: str) -> None:
        """Add permissions to the calling plugin's set."""
        self.granted.update(permissions)

    def revoke(self, *permissions: str) -> None:
        """Remove permissions, making ``permission_denied`` reachable."""
        self.granted.difference_update(permissions)

    def reset(self) -> None:
        """Forget recorded calls and emitted events; keep the wiring."""
        self.calls.reset()
        self.events.clear()

    # ── manifests ───────────────────────────────────────────────────────────

    def method_spec(self, target: str, method: str) -> Optional[Mapping[str, Any]]:
        """The manifest entry for one method, or ``None``."""
        manifest = self.descriptions.get(target)
        if manifest is None:
            return None
        for entry in manifest.get("methods", []):
            if entry.get("name") == method:
                return entry
        return None

    def methods(self, target: str) -> List[str]:
        """Every method one target declares, in manifest order."""
        manifest = self.descriptions.get(target)
        if manifest is None:
            raise BridgeContractError(f"no manifest for {target}")
        return [entry["name"] for entry in manifest.get("methods", [])]

    def handle_for(self, object_type: str, object_id: str) -> Dict[str, str]:
        """Mint an object handle in this harness's session."""
        return {
            "object_id": object_id,
            "object_type": object_type,
            "session_id": self.session_id,
        }

    def _declared_permissions(self) -> set:
        declared = set()
        for manifest in self.descriptions.values():
            for entry in manifest.get("methods", []):
                declared.update(entry.get("permissions", []))
        return declared

    # ── invoking ────────────────────────────────────────────────────────────

    def invoke(self, request: Any) -> Dict[str, Any]:
        """Answer one request envelope — always with a response envelope.

        ``request`` may be a dict or the JSON text of one, because the wire
        carries text and a QWebChannel endpoint carries objects, and a host
        that behaved differently for the two would be hiding a decode bug.
        """
        envelope, decode_error = _as_envelope(request)
        if decode_error is not None:
            return self._failure(None, "invalid_request", decode_error)

        request_id = envelope.get("request_id")
        envelope_error = _check_envelope(envelope)
        if envelope_error is not None:
            return self._failure(
                request_id if isinstance(request_id, str) else None,
                "invalid_request",
                envelope_error,
            )

        target = envelope["target"]
        method = envelope["method"]
        args = envelope["args"]
        self.calls.record(target, method, **args)

        if target not in self.descriptions:
            return self._failure(
                request_id, "unknown_target", f"no bridge object named {target}",
                {"target": target},
            )

        spec = self.method_spec(target, method)
        if spec is None:
            return self._failure(
                request_id, "unknown_method", f"{target} has no method {method}",
                {"target": target, "method": method},
            )

        missing = [p for p in spec.get("permissions", []) if p not in self.granted]
        if missing:
            return self._failure(
                request_id, "permission_denied", f"{method} needs {missing[0]}",
                {"target": target, "method": method, "permission": missing[0]},
            )

        violation = validate_value(spec.get("args", {}), args, self.session_id)
        if violation is not None:
            kind, reason = violation
            return self._failure(request_id, kind, reason, {"target": target, "method": method})

        handler = self.handlers.get((target, method))
        if handler is None:
            kind, reason = self._unanswerable(target, method)
            return self._failure(request_id, kind, reason, {"target": target, "method": method})

        try:
            result = handler(args)
        except HostError as error:
            return self._failure(request_id, error.kind, error.message, error.details)
        except Exception as error:  # noqa: BLE001 - a handler failure is an answer here
            return self._failure(
                request_id, "internal_error", str(error) or type(error).__name__,
                {"type": type(error).__name__},
            )

        try:
            json.dumps(result)
        except (TypeError, ValueError) as error:
            return self._failure(
                request_id,
                "internal_error",
                f"{target}.{method} returned something the wire cannot carry: {error}",
                {"type": type(result).__name__},
            )

        return {
            "bridge_version": BRIDGE_VERSION,
            "request_id": request_id,
            "ok": True,
            "result": result,
        }

    def invoke_json(self, request: str) -> str:
        """``invoke`` over text, the shape a QWebChannel endpoint really sees."""
        return json.dumps(self.invoke(request))

    def _unanswerable(self, target: str, method: str) -> Tuple[str, str]:
        """Which kind an unhandled method answers with.

        A ``qgis_host`` call with no handler in a process with no QGIS is
        ``host_unavailable`` — the kind that keeps a missing environment from
        looking like a plugin bug. Anything else is the test's own omission,
        and says so.
        """
        kind = self.descriptions[target].get("kind")
        if kind == "qgis_host" and not self.host_available:
            return "host_unavailable", f"{target}.{method} needs a live QGIS"
        return "internal_error", f"no handler registered for {target}.{method}"

    def _failure(
        self,
        request_id: Optional[str],
        kind: str,
        message: str,
        details: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        if kind not in ERROR_KINDS:  # pragma: no cover - guarded at construction
            raise BridgeContractError(f"{kind} is not one of {ERROR_KINDS}")
        error: Dict[str, Any] = {"kind": kind, "message": message}
        if details:
            error["details"] = dict(details)
        envelope: Dict[str, Any] = {
            "bridge_version": BRIDGE_VERSION,
            "ok": False,
            "error": error,
        }
        # A request whose id could not be read is answered without one; there
        # is nothing to correlate to, and inventing an id would be a lie.
        if request_id is not None:
            envelope["request_id"] = request_id
        return envelope

    # ── events ──────────────────────────────────────────────────────────────

    def emit(
        self,
        target: str,
        event: str,
        payload: Optional[Mapping[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Emit one event envelope, validated against the target's manifest."""
        manifest = self.descriptions.get(target)
        if manifest is None:
            raise BridgeContractError(f"no manifest for {target}")
        declared = {entry["name"]: entry for entry in manifest.get("events", [])}
        if event not in declared:
            raise BridgeContractError(f"{target} declares no event {event}")

        body = dict(payload or {})
        violation = validate_value(declared[event].get("payload", {}), body, self.session_id)
        if violation is not None:
            raise BridgeContractError(f"{target}.{event} payload: {violation[1]}")

        envelope: Dict[str, Any] = {
            "bridge_version": BRIDGE_VERSION,
            "event": event,
            "target": target,
            "payload": body,
        }
        if request_id is not None:
            envelope["request_id"] = request_id
        self.events.append(envelope)
        for listener in list(self._listeners):
            listener(envelope)
        return envelope

    def on_event(self, listener: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        """Subscribe to emitted events; returns the unsubscribe callable."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe


# ── the schema subset ───────────────────────────────────────────────────────
#
# `type`, `properties`, `required`, `items`, `enum`, `additional_properties`
# and `$handle` — no more, by §5 of the contract: three languages have to
# agree on it offline.


def validate_value(
    schema: Mapping[str, Any], value: Any, session_id: str
) -> Optional[Tuple[str, str]]:
    """Check one value against the subset schema.

    Returns ``None`` when it fits, else ``(error_kind, reason)``. A handle
    that fails is ``unknown_object`` — the arguments were shaped right and the
    object was not there — while everything else is ``invalid_arguments``.
    """
    if not schema:
        return None

    if "$handle" in schema:
        return _validate_handle(value, schema["$handle"], session_id)

    if "enum" in schema and value not in schema["enum"]:
        return "invalid_arguments", f"{value!r} is not one of {schema['enum']}"

    type_name = schema.get("type")
    if type_name is None:
        return None

    if type_name == "object":
        if not isinstance(value, dict):
            return "invalid_arguments", f"expected object, got {type(value).__name__}"
        return _validate_object(schema, value, session_id)

    if type_name == "array":
        if not isinstance(value, list):
            return "invalid_arguments", f"expected array, got {type(value).__name__}"
        items = schema.get("items")
        if not items:
            return None
        for element in value:
            violation = validate_value(items, element, session_id)
            if violation is not None:
                return violation
        return None

    if not _is_scalar(type_name, value):
        return "invalid_arguments", f"expected {type_name}, got {type(value).__name__}"
    return None


def _validate_object(
    schema: Mapping[str, Any], members: Mapping[str, Any], session_id: str
) -> Optional[Tuple[str, str]]:
    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in members:
            return "invalid_arguments", f"missing required member {name}"

    for name, member in members.items():
        child = properties.get(name)
        if child is None:
            if schema.get("additional_properties") is False:
                return "invalid_arguments", f"unexpected member {name}"
            continue
        violation = validate_value(child, member, session_id)
        if violation is not None:
            return violation
    return None


def _validate_handle(
    value: Any, handle_type: str, session_id: str
) -> Optional[Tuple[str, str]]:
    if not isinstance(value, dict) or not {
        "object_id",
        "object_type",
        "session_id",
    } <= set(value):
        return "invalid_arguments", f"expected an object handle, got {value!r}"
    if value["object_type"] != handle_type:
        return (
            "unknown_object",
            f"{value['object_id']} is a {value['object_type']}, not a {handle_type}",
        )
    if value["session_id"] != session_id:
        return (
            "unknown_object",
            f"{value['object_id']} belongs to {value['session_id']}, not to {session_id}",
        )
    return None


def _is_scalar(type_name: str, value: Any) -> bool:
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def _as_envelope(request: Any) -> Tuple[Dict[str, Any], Optional[str]]:
    if isinstance(request, str):
        try:
            decoded = json.loads(request)
        except json.JSONDecodeError as error:
            return {}, f"the request is not JSON: {error}"
        if not isinstance(decoded, dict):
            return {}, "a request envelope is an object"
        return decoded, None
    if isinstance(request, Mapping):
        return dict(request), None
    return {}, f"a request envelope is an object, got {type(request).__name__}"


def _check_envelope(envelope: Mapping[str, Any]) -> Optional[str]:
    """The §2 rules, in the order a host checks them."""
    if envelope.get("bridge_version") != BRIDGE_VERSION:
        return f"bridge_version {envelope.get('bridge_version')} is not {BRIDGE_VERSION}"
    request_id = envelope.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        return "every request carries a non-empty request_id"
    if not isinstance(envelope.get("target"), str):
        return "target is a string naming a bridge object"
    if not isinstance(envelope.get("method"), str):
        return "method is a dotted snake_case string"
    if not isinstance(envelope.get("args"), dict):
        return "args is an object, never positional and never null"
    return None


# ── the legacy toy bridge ───────────────────────────────────────────────────


class FakeBridge:
    """Fake bridge for testing JS↔Python communication."""

    def get_layer(self):
        return {"name": "test_layer", "count": 42}

    def get_extent(self):
        return {"xmin": -180, "ymin": -90, "xmax": 180, "ymax": 90}

    def log(self, msg):
        return f"logged: {msg}"

    def process(self, data):
        try:
            parsed = json.loads(data) if isinstance(data, str) else data
            return {"status": "ok", "action": parsed.get("action", "unknown")}
        except Exception:
            return {"status": "ok", "data": str(data)}


def fake_bridge_factory():
    return FakeBridge()


__all__ = [
    "BRIDGE_VERSION",
    "ERROR_KINDS",
    "BridgeContractError",
    "BridgeHarness",
    "HostError",
    "validate_value",
    "FakeBridge",
    "fake_bridge_factory",
]
