"""The one call across the PyO3 boundary, and the exceptions it raises.

Everything the Python client can ask of qgis-py goes through :func:`invoke`:
one operation name, one JSON payload, one JSON answer. The compiled extension
``qgis_py._core`` exposes exactly one function behind this, so adding an
operation is a change to ``crates/qgis-protocol`` and this client's vocabulary
— never a new ``#[pyfunction]``.

See ``.knowledge/decisions/D09-wire-protocol-over-ffi.md``.

**No fallback.** Importing this module imports the extension. A package whose
extension was never built fails here, with the ImportError that caused it,
instead of quietly answering from a second implementation of the same
arithmetic.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional, Type

from . import _core  # type: ignore[attr-defined]

__all__ = [
    "TRANSPORT_VERSION",
    "EngineError",
    "EngineIOError",
    "InvalidInput",
    "ProjectNotFound",
    "TransportMismatch",
    "Unimplemented",
    "invoke",
]

#: The envelope shape this extension speaks. Compared against every answer, so
#: a client paired with an engine from another release says so at the first
#: call rather than misreading a field.
TRANSPORT_VERSION: int = _core.TRANSPORT_VERSION


class EngineError(Exception):
    """A request the engine understood and refused.

    ``kind`` is the machine-readable classification from the wire
    (``invalid_extent``, ``project_not_found``, ``unimplemented``, …), and
    ``detail`` is whatever extra fields that particular failure carried. Both
    exist so a caller branches on data rather than on English prose.

    The subclasses below also inherit from the built-in exception a Python
    caller would naturally try to catch, so ``except ValueError`` and
    ``except qgis_py.EngineError`` both work on the same object.
    """

    #: Wire classification. Set by :func:`_exception`; class-level defaults
    #: keep a hand-constructed instance usable.
    kind: str = ""
    #: The failure's extra fields, verbatim from the wire.
    detail: Dict[str, Any] = {}


class InvalidInput(EngineError, ValueError):
    """The engine rejected the values in the request."""


class ProjectNotFound(EngineError, FileNotFoundError):
    """The project file does not exist."""


class EngineIOError(EngineError, OSError):
    """A file or directory could not be read or written."""


class Unimplemented(EngineError, NotImplementedError):
    """The operation is not available in the selected engine profile."""


class TransportMismatch(EngineError, RuntimeError):
    """The engine does not speak this client's envelope version."""


# Only the kinds that have a better Python exception than ValueError are
# listed; everything else is a value the engine refused, which is what
# ValueError means. The mapping lives here rather than at each call site so
# one kind cannot become two exception types.
_EXCEPTION_BY_KIND: Dict[str, Type[EngineError]] = {
    "project_not_found": ProjectNotFound,
    "io": EngineIOError,
    "unimplemented": Unimplemented,
    "unsupported_transport": TransportMismatch,
}


def _exception(result: Mapping[str, Any]) -> EngineError:
    """Build the exception one failure envelope describes.

    Constructed with a single positional message and then annotated, because
    ``OSError`` — the base of :class:`ProjectNotFound` and
    :class:`EngineIOError` — reads extra constructor arguments as
    ``errno``/``strerror``/``filename`` and rejects keyword arguments outright.
    """
    kind = str(result.get("kind", "invalid_request"))
    message = str(result.get("error", "the engine refused the request"))
    error = _EXCEPTION_BY_KIND.get(kind, InvalidInput)(message)
    error.kind = kind
    error.detail = {key: value for key, value in result.items() if key not in ("kind", "error")}
    return error


def invoke(operation: str, payload: Optional[Any] = None) -> Any:
    """Run one engine operation and return its ``result``.

    :param operation: a wire operation name, for example ``"plan_tiles"``.
    :param payload: the operation's arguments, or ``None`` for the ones that
        take none.
    :raises EngineError: whenever the engine answered ``ok: false``; the
        concrete class follows the failure's ``kind``.

    Public, and re-exported as ``qgis_py.invoke``: an operation this client has
    no class for is still reachable, which is what keeps a newer engine usable
    from an older wheel.
    """
    request = json.dumps(
        {
            "transport_version": TRANSPORT_VERSION,
            "operation": operation,
            "payload": payload,
        }
    )
    response = json.loads(_core.invoke(request))

    if response.get("transport_version") != TRANSPORT_VERSION:
        mismatch = TransportMismatch(
            f"engine speaks transport version {response.get('transport_version')}, "
            f"this client speaks {TRANSPORT_VERSION}"
        )
        mismatch.kind = "unsupported_transport"
        mismatch.detail = {"supported": TRANSPORT_VERSION, "received": response.get("transport_version")}
        raise mismatch

    if response.get("ok"):
        return response.get("result")

    result = response.get("result") or {}
    raise _exception(result if isinstance(result, Mapping) else {"error": str(result)})
