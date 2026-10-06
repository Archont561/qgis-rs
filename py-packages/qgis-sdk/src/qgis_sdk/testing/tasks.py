"""Task fakes: one deterministic state machine, one celery-shaped facade.

doc-5 asks for an explicit machine::

    PENDING -> RUNNING -> SUCCESS
                       -> FAILURE
                       -> CANCELED

:class:`ScheduledTask` is that machine, and :class:`FakeTaskManager` drives it
with ``submit``/``run_next``/``run_all``/``chain``/``group``. Nothing sleeps
and nothing starts a thread: ``auto_run=False`` leaves a task ``PENDING``
until the test says to run it, which is the only way an ordering assertion can
be about ordering rather than about timing.

**Two vocabularies, on purpose.** ``qgis_sdk.tasks`` presents a celery-like
API, and :class:`FakeTask` mirrors it — so its ``state`` keeps celery's
``STARTED`` and ``REVOKED`` spellings, which existing plugin tests assert on
(AC#1). The scheduler above uses doc-5's five names. :func:`canonical_state`
maps the first onto the second, so one assertion can read either.
"""

from __future__ import annotations

import inspect
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .calls import CallLog, call_log

# ── the state machine ───────────────────────────────────────────────────────

PENDING = "PENDING"
RUNNING = "RUNNING"
SUCCESS = "SUCCESS"
FAILURE = "FAILURE"
CANCELED = "CANCELED"

#: Every state a :class:`ScheduledTask` can be in.
TASK_STATES = (PENDING, RUNNING, SUCCESS, FAILURE, CANCELED)

#: The only moves allowed. A test asserting "transitions never skip a state"
#: reads this table, so the table is the contract rather than the code's habit.
LEGAL_TRANSITIONS: Dict[str, frozenset] = {
    PENDING: frozenset({RUNNING, CANCELED}),
    RUNNING: frozenset({SUCCESS, FAILURE, CANCELED}),
    SUCCESS: frozenset(),
    FAILURE: frozenset(),
    CANCELED: frozenset(),
}

#: Terminal states: nothing leaves them.
TERMINAL_STATES = frozenset({SUCCESS, FAILURE, CANCELED})

#: celery's spelling of the two states it names differently.
CELERY_STATE_ALIASES = {"STARTED": RUNNING, "REVOKED": CANCELED}


class IllegalTransition(AssertionError):
    """Raised when something asks a task for a move the machine forbids."""


def canonical_state(state: str) -> str:
    """Map a celery state name onto this module's five-state vocabulary."""
    return CELERY_STATE_ALIASES.get(state, state)


@dataclass
class ScheduledTask:
    """One unit of deterministic work and the states it passed through.

    Created by :meth:`FakeTaskManager.submit`; a test holds it to read
    :attr:`state`, :attr:`progress` and :attr:`result`, to attach callbacks, or
    to cancel it before the manager runs it.
    """

    description: str = "Task"
    work: Optional[Callable[..., Any]] = None
    args: tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    bind: bool = False
    #: The task this one follows in a chain; it runs only if that one succeeded.
    depends_on: Optional["ScheduledTask"] = None
    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    state: str = PENDING
    progress: float = 0.0
    result: Any = None
    exception: Optional[BaseException] = None
    transitions: List[str] = field(default_factory=lambda: [PENDING])
    progress_history: List[float] = field(default_factory=list)
    _progress_callbacks: List[Callable[[float], None]] = field(default_factory=list)
    _finished_callbacks: List[Callable[[Optional[BaseException], Any], None]] = field(
        default_factory=list
    )

    # ── transitions ─────────────────────────────────────────────────────────

    def transition_to(self, state: str) -> None:
        """Move to ``state``, or refuse with :class:`IllegalTransition`."""
        if state not in TASK_STATES:
            raise IllegalTransition(f"{state} is not one of {TASK_STATES}")
        if state not in LEGAL_TRANSITIONS[self.state]:
            raise IllegalTransition(f"{self.id}: {self.state} cannot become {state}")
        self.state = state
        self.transitions.append(state)

    def set_progress(self, value: float) -> None:
        """Report progress in percent. Monotonic: a decrease is a defect.

        Progress is only meaningful while a task runs; reporting it from a
        terminal state is the same defect seen later.
        """
        if self.state in TERMINAL_STATES:
            raise IllegalTransition(f"{self.id} is {self.state}; it cannot report progress")
        if value < self.progress:
            raise IllegalTransition(
                f"{self.id}: progress went backwards, {self.progress} -> {value}"
            )
        self.progress = float(value)
        self.progress_history.append(float(value))
        for callback in list(self._progress_callbacks):
            callback(float(value))

    def cancel(self) -> bool:
        """Cancel a pending or running task. Returns whether it moved."""
        if self.state in TERMINAL_STATES:
            return False
        self.transition_to(CANCELED)
        self._announce()
        return True

    # ── callbacks ───────────────────────────────────────────────────────────

    def on_progress(self, callback: Callable[[float], None]) -> "ScheduledTask":
        self._progress_callbacks.append(callback)
        return self

    def on_finished(
        self, callback: Callable[[Optional[BaseException], Any], None]
    ) -> "ScheduledTask":
        """Register ``callback(exception, result)``, the SDK's own signature.

        A task that already finished calls it immediately, so a test never has
        to care whether it subscribed before or after the run.
        """
        self._finished_callbacks.append(callback)
        if self.state in TERMINAL_STATES:
            callback(self.exception, self.result)
        return self

    def _announce(self) -> None:
        for callback in list(self._finished_callbacks):
            callback(self.exception, self.result)

    # ── reading ─────────────────────────────────────────────────────────────

    @property
    def canceled(self) -> bool:
        return self.state == CANCELED

    def ready(self) -> bool:
        return self.state in TERMINAL_STATES

    def successful(self) -> bool:
        return self.state == SUCCESS

    def failed(self) -> bool:
        return self.state == FAILURE

    def get(self, propagate: bool = True) -> Any:
        """The result, re-raising the handler's exception by default."""
        if self.exception is not None and propagate:
            raise self.exception
        return self.result

    # ── running ─────────────────────────────────────────────────────────────

    def run(self) -> "ScheduledTask":
        """Run the work once, PENDING -> RUNNING -> SUCCESS/FAILURE."""
        if self.state != PENDING:
            raise IllegalTransition(f"{self.id} is {self.state}; it cannot run")
        self.transition_to(RUNNING)
        try:
            self.result = self._invoke()
        except BaseException as exc:  # noqa: BLE001 - a task failure is data here
            self.exception = exc
            self.transition_to(FAILURE)
        else:
            self.transition_to(SUCCESS)
        self._announce()
        return self

    def _invoke(self) -> Any:
        if self.work is None:
            return None
        if self.bind or _wants_task_argument(self.work):
            return self.work(self, *self.args, **self.kwargs)
        return self.work(*self.args, **self.kwargs)


def _wants_task_argument(work: Callable[..., Any]) -> bool:
    """Whether ``work``'s first parameter is the task itself.

    The SDK's ``@task(bind=True)`` passes the task in; so do plain functions
    that name their first parameter ``task``. Both spellings exist in tests
    that predate this module, so both keep working.
    """
    try:
        parameters = list(inspect.signature(work).parameters.values())
    except (TypeError, ValueError):  # pragma: no cover - builtins and C callables
        return False
    return bool(parameters) and parameters[0].name in ("task", "self", "celery_task", "qgis_task", "bind_task")


class TaskGroup:
    """Tasks submitted together; they succeed or fail independently."""

    def __init__(self, tasks: List[ScheduledTask]):
        self.tasks = list(tasks)

    @property
    def states(self) -> List[str]:
        return [task.state for task in self.tasks]

    @property
    def results(self) -> List[Any]:
        return [task.result for task in self.tasks]

    def ready(self) -> bool:
        return all(task.ready() for task in self.tasks)

    def successful(self) -> bool:
        return all(task.successful() for task in self.tasks)

    def cancel(self) -> None:
        for task in self.tasks:
            task.cancel()

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self):
        return iter(self.tasks)


class TaskChain(TaskGroup):
    """Tasks run in order, each receiving the previous task's result.

    A link that fails or is canceled stops the chain: the manager cancels
    every link behind it rather than running it, which is what makes "did step
    three run?" an answerable question.
    """

    @property
    def result(self) -> Any:
        finished = [task for task in self.tasks if task.state == SUCCESS]
        return finished[-1].result if finished else None

    @property
    def state(self) -> str:
        for task in self.tasks:
            if task.state in (FAILURE, CANCELED):
                return task.state
        if all(task.state == SUCCESS for task in self.tasks):
            return SUCCESS
        return RUNNING if any(task.state == SUCCESS for task in self.tasks) else PENDING


class FakeTaskManager:
    """Deterministic task scheduler — and the old celery-like facade.

    The new surface::

        manager = FakeTaskManager(auto_run=False)
        task = manager.submit(work)
        assert task.state == "PENDING"
        manager.run_next()
        assert task.state == "SUCCESS"

    The old surface — ``add_task``, ``added_tasks``, ``results``, ``tasks()``,
    ``count()``, ``cancel_all()`` — is unchanged and still returns
    :class:`FakeAsyncResult`, because plugin suites written against it must
    keep passing (AC#1).
    """

    def __init__(self, auto_run: bool = True, calls: Optional[CallLog] = None):
        self.auto_run = auto_run
        self.calls = call_log(calls)
        #: Submitted-but-unrun :class:`ScheduledTask` objects, in order.
        self.queue: List[ScheduledTask] = []
        #: Every task this manager ever scheduled, in submission order.
        self.history: List[ScheduledTask] = []
        # The celery-like facade's state, kept exactly as it was.
        self._tasks: List["FakeTask"] = []
        self.added_tasks: List["FakeTask"] = []
        self.results: List["FakeAsyncResult"] = []

    # ── the deterministic surface ───────────────────────────────────────────

    def submit(
        self,
        work: Optional[Callable[..., Any]] = None,
        *args: Any,
        description: str = "Task",
        on_finished: Optional[Callable[[Optional[BaseException], Any], None]] = None,
        on_progress: Optional[Callable[[float], None]] = None,
        bind: bool = False,
        **kwargs: Any,
    ) -> ScheduledTask:
        """Schedule ``work``; run it now when ``auto_run``, else leave it PENDING."""
        task = ScheduledTask(
            description=description, work=work, args=args, kwargs=kwargs, bind=bind
        )
        if on_progress is not None:
            task.on_progress(on_progress)
        if on_finished is not None:
            task.on_finished(on_finished)
        self.history.append(task)
        self.calls.record("tasks", "submit", description=description, task_id=task.id)
        if self.auto_run:
            task.run()
        else:
            self.queue.append(task)
        return task

    def run_next(self) -> Optional[ScheduledTask]:
        """Run the next runnable task.

        A task that was canceled while queued is dropped, and a chain link
        whose predecessor did not succeed is canceled rather than run — a
        failed chain leaves no half-run work behind it.
        """
        while self.queue:
            task = self.queue.pop(0)
            if task.state == CANCELED:
                continue
            if task.depends_on is not None and task.depends_on.state != SUCCESS:
                task.cancel()
                continue
            self.calls.record("tasks", "run", task_id=task.id)
            return task.run()
        return None

    def run_all(self) -> List[ScheduledTask]:
        """Run every queued task, in submission order."""
        ran: List[ScheduledTask] = []
        while self.queue:
            task = self.run_next()
            if task is not None:
                ran.append(task)
        return ran

    def chain(self, works: List[Callable[..., Any]], description: str = "Chain") -> TaskChain:
        """Submit tasks that run in order, each fed the previous result.

        Honours ``auto_run``: with it off, ``run_all()`` walks the chain in the
        order it was declared. The first link takes no argument; every later
        one takes the previous result. A link that fails cancels the rest.
        """
        tasks: List[ScheduledTask] = []
        previous: Dict[str, Any] = {"value": None}

        for index, work in enumerate(works):

            def link(_task, _work=work, _index=index):
                value = _work() if _index == 0 else _work(previous["value"])
                previous["value"] = value
                return value

            task = ScheduledTask(
                description=f"{description}[{index}]",
                work=link,
                bind=True,
                depends_on=tasks[-1] if tasks else None,
            )
            self.history.append(task)
            tasks.append(task)

        self.calls.record("tasks", "chain", description=description, length=len(tasks))
        if self.auto_run:
            for task in tasks:
                if task.depends_on is not None and task.depends_on.state != SUCCESS:
                    task.cancel()
                    continue
                task.run()
        else:
            self.queue.extend(tasks)
        return TaskChain(tasks)

    def group(self, works: List[Callable[..., Any]], description: str = "Group") -> TaskGroup:
        """Submit independent tasks; one failing says nothing about the others."""
        tasks = [
            self.submit(work, description=f"{description}[{index}]")
            for index, work in enumerate(works)
        ]
        self.calls.record("tasks", "group", description=description, length=len(tasks))
        return TaskGroup(tasks)

    def cancel(self, task: ScheduledTask) -> bool:
        """Cancel one scheduled task."""
        self.calls.record("tasks", "cancel", task_id=task.id)
        return task.cancel()

    @property
    def states(self) -> List[str]:
        """The state of every task this manager scheduled, in order."""
        return [task.state for task in self.history]

    # ── the celery-like facade (unchanged behaviour) ────────────────────────

    def add_task(self, task, *args, **kwargs):
        # Handle TaskWrapper
        if isinstance(task, FakeTaskWrapper):
            async_res = task.delay(*args, **kwargs)
            self.added_tasks.append(async_res._task)
            self.results.append(async_res)
            self.calls.record("tasks", "add", description=task.description)
            return async_res

        # Handle Signature
        if isinstance(task, FakeSignature):
            async_res = task.delay(*args, **kwargs)
            self.added_tasks.append(async_res._task)
            self.results.append(async_res)
            self.calls.record("tasks", "add", description=getattr(task.task, "description", "Task"))
            return async_res

        # Handle callable or FakeTask
        if callable(task) and not isinstance(task, FakeTask):
            description = kwargs.pop("description", "Task")
            on_finished = kwargs.pop("on_finished", None)
            bind = kwargs.pop("bind", False)
            t = FakeTask(description, task, *args, on_finished=on_finished, bind=bind, **kwargs)
        else:
            t = task

        self._tasks.append(t)
        self.added_tasks.append(t)
        self.calls.record("tasks", "add", description=t.description)

        # Execute immediately (synchronous for tests)
        result = FakeAsyncResult(t)
        self._tasks.remove(t)
        self.results.append(result)
        return result if isinstance(task, FakeTaskWrapper) or kwargs.get("return_async", True) else t

    def tasks(self):
        return list(self._tasks)

    def count(self):
        return len(self._tasks)

    def cancel_all(self):
        """Cancel everything still cancellable, on both surfaces."""
        for t in self._tasks:
            t.cancel()
        for task in list(self.queue):
            task.cancel()


# ── the celery-shaped facade ────────────────────────────────────────────────


class FakeTask:
    """Fake Task — celery-like + QGIS-like for testing without QGIS."""

    def __init__(self, description="Task", function=None, *args, on_finished=None, can_cancel=True, bind=False, **kwargs):
        self.description = description
        self._function = function
        self._args = args
        self._kwargs = kwargs
        self._on_finished = on_finished
        self._can_cancel = can_cancel
        self._bind = bind
        self._is_canceled = False
        self._is_finished = False
        self._progress = 0
        self._result = None
        self._exception = None
        self._id = str(uuid.uuid4())
        self._state = "PENDING"

    @property
    def id(self):
        return self._id

    @property
    def task_id(self):
        return self._id

    @property
    def state(self):
        return self._state

    @property
    def canonical_state(self) -> str:
        """This task's state in the five-name vocabulary doc-5 specifies."""
        return canonical_state(self._state)

    @property
    def status(self):
        return self._state

    def run(self):
        if self._function:
            try:
                sig = inspect.signature(self._function)
                params = list(sig.parameters.values())
                if self._bind or (params and params[0].name in ("task", "self", "celery_task", "qgis_task", "bind_task")):
                    return self._function(self, *self._args, **self._kwargs)
                else:
                    return self._function(*self._args, **self._kwargs)
            except Exception as e:
                raise e
        return True

    def set_progress(self, progress):
        self._progress = progress

    def setProgress(self, progress):  # noqa: N802 - PyQGIS naming
        self._progress = progress

    def progress(self):
        return self._progress

    def is_canceled(self):
        return self._is_canceled

    def isCanceled(self):  # noqa: N802 - PyQGIS naming
        return self._is_canceled

    def is_finished(self):
        return self._is_finished

    def isFinished(self):  # noqa: N802 - PyQGIS naming
        return self._is_finished

    def cancel(self):
        self._is_canceled = True
        self._state = "REVOKED"

    def can_cancel(self):
        return self._can_cancel

    def canCancel(self):  # noqa: N802 - PyQGIS naming
        return self._can_cancel

    def finished(self, result):
        pass

    def _execute(self):
        self._state = "STARTED"
        try:
            result = self.run()
            self._result = result
            self._is_finished = True
            self._state = "SUCCESS"
            if self._on_finished:
                try:
                    self._on_finished(None, result)
                except Exception:
                    pass
            return result
        except Exception as e:
            self._exception = e
            self._is_finished = True
            self._state = "FAILURE"
            if self._on_finished:
                try:
                    self._on_finished(e, None)
                except Exception:
                    pass
            return None

    def result(self):
        return self._result

    def exception(self):
        return self._exception

    @classmethod
    def from_function(cls, description, function, *args, on_finished=None, flags=None, bind=False, **kwargs):
        return cls(description, function, *args, on_finished=on_finished, bind=bind, **kwargs)

    # Celery-like API
    def delay(self, *args, **kwargs):
        # For FakeTask used as function wrapper, delay creates new task
        new_task = FakeTask(self.description, self._function, *args, on_finished=self._on_finished, bind=self._bind, **{**self._kwargs, **kwargs})
        return FakeAsyncResult(new_task)

    def apply_async(self, args=None, kwargs=None, **options):
        args = args or ()
        kwargs = kwargs or {}
        return self.delay(*args, **kwargs)


class FakeAsyncResult:
    """Fake AsyncResult — celery-like."""

    def __init__(self, task: FakeTask):
        self._task = task
        # Auto-execute for sync testing
        if not task.is_finished():
            task._execute()

    @property
    def id(self):
        return self._task.id

    @property
    def task_id(self):
        return self._task.id

    def get(self, timeout=None, propagate=True):
        if self._task._exception and propagate:
            raise self._task._exception
        return self._task._result

    def wait(self, timeout=None, propagate=True):
        return self.get(timeout=timeout, propagate=propagate)

    def ready(self):
        return self._task.is_finished()

    def successful(self):
        return self._task.is_finished() and self._task._exception is None

    def failed(self):
        return self._task.is_finished() and self._task._exception is not None

    @property
    def result(self):
        return self._task._result

    @property
    def state(self):
        return self._task._state

    @property
    def canonical_state(self) -> str:
        return canonical_state(self._task._state)

    @property
    def status(self):
        return self.state

    def revoke(self, terminate=False):
        self._task.cancel()

    def __repr__(self):
        return f"<FakeAsyncResult [{self.state}] id={self.id}>"


class FakeSignature:
    """Fake Signature — celery-like."""

    def __init__(self, task, args=(), kwargs=None, immutable=False, options=None):
        self.task = task
        self.args = args
        self.kwargs = kwargs or {}
        self.immutable = immutable
        self.options = options or {}

    def delay(self, *args, **kwargs):
        if self.immutable:
            return self.task.delay(*self.args, **self.kwargs)
        merged_args = self.args + args
        merged_kwargs = {**self.kwargs, **kwargs}
        return self.task.delay(*merged_args, **merged_kwargs)

    def apply_async(self, args=None, kwargs=None, **options):
        if self.immutable:
            return self.task.delay(*self.args, **self.kwargs)
        merged_args = self.args + (args or ())
        merged_kwargs = {**self.kwargs, **(kwargs or {})}
        return self.task.delay(*merged_args, **merged_kwargs)

    def __call__(self, *args, **kwargs):
        if self.immutable:
            return self.task._function(*self.args, **self.kwargs) if hasattr(self.task, "_function") else self.task(*self.args, **self.kwargs)
        merged_args = self.args + args
        merged_kwargs = {**self.kwargs, **kwargs}
        # Direct call
        if hasattr(self.task, "_function") and self.task._function:
            sig = inspect.signature(self.task._function)
            params = list(sig.parameters.values())
            if params and params[0].name in ("task", "self"):
                dummy = FakeTask()
                return self.task._function(dummy, *merged_args, **merged_kwargs)
            return self.task._function(*merged_args, **merged_kwargs)
        return self.task(*merged_args, **merged_kwargs)


class FakeTaskWrapper:
    """Fake TaskWrapper — celery-like decorator result for testing."""

    def __init__(self, func, description="Task", bind=False, can_cancel=True, on_finished=None):
        self.func = func
        self.description = description
        self.bind = bind
        self.can_cancel = can_cancel
        self.on_finished = on_finished
        self.name = getattr(func, "__name__", "task")

    def __call__(self, *args, **kwargs):
        sig = inspect.signature(self.func)
        params = list(sig.parameters.values())
        if self.bind or (params and params[0].name in ("task", "self")):
            dummy = FakeTask(description=self.description, bind=self.bind)
            return self.func(dummy, *args, **kwargs)
        return self.func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        task = FakeTask(self.description, self.func, *args, on_finished=self.on_finished, bind=self.bind, **kwargs)
        return FakeAsyncResult(task)

    def apply_async(self, args=None, kwargs=None, **options):
        args = args or ()
        kwargs = kwargs or {}
        return self.delay(*args, **kwargs)

    def s(self, *args, **kwargs):
        return FakeSignature(self, args, kwargs, immutable=False)

    def si(self, *args, **kwargs):
        return FakeSignature(self, args, kwargs, immutable=True)


def fake_task_manager_factory(**kwargs):
    return FakeTaskManager(**kwargs)


def fake_task_factory(description="Task", function=None, *args, **kwargs):
    return FakeTask(description, function, *args, **kwargs)


__all__ = [
    "PENDING",
    "RUNNING",
    "SUCCESS",
    "FAILURE",
    "CANCELED",
    "TASK_STATES",
    "TERMINAL_STATES",
    "LEGAL_TRANSITIONS",
    "CELERY_STATE_ALIASES",
    "IllegalTransition",
    "canonical_state",
    "ScheduledTask",
    "TaskChain",
    "TaskGroup",
    "FakeTaskManager",
    "FakeTask",
    "FakeAsyncResult",
    "FakeSignature",
    "FakeTaskWrapper",
    "fake_task_manager_factory",
    "fake_task_factory",
]
