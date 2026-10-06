"""The deterministic task machine: five states, no threads, no sleeping.

Two things are being pinned here. The machine itself — which moves are legal,
what cancellation does, how a chain stops — and the fact that it is
*deterministic*: with ``auto_run=False`` nothing happens until the test says
so, which is the only way an ordering assertion is about ordering rather than
about how fast the machine running the suite happens to be.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings

from qgis_sdk.testing import (
    CANCELED,
    FAILURE,
    LEGAL_TRANSITIONS,
    PENDING,
    RUNNING,
    SUCCESS,
    FakeTask,
    FakeTaskManager,
    IllegalTransition,
    ScheduledTask,
    canonical_state,
)
from qgis_sdk.testing import strategies as qst


def test_a_submitted_task_runs_at_once_by_default() -> None:
    manager = FakeTaskManager()

    task = manager.submit(lambda: 21 * 2, description="double")

    assert task.state == SUCCESS
    assert task.result == 42
    assert task.transitions == [PENDING, RUNNING, SUCCESS]


def test_nothing_runs_until_the_test_says_so() -> None:
    manager = FakeTaskManager(auto_run=False)

    task = manager.submit(lambda: 42)
    assert task.state == PENDING
    assert manager.queue == [task]

    manager.run_next()
    assert task.state == SUCCESS
    assert manager.queue == []
    assert manager.run_next() is None


def test_a_raising_task_fails_rather_than_escaping() -> None:
    manager = FakeTaskManager()
    seen: list[tuple] = []

    def boom():
        raise ValueError("no layer")

    task = manager.submit(boom, on_finished=lambda exc, result: seen.append((exc, result)))

    assert task.state == FAILURE
    assert isinstance(task.exception, ValueError)
    assert [type(exc) for exc, _ in seen] == [ValueError]
    with pytest.raises(ValueError, match="no layer"):
        task.get()
    assert task.get(propagate=False) is None


def test_progress_is_monotonic_and_reported_to_subscribers() -> None:
    manager = FakeTaskManager(auto_run=False)
    seen: list[float] = []

    def work(task):
        task.set_progress(25)
        task.set_progress(80)
        return "done"

    task = manager.submit(work, bind=True, on_progress=seen.append)
    manager.run_next()

    assert seen == [25.0, 80.0]
    assert task.progress_history == [25.0, 80.0]
    assert task.progress == 80.0


def test_progress_may_not_go_backwards_or_arrive_after_the_end() -> None:
    """A fake that tolerates nonsense teaches a plugin to emit nonsense."""
    task = ScheduledTask(work=lambda: None)
    task.transition_to(RUNNING)
    task.set_progress(50)

    with pytest.raises(IllegalTransition, match="progress went backwards"):
        task.set_progress(10)

    task.transition_to(SUCCESS)
    with pytest.raises(IllegalTransition, match="cannot report progress"):
        task.set_progress(100)


def test_cancelling_a_queued_task_means_it_never_runs() -> None:
    manager = FakeTaskManager(auto_run=False)
    ran: list[str] = []

    first = manager.submit(lambda: ran.append("first"))
    second = manager.submit(lambda: ran.append("second"))

    assert manager.cancel(first) is True
    manager.run_all()

    assert first.state == CANCELED
    assert second.state == SUCCESS
    assert ran == ["second"]
    assert manager.calls.paths().count("tasks.cancel") == 1


def test_a_finished_task_cannot_be_cancelled_or_rerun() -> None:
    manager = FakeTaskManager()
    task = manager.submit(lambda: 1)

    assert task.cancel() is False
    assert task.state == SUCCESS
    with pytest.raises(IllegalTransition, match="cannot run"):
        task.run()


def test_a_finished_callback_added_late_still_fires() -> None:
    """Subscribing after the fact is the common shape in a synchronous test."""
    manager = FakeTaskManager()
    task = manager.submit(lambda: "value")

    seen: list = []
    task.on_finished(lambda exc, result: seen.append((exc, result)))

    assert seen == [(None, "value")]


def test_a_chain_feeds_each_result_to_the_next_link() -> None:
    manager = FakeTaskManager(auto_run=False)

    chain = manager.chain([lambda: 2, lambda value: value * 3, lambda value: value + 1])
    manager.run_all()

    assert [task.state for task in chain] == [SUCCESS, SUCCESS, SUCCESS]
    assert chain.result == 7
    assert chain.state == SUCCESS


def test_a_broken_link_cancels_the_rest_of_the_chain() -> None:
    manager = FakeTaskManager(auto_run=False)

    def explode(_value):
        raise RuntimeError("bad geometry")

    chain = manager.chain([lambda: 1, explode, lambda value: value + 1])
    manager.run_all()

    assert [task.state for task in chain] == [SUCCESS, FAILURE, CANCELED]
    assert chain.state == FAILURE
    assert isinstance(chain.tasks[1].exception, RuntimeError)


def test_a_group_runs_independently() -> None:
    manager = FakeTaskManager()

    def explode():
        raise ValueError("nope")

    group = manager.group([lambda: 1, explode, lambda: 3])

    assert group.states == [SUCCESS, FAILURE, SUCCESS]
    assert group.ready() and not group.successful()
    assert group.results == [1, None, 3]


def test_the_manager_records_every_move_in_its_call_log() -> None:
    manager = FakeTaskManager(auto_run=False)
    task = manager.submit(lambda: 1, description="count")
    manager.run_next()
    manager.cancel(task)

    assert manager.calls.paths() == ["tasks.submit", "tasks.run", "tasks.cancel"]
    assert manager.calls.assert_called_once("tasks", "submit").args["description"] == "count"


def test_the_celery_facade_keeps_its_own_spelling() -> None:
    """AC#1: ``FakeTask`` still answers celery's STARTED/REVOKED names.

    Both vocabularies are deliberate — the celery-shaped API mirrors
    ``qgis_sdk.tasks``, the scheduler mirrors doc-5 — and ``canonical_state``
    is the one place that maps between them.
    """
    task = FakeTask("legacy", lambda: 7)
    assert task.state == "PENDING"
    task._execute()
    assert task.state == "SUCCESS"

    canceled = FakeTask("legacy", lambda: 7)
    canceled.cancel()
    assert canceled.state == "REVOKED"
    assert canceled.canonical_state == CANCELED
    assert canonical_state("STARTED") == RUNNING


def test_cancel_all_reaches_both_surfaces() -> None:
    manager = FakeTaskManager(auto_run=False)
    queued = manager.submit(lambda: 1)

    manager.cancel_all()

    assert queued.state == CANCELED


@settings(max_examples=100, deadline=None)
@given(path=qst.task_transitions())
def test_a_generated_path_is_one_the_machine_accepts(path: list[str]) -> None:
    """doc-5's property: "task transitions never skip illegal states".

    The strategy draws from the same table :class:`ScheduledTask` enforces, so
    this fails the day one of them is changed without the other.
    """
    task = ScheduledTask(work=lambda: None)

    for state in path[1:]:
        task.transition_to(state)

    assert task.transitions == path
    for before, after in zip(path, path[1:]):
        assert after in LEGAL_TRANSITIONS[before]


@settings(max_examples=50, deadline=None)
@given(terminal=qst.terminal_states())
def test_nothing_leaves_a_terminal_state(terminal: str) -> None:
    task = ScheduledTask(work=lambda: None)
    if terminal != CANCELED:
        task.transition_to(RUNNING)
    task.transition_to(terminal)

    for state in (RUNNING, SUCCESS, FAILURE, CANCELED, PENDING):
        with pytest.raises(IllegalTransition):
            task.transition_to(state)
