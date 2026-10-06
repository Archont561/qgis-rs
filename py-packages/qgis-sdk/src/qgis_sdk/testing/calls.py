"""One observable shape for everything a fake was asked to do.

Before this module each fake kept its own log in its own spelling:
``FakeIface.messages`` was a list of strings, ``FakeNetworkManager.requests`` a
list of dicts, the task manager kept ``added_tasks``, and the bridge kept
nothing at all. A test that wanted "was this called, with what" had to know
which fake it was holding.

:class:`Call` and :class:`CallLog` are the one shape all of them record
through — ``target`` (``"iface"``, ``"qgis"``, ``"network"``, ``"tasks"``,
``"ui"``), dotted ``method`` and keyword ``args`` — so an assertion reads the
same whichever fake produced the call, and several fakes can share one log and
be read in call order. The per-fake lists stay where they were: they are what
existing plugin tests assert on, and deleting them would break AC#1 of
TASK-32 for no gain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Mapping, Optional


@dataclass(frozen=True)
class Call:
    """One recorded call: who was asked, what was asked, with which arguments.

    ``args`` is always a mapping, never positional — the same rule the bridge
    wire follows, for the same reason: a test that has to count positions
    cannot say what it is asserting.
    """

    target: str
    method: str
    args: Mapping[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> str:
        """``target.method``, the spelling an assertion message uses."""
        return f"{self.target}.{self.method}"

    def matches(
        self,
        target: Optional[str] = None,
        method: Optional[str] = None,
        **args: Any,
    ) -> bool:
        """Whether this call matches a partial description of one.

        ``args`` is matched as a subset: a call carrying extra arguments still
        matches, because a test that names every argument of every call is a
        test that fails when an unrelated one is added.
        """
        if target is not None and self.target != target:
            return False
        if method is not None and self.method != method:
            return False
        return all(self.args.get(name) == value for name, value in args.items())


class CallLog:
    """An ordered, resettable record of :class:`Call` objects.

    A fake owns one by default and takes one in its constructor, so a test can
    hand the same log to several fakes and read their calls interleaved in the
    order they really happened.
    """

    def __init__(self) -> None:
        self._calls: List[Call] = []

    # ── recording ───────────────────────────────────────────────────────────

    def record(self, target: str, method: str, **args: Any) -> Call:
        """Record a call and return it."""
        call = Call(target=target, method=method, args=dict(args))
        self._calls.append(call)
        return call

    def add(self, call: Call) -> Call:
        """Record an already-built :class:`Call` (for a fake that makes its own)."""
        self._calls.append(call)
        return call

    def reset(self) -> None:
        """Forget every recorded call; the log stays usable."""
        self._calls.clear()

    # ── reading ─────────────────────────────────────────────────────────────

    def all(self) -> List[Call]:
        """Every call, in the order it was made."""
        return list(self._calls)

    def for_target(self, target: str) -> List[Call]:
        """Every call made against one target."""
        return [call for call in self._calls if call.target == target]

    def for_method(self, method: str, target: Optional[str] = None) -> List[Call]:
        """Every call of one method, optionally narrowed to one target.

        ``method`` may be written ``"target.method"``; the target part is then
        matched too, so ``for_method("qgis.layers.list")`` and
        ``for_method("layers.list", target="qgis")`` mean the same thing.
        """
        if target is None:
            for call in self._calls:
                if method == call.path:
                    target, method = call.target, call.method
                    break
        return [call for call in self._calls if call.matches(target, method)]

    def last(self) -> Call:
        """The most recent call.

        :raises AssertionError: when nothing has been recorded.
        """
        if not self._calls:
            raise AssertionError("no calls were recorded")
        return self._calls[-1]

    def paths(self) -> List[str]:
        """``target.method`` for every call — the cheapest readable summary."""
        return [call.path for call in self._calls]

    # ── asserting ───────────────────────────────────────────────────────────

    def assert_called(
        self,
        target: Optional[str] = None,
        method: Optional[str] = None,
        **args: Any,
    ) -> Call:
        """Assert at least one matching call, and return the first one."""
        matches = [call for call in self._calls if call.matches(target, method, **args)]
        if not matches:
            raise AssertionError(self._explain("expected a call", target, method, args))
        return matches[0]

    def assert_called_once(
        self,
        target: Optional[str] = None,
        method: Optional[str] = None,
        **args: Any,
    ) -> Call:
        """Assert exactly one matching call, and return it."""
        matches = [call for call in self._calls if call.matches(target, method, **args)]
        if len(matches) != 1:
            raise AssertionError(
                self._explain(
                    f"expected exactly one call, found {len(matches)}", target, method, args
                )
            )
        return matches[0]

    def assert_not_called(
        self,
        target: Optional[str] = None,
        method: Optional[str] = None,
        **args: Any,
    ) -> None:
        """Assert no matching call was made."""
        matches = [call for call in self._calls if call.matches(target, method, **args)]
        if matches:
            raise AssertionError(self._explain("expected no call", target, method, args))

    def _explain(
        self,
        what: str,
        target: Optional[str],
        method: Optional[str],
        args: Dict[str, Any],
    ) -> str:
        wanted = ".".join(part for part in (target, method) if part) or "any call"
        if args:
            wanted = f"{wanted} with {args}"
        if not self._calls:
            return f"{what} {wanted}; nothing was recorded"
        recorded = "\n  ".join(f"{call.path} {dict(call.args)}" for call in self._calls)
        return f"{what} {wanted}; recorded:\n  {recorded}"

    # ── container protocol ──────────────────────────────────────────────────

    def __iter__(self) -> Iterator[Call]:
        return iter(self._calls)

    def __len__(self) -> int:
        return len(self._calls)

    def __getitem__(self, index: int) -> Call:
        return self._calls[index]

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"<CallLog {self.paths()}>"


def call_log(existing: Optional[CallLog] = None) -> CallLog:
    """Return ``existing`` when a caller supplied one, else a fresh log.

    Every fake constructor takes ``calls=None`` and runs it through this, which
    is what makes "give these three fakes one shared log" a one-word change at
    the call site.
    """
    return existing if existing is not None else CallLog()


__all__ = ["Call", "CallLog", "call_log"]
