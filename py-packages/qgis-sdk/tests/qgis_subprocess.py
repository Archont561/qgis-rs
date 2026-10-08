"""Run a script in a fresh interpreter that owns its own QGIS runtime.

Native QGIS startup and shutdown are isolated here, not in the pytest process:
a crash, a hang or a segfault during ``exitQgis()`` takes down the child, and
the parent reports it as a failed test with the child's output attached. This
is the same shape TASK-47 needed for the native shutdown SIGSEGV.

Three properties the integration tests rely on:

* ``QT_QPA_PLATFORM=offscreen`` is set in the child, so Qt never needs a
  display.
* ``PYTHONDONTWRITEBYTECODE=1`` is set, so importing a committed fixture plugin
  cannot leave ``__pycache__`` behind in the tree it was read from.
* A wall-clock timeout bounds the child, so a hang fails the run with the
  partial output instead of stalling CI until the job times out.

Kept under ``tests/`` rather than in ``qgis_sdk.testing``: it is test
infrastructure for this repository, not API a downstream plugin should import.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

#: Generous enough for a cold QGIS start on a loaded CI runner, short enough
#: that a hang is a reported failure well before the CI job's own limit.
DEFAULT_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class QgisRun:
    """The outcome of one child interpreter."""

    returncode: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def succeeded(self) -> bool:
        return not self.timed_out and self.returncode == 0

    def describe_exit(self) -> str:
        if self.timed_out:
            return "timed out (the child was killed; output below is what it wrote before that)"
        if self.returncode is None:  # pragma: no cover - subprocess always sets it
            return "no exit status"
        if self.returncode < 0:
            return f"killed by signal {-self.returncode}"
        return f"exit status {self.returncode}"

    def diagnostics(self, *, qgis_version: Optional[str] = None) -> str:
        """Everything needed to diagnose a QGIS/Qt failure from the log alone."""
        return "\n".join(
            [
                f"QGIS subprocess failed: {self.describe_exit()}",
                f"QGIS runtime: {qgis_version or 'unknown'}",
                "--- subprocess stdout ---",
                self.stdout.rstrip() or "(empty)",
                "--- subprocess stderr ---",
                self.stderr.rstrip() or "(empty)",
            ]
        )


def _text(value: object) -> str:
    """``TimeoutExpired`` can carry bytes even when ``text=True`` was requested."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_in_subprocess(
    script: str,
    *,
    cwd: Path,
    pythonpath: Iterable[Path] = (),
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> QgisRun:
    """Run ``script`` with ``sys.executable`` and return what it did.

    ``pythonpath`` entries are prepended to any ``PYTHONPATH`` already set, so a
    fixture plugin is importable by name without touching the caller's
    environment.
    """
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    entries = [str(path) for path in pythonpath]
    if environment.get("PYTHONPATH"):
        entries.append(environment["PYTHONPATH"])
    if entries:
        environment["PYTHONPATH"] = os.pathsep.join(entries)

    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as expired:
        return QgisRun(
            returncode=None,
            stdout=_text(expired.stdout),
            stderr=_text(expired.stderr),
            timed_out=True,
        )
    return QgisRun(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def tree_digest(root: Path) -> Dict[str, str]:
    """Map every file under ``root`` to the SHA-256 of its bytes.

    Used to prove a test left a directory exactly as it found it: the digest
    before and after must be equal, which catches an added file, a removed
    file and an edited one alike.
    """
    digest: Dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            digest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest
