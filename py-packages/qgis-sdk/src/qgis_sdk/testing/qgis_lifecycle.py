"""Constructing and tearing down a real ``QgsApplication``, deterministically.

The ``qgis_app`` fixture deliberately does **not** do this: it hands back the
host's live application when a plugin's tests run inside QGIS, and skips
otherwise. That is right for a plugin test, and useless for the ``qgis`` gate,
whose whole job is to prove the QGIS layer works in a plain pytest process.

So this module owns the other half — the standalone lifecycle — and keeps it
out of the fixture file because it is the one piece of the testing package
that genuinely touches a native singleton.

Three things make it deterministic rather than hopeful:

* **One application per process.** ``QgsApplication`` is a process-wide
  singleton. If one already exists — the plugin-inside-QGIS case — it is
  adopted and *not* shut down, because this code did not create it and the
  host is still using it.
* **Offscreen before the import.** ``QT_QPA_PLATFORM`` is set before Qt picks
  a platform plugin; a headless runner that picks the wrong one aborts rather
  than skipping, and it cannot be changed after the fact.
* **``exitQgis`` in a finally.** The provider registry holds open file handles
  and loaded plugin libraries. Leaving them to interpreter teardown is what
  produces the "aborts during pytest shutdown" folklore; calling ``exitQgis``
  explicitly, before the interpreter starts dismantling modules, does not.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator, Optional

#: Set before Qt resolves its platform plugin — see the module docstring.
HEADLESS_PLATFORM = "offscreen"


def ensure_headless() -> str:
    """Force an offscreen Qt platform unless the caller chose one already."""
    os.environ.setdefault("QT_QPA_PLATFORM", HEADLESS_PLATFORM)
    return os.environ["QT_QPA_PLATFORM"]


def _prefix_path() -> Optional[str]:
    """The QGIS prefix, when the environment names one.

    Conda-style installs set ``QGIS_PREFIX_PATH``; when it is absent QGIS
    resolves its own prefix from the loaded library, which is correct more
    often than any guess this function could make.
    """
    prefix = os.environ.get("QGIS_PREFIX_PATH")
    return prefix or None


@contextmanager
def qgis_application(*, exit_on_close: Optional[bool] = None) -> Iterator[Any]:
    """A live ``QgsApplication`` for the duration of the block.

    Adopts an existing instance when one is already running, and in that case
    leaves it alone on the way out: shutting down a host's application from
    underneath it would be a far worse bug than leaking one in a test process.

    :param exit_on_close: override the shutdown decision. ``None`` means
        "shut down what we created, adopt what we did not".
    :raises RuntimeError: when ``qgis.core`` cannot be imported — callers are
        expected to have checked the layer first, so reaching here is a
        programming error rather than an environment to skip over.
    """
    ensure_headless()

    try:
        from qgis.core import QgsApplication
    except ImportError as exc:  # pragma: no cover - guarded by the caller
        raise RuntimeError("qgis.core is not importable; check the layer first") from exc

    existing = QgsApplication.instance()
    owned = existing is None

    if owned:
        application = QgsApplication([], False)
        prefix = _prefix_path()
        if prefix:
            QgsApplication.setPrefixPath(prefix, True)
        application.initQgis()
    else:
        application = existing

    should_exit = owned if exit_on_close is None else exit_on_close
    try:
        yield application
    finally:
        if should_exit:
            application.exitQgis()


__all__ = ["HEADLESS_PLATFORM", "ensure_headless", "qgis_application"]
