"""Which tests belong to which execution-layer gate.

:mod:`~qgis_sdk.testing.environment` answers *what this process can reach*.
This module answers the other half: *what a given gate is supposed to run*,
and it does so as pure data — no pytest, no Qt, no QGIS, nothing imported for
a side effect — so the policy can be tested without any of the runtimes it
talks about.

Four gates, one per layer:

===========  ==========================================================
``pure``     every test that demands no runtime at all
``qt``       tests marked ``qt``
``qgis``     tests marked ``qgis``
``webengine``tests marked ``webengine``
===========  ==========================================================

The gates deliberately **overlap** rather than partition: a test marked both
``qt`` and ``webengine`` runs in both, because both claims about it are true.
What they must never do is leave a test in no gate at all, which is why
``pure`` is defined by the absence of a layer marker rather than by the
presence of a ``pure_python`` one.

Why a gate is not just ``pytest -m qgis``
-----------------------------------------

Because ``-m qgis`` passes when every selected test skips. The ordinary suite
*should* skip a layer it cannot reach — that is what makes one command work on
a laptop, in a bare CI virtualenv and inside QGIS. But a gate is a different
claim: "the QGIS layer works here". Running it on a machine without QGIS has
to be an error, not a green run with a skip count nobody reads.

So selecting a gate flips the policy: the layer is asserted at startup, the
run is narrowed to that layer's tests, and a skip for a missing runtime can no
longer happen because the run would have failed before collection.
"""

from __future__ import annotations

from typing import Any, FrozenSet, Iterable, Mapping, Optional, Tuple

#: Environment variable that pins a run to one gate.
LAYER_ENV_VAR = "QGIS_TEST_LAYER"

#: The gates, in increasing order of what they need installed.
GATES: Tuple[str, ...] = ("pure", "qt", "qgis", "webengine")

#: Markers that demand a runtime. ``network``, ``tasks`` and ``pure_python``
#: describe what a test is *about*, not what has to be installed for it.
LAYER_MARKERS: Tuple[str, ...] = ("qt", "qgis", "webengine")


def layers_required(markers: Iterable[str]) -> FrozenSet[str]:
    """The runtimes a test carrying ``markers`` needs before it can run."""
    return frozenset(marker for marker in markers if marker in LAYER_MARKERS)


def selected_by(gate: str, markers: Iterable[str]) -> bool:
    """Whether a test carrying ``markers`` belongs to ``gate``.

    :raises ValueError: for a gate name that is not one of :data:`GATES`;
        a typo must not quietly select nothing and report a pass.
    """
    if gate not in GATES:
        raise ValueError(f"unknown test gate {gate!r}; expected one of {', '.join(GATES)}")
    required = layers_required(markers)
    if gate == "pure":
        return not required
    return gate in required


def requested_gate(environ: Mapping[str, str]) -> Optional[str]:
    """The gate :data:`LAYER_ENV_VAR` asks for, or ``None`` for the full suite.

    Whitespace and case are forgiven because this arrives from a shell; an
    unknown name is not, for the same reason as in :func:`selected_by`.
    """
    raw = environ.get(LAYER_ENV_VAR, "")
    name = raw.strip().lower()
    if not name:
        return None
    if name not in GATES:
        raise ValueError(f"unknown test gate {raw!r}; expected one of {', '.join(GATES)}")
    return name


def unreachable_reason(gate: str, environment: Any) -> Optional[str]:
    """Why ``gate`` cannot run here, or ``None`` when it can.

    ``environment`` is a :class:`~qgis_sdk.testing.environment.QgisTestEnvironment`;
    it is taken as a parameter rather than detected here so this module stays
    free of imports with side effects.
    """
    if gate not in GATES:
        raise ValueError(f"unknown test gate {gate!r}; expected one of {', '.join(GATES)}")
    if gate == "pure":
        return None
    if environment.supports(gate):
        return None
    return (
        f"the {gate} gate was requested but this environment cannot reach the "
        f"{gate} layer (reachable: {', '.join(sorted(environment.layers))}). "
        "A gate that skips is a gate that proved nothing, so this is an error "
        "rather than a skip."
    )


def parallelism_of(config: Any) -> int:
    """How many workers pytest was asked for, as an integer.

    QGIS is a process-wide singleton, so the ``qgis`` gate has to run
    serialized. ``-n`` comes from pytest-xdist, which may not be installed at
    all; absent or non-numeric means one worker.
    """
    workers = getattr(config.option, "numprocesses", None)
    if workers in (None, "no"):
        return 1
    if workers == "auto":
        return 2  # "more than one" is all the caller needs to know
    try:
        return max(1, int(workers))
    except (TypeError, ValueError):
        return 1


__all__ = [
    "GATES",
    "LAYER_ENV_VAR",
    "LAYER_MARKERS",
    "layers_required",
    "parallelism_of",
    "requested_gate",
    "selected_by",
    "unreachable_reason",
]
