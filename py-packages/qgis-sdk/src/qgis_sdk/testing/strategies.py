"""Hypothesis strategies for the pure values the SDK passes around.

Pure data only — extents, zoom ranges, CRS auth ids, plugin names, field
specs, bridge envelopes, network responses, task transition paths. Nothing
here builds a QGIS object, a Qt widget or a live layer, because a generator
that can produce a QGIS object can produce one that only exists in a QGIS
process, and the suite that uses it stops being pure.

Importing this module needs ``hypothesis``; :mod:`qgis_sdk.testing` imports it
defensively, so the package stays importable in a plain QGIS runtime that has
only the SDK installed.
"""

from __future__ import annotations

import keyword
from typing import Any, Dict, List, Mapping, Optional, Sequence

from hypothesis import strategies as st

from .tasks import CANCELED, FAILURE, LEGAL_TRANSITIONS, PENDING, SUCCESS, TERMINAL_STATES

# ── names and identifiers ───────────────────────────────────────────────────

#: The authorities a QGIS install actually answers for.
CRS_AUTHORITIES = ("EPSG", "ESRI", "IGNF", "OGC")

FIELD_TYPES = ("text", "spin", "check", "combo", "file", "layer", "crs")


def snake_case_names(min_size: int = 3, max_size: int = 24) -> st.SearchStrategy:
    """Lowercase identifiers: ``[a-z][a-z0-9_]*``, never ending in ``_``."""
    tail = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_", min_size=min_size - 2, max_size=max_size - 2)
    return st.builds(
        lambda head, middle, last: f"{head}{middle}{last}",
        st.sampled_from("abcdefghijklmnopqrstuvwxyz"),
        tail,
        st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789"),
    )


def plugin_names() -> st.SearchStrategy:
    """Plugin names that are legal Python module names and legal directories."""
    return snake_case_names(min_size=3, max_size=30).filter(lambda name: not keyword.iskeyword(name))


def crs_auth_ids(authorities: Sequence[str] = CRS_AUTHORITIES) -> st.SearchStrategy:
    """``AUTHORITY:CODE`` strings, e.g. ``EPSG:4326``."""
    return st.builds(
        lambda authority, code: f"{authority}:{code}",
        st.sampled_from(list(authorities)),
        st.integers(min_value=1000, max_value=99999),
    )


# ── geometry-adjacent values ────────────────────────────────────────────────


def extents(
    min_value: float = -180.0, max_value: float = 180.0, allow_degenerate: bool = False
) -> st.SearchStrategy:
    """Extent dicts with ``xmin < xmax`` and ``ymin < ymax``.

    ``allow_degenerate`` keeps zero-width extents, which a renderer has to
    refuse rather than divide by.
    """
    coordinate = st.floats(
        min_value=min_value, max_value=max_value, allow_nan=False, allow_infinity=False, width=32
    )

    def ordered(pair):
        low, high = sorted(pair)
        return low, high

    return st.builds(
        lambda xs, ys: {"xmin": xs[0], "ymin": ys[0], "xmax": xs[1], "ymax": ys[1]},
        st.tuples(coordinate, coordinate).map(ordered),
        st.tuples(coordinate, coordinate).map(ordered),
    ).filter(
        lambda extent: allow_degenerate
        or (extent["xmin"] < extent["xmax"] and extent["ymin"] < extent["ymax"])
    )


def zoom_ranges(max_zoom: int = 24) -> st.SearchStrategy:
    """``(min_zoom, max_zoom)`` pairs inside a slippy-map's 0..24."""
    return st.tuples(
        st.integers(min_value=0, max_value=max_zoom), st.integers(min_value=0, max_value=max_zoom)
    ).map(lambda pair: (min(pair), max(pair)))


# ── UI field specs ──────────────────────────────────────────────────────────


def field_specs(field_types: Sequence[str] = FIELD_TYPES) -> st.SearchStrategy:
    """Field-spec *dicts* — the keys ``qgis_sdk.ui.FieldSpec`` takes.

    Dicts, not ``FieldSpec`` objects: importing the UI module drags in Qt, and
    a strategy that forces that on a pure test defeats the point. A test that
    wants the real thing does ``FieldSpec(**spec)``.
    """

    @st.composite
    def build(draw):
        field_type = draw(st.sampled_from(list(field_types)))
        name = draw(snake_case_names())
        spec: Dict[str, Any] = {"name": name, "label": name.replace("_", " ").title(), "field_type": field_type}
        if field_type == "spin":
            low = draw(st.integers(min_value=-1000, max_value=1000))
            high = draw(st.integers(min_value=low, max_value=low + 1000))
            spec.update({"min": float(low), "max": float(high), "default": float(low)})
        elif field_type == "check":
            spec["default"] = draw(st.booleans())
        elif field_type == "combo":
            options = draw(st.lists(snake_case_names(), min_size=1, max_size=5, unique=True))
            spec.update({"options": tuple(options), "default": options[0]})
        elif field_type == "layer":
            spec.update({"layer_filter": draw(st.sampled_from(["vector", "raster"])), "default": ""})
        elif field_type == "crs":
            spec["default"] = draw(crs_auth_ids())
        else:
            spec["default"] = draw(st.text(max_size=20))
        return spec

    return build()


# ── bridge envelopes ────────────────────────────────────────────────────────


def request_ids() -> st.SearchStrategy:
    """Opaque caller-chosen ids; the host must echo whatever it is given."""
    return st.builds(
        lambda prefix, number: f"{prefix}-{number}",
        st.sampled_from(["req", "call", "rpc", "x"]),
        st.integers(min_value=0, max_value=10_000),
    )


def object_handles(object_type: str = "qgis.layer", session_id: str = "sess-1") -> st.SearchStrategy:
    """Handles with opaque ids, inside one session."""
    return st.builds(
        lambda object_id: {
            "object_id": object_id,
            "object_type": object_type,
            "session_id": session_id,
        },
        st.text(alphabet="abcdef0123456789-", min_size=4, max_size=16),
    )


def values_for_schema(schema: Mapping[str, Any], session_id: str = "sess-1") -> st.SearchStrategy:
    """Values that satisfy one subset schema from a bridge manifest.

    The inverse of the harness's validator: whatever this draws,
    ``validate_value`` must accept. That pairing is the property worth having
    — it fails when either side drifts.
    """
    if "$handle" in schema:
        return object_handles(schema["$handle"], session_id)
    if "enum" in schema:
        return st.sampled_from(list(schema["enum"]))

    type_name = schema.get("type")
    if type_name == "object":
        properties: Mapping[str, Any] = schema.get("properties", {})
        required = list(schema.get("required", []))
        optional = [name for name in properties if name not in required]

        @st.composite
        def build_object(draw):
            members = {
                name: draw(values_for_schema(properties[name], session_id)) for name in required
            }
            extras = (
                draw(st.lists(st.sampled_from(optional), unique=True)) if optional else []
            )
            for name in extras:
                members[name] = draw(values_for_schema(properties[name], session_id))
            return members

        return build_object()
    if type_name == "array":
        items = schema.get("items")
        if not items:
            return st.lists(st.integers(), max_size=3)
        return st.lists(values_for_schema(items, session_id), max_size=3)
    if type_name == "string":
        return st.text(max_size=20)
    if type_name == "boolean":
        return st.booleans()
    if type_name == "integer":
        return st.integers(min_value=-1000, max_value=1000)
    if type_name == "number":
        return st.floats(allow_nan=False, allow_infinity=False, width=32)
    return st.none()


def bridge_requests(
    description: Mapping[str, Any],
    target: Optional[str] = None,
    session_id: str = "sess-1",
    methods: Optional[Sequence[str]] = None,
) -> st.SearchStrategy:
    """Well-formed request envelopes for one manifest.

    Every draw names a method the manifest really declares and carries
    arguments its schema really accepts, so a harness must answer every one of
    them without an ``invalid_*`` error.
    """
    namespace = target or description.get("namespace")
    if namespace is None:
        raise ValueError("the manifest has no namespace; pass target=")
    specs = [
        spec
        for spec in description.get("methods", [])
        if methods is None or spec["name"] in methods
    ]
    if not specs:
        raise ValueError(f"{namespace} declares none of {methods}")

    @st.composite
    def build(draw):
        spec = draw(st.sampled_from(specs))
        return {
            "bridge_version": description.get("bridge_version", 1),
            "request_id": draw(request_ids()),
            "target": namespace,
            "method": spec["name"],
            "args": draw(values_for_schema(spec.get("args", {}), session_id)) or {},
        }

    return build()


def bridge_error_kinds(kinds: Sequence[str] = ()) -> st.SearchStrategy:
    """One of the closed error-kind set."""
    from .bridge import ERROR_KINDS

    return st.sampled_from(list(kinds) if kinds else list(ERROR_KINDS))


def bridge_responses(request_id: Optional[str] = None) -> st.SearchStrategy:
    """Response envelopes, success and failure, correlated to a request id."""
    ids = st.just(request_id) if request_id is not None else request_ids()

    success = st.builds(
        lambda rid, result: {
            "bridge_version": 1,
            "request_id": rid,
            "ok": True,
            "result": result,
        },
        ids,
        st.recursive(
            st.none() | st.booleans() | st.integers() | st.text(max_size=10),
            lambda children: st.lists(children, max_size=3)
            | st.dictionaries(st.text(min_size=1, max_size=6), children, max_size=3),
            max_leaves=5,
        ),
    )
    failure = st.builds(
        lambda rid, kind, message: {
            "bridge_version": 1,
            "request_id": rid,
            "ok": False,
            "error": {"kind": kind, "message": message},
        },
        ids,
        bridge_error_kinds(),
        st.text(min_size=1, max_size=40),
    )
    return st.one_of(success, failure)


# ── network and tasks ───────────────────────────────────────────────────────


def network_responses(
    status_codes: Sequence[int] = (200, 201, 204, 301, 400, 404, 500, 503),
) -> st.SearchStrategy:
    """Scripted :class:`~qgis_sdk.testing.network.FakeResponse` objects."""
    from .network import FakeResponse

    return st.builds(
        lambda status, body, encoding: FakeResponse(
            url="https://example.test/resource",
            status_code=status,
            content=body.encode(encoding, errors="ignore"),
            encoding=encoding,
        ),
        st.sampled_from(list(status_codes)),
        st.text(max_size=64),
        st.sampled_from(["utf-8", "latin-1"]),
    )


def task_transitions(max_length: int = 4) -> st.SearchStrategy:
    """Legal paths through the task state machine, starting at PENDING.

    Drawn from :data:`~qgis_sdk.testing.tasks.LEGAL_TRANSITIONS`, so a test
    asserting "a task never skips a state" is reading the same table the fake
    enforces — and a change to one of them fails the property rather than
    quietly agreeing with itself.
    """

    @st.composite
    def build(draw):
        path: List[str] = [PENDING]
        while len(path) < max_length and path[-1] not in TERMINAL_STATES:
            choices = sorted(LEGAL_TRANSITIONS[path[-1]])
            path.append(draw(st.sampled_from(choices)))
        return path

    return build()


def terminal_states() -> st.SearchStrategy:
    """One of the three ways a task can end."""
    return st.sampled_from([SUCCESS, FAILURE, CANCELED])


__all__ = [
    "CRS_AUTHORITIES",
    "FIELD_TYPES",
    "snake_case_names",
    "plugin_names",
    "crs_auth_ids",
    "extents",
    "zoom_ranges",
    "field_specs",
    "request_ids",
    "object_handles",
    "values_for_schema",
    "bridge_requests",
    "bridge_error_kinds",
    "bridge_responses",
    "network_responses",
    "task_transitions",
    "terminal_states",
]
