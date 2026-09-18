"""
qgis_sdk.tasks — Pythonic wrapper around QgsTaskManager and QgsTask.

QGIS tasks run heavy work in background threads without freezing UI.
Global task manager: QgsApplication.taskManager() — handles progress,
cancellation, dependencies, and UI feedback.

Now with Celery-like API:

    from qgis_sdk.tasks import task, shared_task, TaskManager

    @task("My task", bind=True, can_cancel=True)
    def my_task(self, x, y):
        self.set_progress(50)
        if self.is_canceled():
            return None
        return x + y

    # Synchronous — like calling function directly (Celery direct call)
    result = my_task(4, 4)  # returns 8 immediately

    # Async — like Celery delay/apply_async
    async_result = my_task.delay(4, 4)
    print(async_result.get(timeout=10))  # waits, returns 8
    print(async_result.ready())
    print(async_result.successful())
    print(async_result.state)  # PENDING, SUCCESS, FAILURE, REVOKED

    # apply_async with more control
    async_result = my_task.apply_async(args=(4, 4), kwargs={}, countdown=1,
                                        description="Custom", on_finished=callback)

    # Signature / chain (Celery-like)
    sig = my_task.s(4, 4)
    result = sig.delay()
    # or immutable
    sig = my_task.si(4, 4)

    # TaskManager — QGIS global manager or ThreadPoolExecutor fallback
    TaskManager.instance().add_task(my_task.s(4, 4))

    # Old API still works
    from qgis_sdk.tasks import Task
    t = Task.from_function("My task", my_function, on_finished=callback)
    TaskManager.instance().add_task(t)

This module provides:
- Task wrapper around QgsTask with Pythonic API
- TaskManager wrapper around QgsApplication.taskManager()
- @task / @shared_task decorator with Celery-like delay/apply_async/get
- AsyncResult, Signature for Celery compatibility
- Fallback to ThreadPoolExecutor for testing without QGIS
"""

from __future__ import annotations

import concurrent.futures
import functools
import inspect
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# ── Lazy QGIS access ────────────────────────────────────────────────────────

def _get_qgis_task_manager():
    try:
        from qgis.core import QgsApplication  # type: ignore

        return QgsApplication.taskManager()
    except ImportError:
        return None


def _get_qgis_task_class():
    try:
        from qgis.core import QgsTask  # type: ignore

        return QgsTask
    except ImportError:
        return None


def _get_qgis_processing_task():
    try:
        from qgis.core import QgsProcessingAlgRunnerTask  # type: ignore

        return QgsProcessingAlgRunnerTask
    except ImportError:
        return None


# ── Fallback task implementation (no QGIS) ──────────────────────────────────

class _DummyTask:
    """Dummy task for synchronous execution — mimics QgsTask minimal API."""

    def __init__(self):
        self._progress = 0
        self._canceled = False

    def set_progress(self, progress: float):
        self._progress = progress

    def setProgress(self, progress: float):  # QGIS camelCase
        self._progress = progress

    def progress(self) -> float:
        return self._progress

    def is_canceled(self) -> bool:
        return self._canceled

    def isCanceled(self) -> bool:
        return self._canceled

    def is_finished(self) -> bool:
        return True

    def can_cancel(self) -> bool:
        return True


class _FallbackTask:
    """Fallback task that runs in ThreadPoolExecutor — for testing without QGIS."""

    def __init__(
        self,
        description: str,
        function: Optional[Callable] = None,
        *args,
        on_finished: Optional[Callable] = None,
        can_cancel: bool = True,
        bind: bool = False,
        **kwargs,
    ):
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
        self._exception: Optional[Exception] = None
        self._future: Optional[concurrent.futures.Future] = None
        self._progress_callbacks: List[Callable[[float], None]] = []
        self._finished_callbacks: List[Callable] = []
        self._id = str(uuid.uuid4())

    @property
    def id(self):
        return self._id

    def run(self):
        """Run task — to be overridden by subclass."""
        if self._function:
            try:
                # Handle bind logic: if bind=True, first arg is task
                # If function signature first param is task/self and bind not explicitly False, pass self
                sig = inspect.signature(self._function)
                params = list(sig.parameters.values())
                if self._bind or (params and params[0].name in ("task", "self", "celery_task", "qgis_task")):
                    return self._function(self, *self._args, **self._kwargs)
                else:
                    return self._function(*self._args, **self._kwargs)
            except Exception as e:
                raise e
        return True

    def set_progress(self, progress: float):
        self._progress = progress
        for cb in self._progress_callbacks:
            try:
                cb(progress)
            except Exception:
                pass

    def setProgress(self, progress: float):
        self.set_progress(progress)

    def progress(self) -> float:
        return self._progress

    def is_canceled(self) -> bool:
        return self._is_canceled

    def isCanceled(self) -> bool:
        return self._is_canceled

    def is_finished(self) -> bool:
        return self._is_finished

    def isFinished(self) -> bool:
        return self._is_finished

    def cancel(self):
        self._is_canceled = True
        if self._future:
            self._future.cancel()

    def can_cancel(self) -> bool:
        return self._can_cancel

    def canCancel(self) -> bool:
        return self._can_cancel

    def finished(self, result: Any):
        """Called when task finishes — to be overridden."""
        pass

    def _execute(self):
        """Execute task and handle callbacks."""
        try:
            result = self.run()
            self._result = result
            self._is_finished = True
            if self._on_finished:
                try:
                    self._on_finished(None, result)
                except Exception:
                    pass
            try:
                self.finished(result)
            except Exception:
                pass
            for cb in self._finished_callbacks:
                try:
                    cb(None, result)
                except Exception:
                    pass
            return result
        except Exception as e:
            self._exception = e
            self._is_finished = True
            if self._on_finished:
                try:
                    self._on_finished(e, None)
                except Exception:
                    pass
            try:
                self.finished(None)
            except Exception:
                pass
            for cb in self._finished_callbacks:
                try:
                    cb(e, None)
                except Exception:
                    pass
            return None

    def result(self):
        return self._result

    def exception(self):
        return self._exception

    @classmethod
    def from_function(
        cls,
        description: str,
        function: Callable,
        *args,
        on_finished: Optional[Callable] = None,
        flags: Any = None,
        bind: bool = False,
        **kwargs,
    ) -> "_FallbackTask":
        can_cancel = True
        if flags is not None:
            try:
                from qgis.core import QgsTask  # type: ignore

                if flags == QgsTask.CanCancel or (hasattr(flags, "__and__") and flags & QgsTask.CanCancel):
                    can_cancel = True
                elif flags == 0:
                    can_cancel = False
            except ImportError:
                pass
        return cls(description, function, *args, on_finished=on_finished, can_cancel=can_cancel, bind=bind, **kwargs)


class _FallbackTaskManager:
    """Fallback task manager using ThreadPoolExecutor — for testing without QGIS."""

    def __init__(self, max_workers: int = 4):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._tasks: List[_FallbackTask] = []
        self._lock = threading.Lock()

    def add_task(self, task: Union[_FallbackTask, Callable], *args, **kwargs) -> _FallbackTask:
        """Add task — accepts Task instance or function."""
        if callable(task) and not isinstance(task, _FallbackTask):
            description = kwargs.pop("description", "Task")
            on_finished = kwargs.pop("on_finished", None)
            bind = kwargs.pop("bind", False)
            t = _FallbackTask(description, task, *args, on_finished=on_finished, bind=bind, **kwargs)
        else:
            t = task

        with self._lock:
            self._tasks.append(t)

        future = self._executor.submit(t._execute)
        t._future = future

        def _remove_on_done(f):
            with self._lock:
                if t in self._tasks:
                    self._tasks.remove(t)

        future.add_done_callback(_remove_on_done)

        return t

    def tasks(self) -> List[_FallbackTask]:
        with self._lock:
            return list(self._tasks)

    def count(self) -> int:
        with self._lock:
            return len(self._tasks)

    def cancel_all(self):
        with self._lock:
            for t in self._tasks:
                t.cancel()

    def shutdown(self, wait: bool = True):
        self._executor.shutdown(wait=wait)


# ── AsyncResult (Celery-like) ───────────────────────────────────────────────

class AsyncResult:
    """
    Celery-like AsyncResult for QGIS tasks.

    Example:
        result = my_task.delay(4, 4)
        print(result.get(timeout=10))
        print(result.ready())
        print(result.successful())
        print(result.state)
        print(result.result)
        print(result.id)

        # Wait
        result.wait(timeout=5)
        result.get(propagate=False)

        # Revoke/cancel
        result.revoke()
    """

    def __init__(self, task_obj: Union["Task", _FallbackTask, Any], task_id: Optional[str] = None):
        self._task = task_obj
        self._task_id = task_id or getattr(task_obj, "id", None) or str(uuid.uuid4())
        self._result = None
        self._exception: Optional[Exception] = None

    @property
    def id(self) -> str:
        # Try to get from underlying task
        if hasattr(self._task, "id"):
            try:
                return self._task.id
            except Exception:
                pass
        if hasattr(self._task, "fallback_task") and self._task.fallback_task:
            return self._task.fallback_task.id
        return self._task_id

    @property
    def task_id(self) -> str:
        return self.id

    def _get_underlying(self) -> Tuple[Optional[Any], bool, Optional[Any], Optional[Exception]]:
        """Return (result, is_finished, exception, task_obj)"""
        task = self._task

        # If task is our wrapper Task
        if isinstance(task, Task):
            if task.fallback_task:
                ft = task.fallback_task
                return ft.result(), ft.is_finished(), ft.exception(), ft
            if task.qgis_task:
                # QGIS task — try to get result via status
                # QGIS QgsTask doesn't store result directly, but we can check status
                try:
                    is_finished = task.is_finished()
                    # For QGIS, result is not directly available unless stored via on_finished
                    # We'll try to get from wrapper if available
                    return getattr(task, "_result", None), is_finished, getattr(task, "_exception", None), task.qgis_task
                except Exception:
                    pass
            return None, False, None, task

        if isinstance(task, _FallbackTask):
            return task.result(), task.is_finished(), task.exception(), task

        # If task is _FallbackTask directly or has future
        if hasattr(task, "_future"):
            try:
                # If future done, get result
                if task._future and task._future.done():
                    try:
                        res = task._future.result(timeout=0)
                        return res, True, None, task
                    except Exception as e:
                        return None, True, e, task
            except Exception:
                pass

        return None, False, None, task

    def get(self, timeout: Optional[float] = None, propagate: bool = True) -> Any:
        """
        Wait for task and return result — like Celery AsyncResult.get().
        """
        start = time.time()
        while True:
            result, is_finished, exception, _ = self._get_underlying()
            if is_finished:
                self._result = result
                self._exception = exception
                if exception and propagate:
                    raise exception
                return result
            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError(f"Task {self.id} timed out after {timeout}s")
            time.sleep(0.05)

    def wait(self, timeout: Optional[float] = None, propagate: bool = True) -> Any:
        """Alias for get() — Celery compatibility."""
        return self.get(timeout=timeout, propagate=propagate)

    def ready(self) -> bool:
        """Return True if task has finished — like Celery."""
        _, is_finished, _, _ = self._get_underlying()
        return is_finished

    def successful(self) -> bool:
        """Return True if task succeeded — like Celery."""
        result, is_finished, exception, _ = self._get_underlying()
        return is_finished and exception is None

    def failed(self) -> bool:
        """Return True if task failed."""
        _, is_finished, exception, _ = self._get_underlying()
        return is_finished and exception is not None

    @property
    def result(self) -> Any:
        result, _, _, _ = self._get_underlying()
        return result

    @property
    def state(self) -> str:
        _, is_finished, exception, _ = self._get_underlying()
        if not is_finished:
            return "PENDING"
        if exception is not None:
            return "FAILURE"
        return "SUCCESS"

    @property
    def status(self) -> str:
        return self.state

    def revoke(self, terminate: bool = False):
        """Cancel task — like Celery revoke."""
        task = self._task
        try:
            if hasattr(task, "cancel"):
                task.cancel()
            if hasattr(task, "fallback_task") and task.fallback_task:
                task.fallback_task.cancel()
        except Exception:
            pass

    def __repr__(self):
        return f"<AsyncResult [{self.state}] id={self.id}>"


# ── Signature (Celery-like) ─────────────────────────────────────────────────

class Signature:
    """
    Celery-like signature for chaining tasks.

    Example:
        sig = my_task.s(4, 4)
        result = sig.delay()
        result.get()

        # Immutable
        sig = my_task.si(4, 4)
        sig.apply_async()

        # Chain (simplified)
        chain = (my_task.s(4, 4) | my_other_task.s())
        result = chain()
    """

    def __init__(self, task_wrapper: "TaskWrapper", args: Tuple = (), kwargs: Optional[Dict] = None, immutable: bool = False, options: Optional[Dict] = None):
        self.task = task_wrapper
        self.args = args
        self.kwargs = kwargs or {}
        self.immutable = immutable
        self.options = options or {}

    def delay(self, *args, **kwargs) -> AsyncResult:
        # If immutable, ignore new args
        if self.immutable:
            return self.task.delay(*self.args, **self.kwargs)
        # Merge
        merged_args = self.args + args
        merged_kwargs = {**self.kwargs, **kwargs}
        return self.task.delay(*merged_args, **merged_kwargs)

    def apply_async(self, args=None, kwargs=None, **options) -> AsyncResult:
        if self.immutable:
            return self.task.apply_async(args=self.args, kwargs=self.kwargs, **{**self.options, **options})
        merged_args = self.args + (args or ())
        merged_kwargs = {**self.kwargs, **(kwargs or {})}
        merged_options = {**self.options, **options}
        return self.task.apply_async(args=merged_args, kwargs=merged_kwargs, **merged_options)

    def __call__(self, *args, **kwargs) -> Any:
        # Synchronous execution via signature
        if self.immutable:
            return self.task(*self.args, **self.kwargs)
        merged_args = self.args + args
        merged_kwargs = {**self.kwargs, **kwargs}
        return self.task(*merged_args, **merged_kwargs)

    def __or__(self, other: "Signature") -> "Chain":
        return Chain(self, other)

    def clone(self, args=None, kwargs=None, **opts) -> "Signature":
        new_args = args if args is not None else self.args
        new_kwargs = kwargs if kwargs is not None else self.kwargs
        new_opts = {**self.options, **opts}
        return Signature(self.task, new_args, new_kwargs, self.immutable, new_opts)


class Chain:
    """Simple chain of signatures — Celery-like.

    Previous result is passed as first arg to next task, plus signature args.
    Example: chain(add.s(2,2), add.s(3)) -> add(2,2)=4, then add(4,3)=7
    """

    def __init__(self, *signatures: Signature):
        self.signatures = list(signatures)

    def __or__(self, other: Union[Signature, "Chain"]) -> "Chain":
        if isinstance(other, Chain):
            return Chain(*self.signatures, *other.signatures)
        return Chain(*self.signatures, other)

    def _execute_sig(self, sig: Signature, prev_result: Any) -> Any:
        if not isinstance(sig, Signature):
            # TaskWrapper or callable
            if prev_result is None:
                return sig() if callable(sig) else sig
            else:
                # Try calling with prev_result as first arg
                try:
                    return sig(prev_result)
                except TypeError:
                    return sig()

        if prev_result is None:
            return sig()

        if sig.immutable:
            return sig()

        # Celery-like: previous result as first arg, plus signature args
        try:
            return sig.task(prev_result, *sig.args, **sig.kwargs)
        except TypeError:
            # Fallback: try with only prev_result
            try:
                return sig.task(prev_result)
            except TypeError:
                return sig()

    def delay(self) -> AsyncResult:
        result = None
        for sig in self.signatures:
            result = self._execute_sig(sig, result)
        dummy_task = _FallbackTask("Chain", lambda: result)
        dummy_task._result = result
        dummy_task._is_finished = True
        return AsyncResult(dummy_task)

    def __call__(self) -> Any:
        result = None
        for sig in self.signatures:
            result = self._execute_sig(sig, result)
        return result


# ── TaskWrapper (Celery-like decorator result) ──────────────────────────────

class TaskWrapper:
    """
    Celery-like task wrapper returned by @task decorator.

    Provides:
    - Direct call: my_task(4, 4) → synchronous result
    - delay: my_task.delay(4, 4) → AsyncResult
    - apply_async: my_task.apply_async(args=(4,4), kwargs={}, countdown=1)
    - s/si: signature creation
    - run: underlying function
    - name, description
    """

    def __init__(
        self,
        func: Callable,
        description: str = "Task",
        bind: bool = False,
        can_cancel: bool = True,
        on_finished: Optional[Callable] = None,
        flags: Any = None,
        base: Optional[type] = None,
    ):
        self.func = func
        self.description = description
        self.bind = bind
        self.can_cancel = can_cancel
        self.on_finished = on_finished
        self.flags = flags
        self.base = base
        self.name = getattr(func, "__name__", "task")
        self.__name__ = self.name
        self.__doc__ = getattr(func, "__doc__", None)
        functools.update_wrapper(self, func)
        self._original_function = func

    def __call__(self, *args, **kwargs) -> Any:
        """Synchronous execution — like Celery task direct call."""
        dummy = _DummyTask()
        try:
            sig = inspect.signature(self.func)
            params = list(sig.parameters.values())
            if self.bind or (params and params[0].name in ("task", "self", "celery_task", "qgis_task", "bind_task")):
                return self.func(dummy, *args, **kwargs)
            else:
                return self.func(*args, **kwargs)
        except Exception as e:
            raise e

    def run(self, *args, **kwargs) -> Any:
        """Alias for direct call — Celery compatibility."""
        return self.__call__(*args, **kwargs)

    def delay(self, *args, **kwargs) -> AsyncResult:
        """Async execution — like Celery delay()."""
        return self.apply_async(args=args, kwargs=kwargs)

    def apply_async(
        self,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
        description: Optional[str] = None,
        on_finished: Optional[Callable] = None,
        countdown: Optional[float] = None,
        eta: Optional[Any] = None,
        bind: Optional[bool] = None,
        **options,
    ) -> AsyncResult:
        """
        Async execution with options — like Celery apply_async.

        Args:
            args: positional args for task
            kwargs: keyword args for task
            description: task description override
            on_finished: callback(exception, result)
            countdown: seconds to wait before starting (simple sleep)
            eta: not implemented, for compatibility
            bind: override bind setting
        """
        args = args or ()
        kwargs = kwargs or {}
        desc = description or self.description
        cb = on_finished or self.on_finished
        use_bind = bind if bind is not None else self.bind

        if countdown:
            time.sleep(countdown)

        # Create Task via from_function
        task_obj = Task.from_function(desc, self.func, *args, on_finished=cb, flags=self.flags, bind=use_bind, **kwargs)
        added = TaskManager.instance().add_task(task_obj)
        return AsyncResult(added)

    def s(self, *args, **kwargs) -> Signature:
        """Create signature — like Celery s()."""
        return Signature(self, args, kwargs, immutable=False)

    def si(self, *args, **kwargs) -> Signature:
        """Create immutable signature — like Celery si()."""
        return Signature(self, args, kwargs, immutable=True)

    def signature(self, args=None, kwargs=None, immutable=False, **options) -> Signature:
        return Signature(self, args or (), kwargs or {}, immutable=immutable, options=options)

    @property
    def original_func(self):
        return self.func


# ── Task wrapper (QGIS + fallback) ──────────────────────────────────────────

class Task:
    """
    Wrapper around QgsTask — runs heavy work in background.

    When QGIS available, uses QgsTask and QgsApplication.taskManager().
    Otherwise, falls back to ThreadPoolExecutor.

    Now also supports Celery-like API via TaskWrapper.

    Example:
        def do_work(task, wait_time):
            for i in range(100):
                time.sleep(wait_time / 100.0)
                task.set_progress(i)
                if task.is_canceled():
                    return None
            return {"result": 42}

        def on_finished(exception, result):
            print(f"Done: {result}, exception: {exception}")

        task = Task.from_function("My task", do_work, wait_time=2, on_finished=on_finished)
        TaskManager.instance().add_task(task)

        # Celery-like
        @task("My task", bind=True)
        def my_task(self, x, y):
            return x + y

        result = my_task.delay(4, 4)
        print(result.get())
    """

    def __init__(self, description: str, flags: Any = None, bind: bool = False):
        self.description = description
        self._qgis_task = None
        self._fallback_task: Optional[_FallbackTask] = None
        self._on_finished: Optional[Callable] = None
        self._result: Optional[Any] = None
        self._exception: Optional[Exception] = None
        self._bind = bind

        QgsTask = _get_qgis_task_class()
        if QgsTask:
            try:
                if flags is not None:
                    self._qgis_task = QgsTask(description, flags)
                else:
                    self._qgis_task = QgsTask(description)
            except Exception:
                self._qgis_task = None

        if self._qgis_task is None:
            self._fallback_task = _FallbackTask(description, bind=bind)

    @classmethod
    def from_function(
        cls,
        description: str,
        function: Callable,
        *args,
        on_finished: Optional[Callable] = None,
        flags: Any = None,
        bind: bool = False,
        **kwargs,
    ) -> "Task":
        """
        Create task from function.

        Function signature: def function(task, *args, **kwargs) -> Any
        on_finished signature: def on_finished(exception, result)

        Example:
            def run(task, wait_time):
                for i in range(100):
                    task.set_progress(i)
                    if task.is_canceled():
                        return None
                return 42

            task = Task.from_function("My task", run, wait_time=2, on_finished=lambda e, r: print(r))
        """
        QgsTask = _get_qgis_task_class()
        if QgsTask:
            try:
                qgis_task = QgsTask.fromFunction(description, function, *args, on_finished=on_finished, flags=flags or 0, **kwargs)
                wrapper = cls.__new__(cls)
                wrapper.description = description
                wrapper._qgis_task = qgis_task
                wrapper._fallback_task = None
                wrapper._on_finished = on_finished
                wrapper._result = None
                wrapper._exception = None
                wrapper._bind = bind
                return wrapper
            except Exception as e:
                print(f"[Task] QGIS fromFunction failed, using fallback: {e}")

        wrapper = cls.__new__(cls)
        wrapper.description = description
        wrapper._qgis_task = None
        wrapper._fallback_task = _FallbackTask.from_function(description, function, *args, on_finished=on_finished, flags=flags, bind=bind, **kwargs)
        wrapper._on_finished = on_finished
        wrapper._result = None
        wrapper._exception = None
        wrapper._bind = bind
        return wrapper

    def run(self) -> Any:
        """Override in subclass — heavy work."""
        if self._fallback_task:
            return self._fallback_task.run()
        if self._qgis_task:
            return True
        return True

    def finished(self, result: Any):
        """Override in subclass — called when task finishes."""
        if self._fallback_task:
            self._fallback_task.finished(result)

    def set_progress(self, progress: float):
        if self._qgis_task and hasattr(self._qgis_task, "setProgress"):
            try:
                self._qgis_task.setProgress(progress)
                return
            except Exception:
                pass
        if self._fallback_task:
            self._fallback_task.set_progress(progress)

    def setProgress(self, progress: float):
        self.set_progress(progress)

    def progress(self) -> float:
        if self._qgis_task and hasattr(self._qgis_task, "progress"):
            try:
                return self._qgis_task.progress()
            except Exception:
                pass
        if self._fallback_task:
            return self._fallback_task.progress()
        return 0

    def is_canceled(self) -> bool:
        if self._qgis_task and hasattr(self._qgis_task, "isCanceled"):
            try:
                return self._qgis_task.isCanceled()
            except Exception:
                pass
        if self._fallback_task:
            return self._fallback_task.is_canceled()
        return False

    def isCanceled(self) -> bool:
        return self.is_canceled()

    def is_finished(self) -> bool:
        if self._qgis_task and hasattr(self._qgis_task, "isFinished"):
            try:
                return self._qgis_task.status() == self._qgis_task.Complete or self._qgis_task.isFinished()
            except Exception:
                pass
        if self._fallback_task:
            return self._fallback_task.is_finished()
        return False

    def isFinished(self) -> bool:
        return self.is_finished()

    def cancel(self):
        if self._qgis_task and hasattr(self._qgis_task, "cancel"):
            try:
                self._qgis_task.cancel()
                return
            except Exception:
                pass
        if self._fallback_task:
            self._fallback_task.cancel()

    def can_cancel(self) -> bool:
        if self._qgis_task and hasattr(self._qgis_task, "canCancel"):
            try:
                return self._qgis_task.canCancel()
            except Exception:
                pass
        if self._fallback_task:
            return self._fallback_task.can_cancel()
        return True

    def canCancel(self) -> bool:
        return self.can_cancel()

    @property
    def qgis_task(self):
        return self._qgis_task

    @property
    def fallback_task(self):
        return self._fallback_task

    @property
    def id(self):
        if self._fallback_task:
            return self._fallback_task.id
        if self._qgis_task and hasattr(self._qgis_task, "id"):
            try:
                return self._qgis_task.id()
            except Exception:
                pass
        return str(id(self))


# ── TaskManager wrapper ─────────────────────────────────────────────────────

class TaskManager:
    """
    Wrapper around QgsApplication.taskManager() — global task manager.

    When QGIS available, uses QgsApplication.taskManager().
    Otherwise, falls back to ThreadPoolExecutor.

    Example:
        mgr = TaskManager.instance()
        task = Task.from_function("My task", my_function)
        mgr.add_task(task)
        print(f"Running tasks: {mgr.count()}")

        # With decorator (Celery-like)
        @task("My task")
        def my_task(self, x, y):
            return x + y

        result = my_task.delay(4, 4)
        print(result.get())
    """

    _instance: Optional["TaskManager"] = None

    def __init__(self, max_workers: int = 4):
        self._qgis_manager = _get_qgis_task_manager()
        self._fallback_manager: Optional[_FallbackTaskManager] = None

        if self._qgis_manager is None:
            self._fallback_manager = _FallbackTaskManager(max_workers=max_workers)

    @classmethod
    def instance(cls, max_workers: int = 4) -> "TaskManager":
        if cls._instance is None:
            cls._instance = cls(max_workers=max_workers)
        return cls._instance

    def add_task(self, task: Union[Task, Callable, _FallbackTask, TaskWrapper, Signature], *args, **kwargs) -> Union[Task, _FallbackTask, AsyncResult]:
        """
        Add task to manager — supports Task, callable, TaskWrapper, Signature.

        Returns Task or AsyncResult.
        """
        # Handle Signature
        if isinstance(task, Signature):
            return task.apply_async()

        # Handle TaskWrapper — create task and add
        if isinstance(task, TaskWrapper):
            # If args/kwargs provided, use them
            return task.apply_async(args=args, kwargs=kwargs, **kwargs)

        # If task is our wrapper Task
        if isinstance(task, Task):
            if self._qgis_manager and task.qgis_task:
                try:
                    self._qgis_manager.addTask(task.qgis_task)
                    return task
                except Exception as e:
                    print(f"[TaskManager] QGIS addTask failed, using fallback: {e}")

            if self._fallback_manager:
                if task.fallback_task:
                    return self._fallback_manager.add_task(task.fallback_task)
                else:
                    fallback = _FallbackTask(task.description, task.run, on_finished=kwargs.get("on_finished"), bind=task._bind)
                    return self._fallback_manager.add_task(fallback)

            return task

        if self._qgis_manager:
            if callable(task) and not isinstance(task, _FallbackTask):
                QgsTask = _get_qgis_task_class()
                if QgsTask:
                    try:
                        description = kwargs.pop("description", "Task")
                        on_finished = kwargs.pop("on_finished", None)
                        qgis_task = QgsTask.fromFunction(description, task, *args, on_finished=on_finished, **kwargs)
                        self._qgis_manager.addTask(qgis_task)
                        wrapper = Task.__new__(Task)
                        wrapper.description = description
                        wrapper._qgis_task = qgis_task
                        wrapper._fallback_task = None
                        wrapper._on_finished = on_finished
                        wrapper._result = None
                        wrapper._exception = None
                        wrapper._bind = kwargs.get("bind", False)
                        return wrapper
                    except Exception as e:
                        print(f"[TaskManager] QGIS fromFunction failed, using fallback: {e}")

        if self._fallback_manager:
            return self._fallback_manager.add_task(task, *args, **kwargs)

        if callable(task):
            try:
                task(*args, **kwargs)
            except Exception:
                pass
        return task

    def tasks(self) -> List[Any]:
        if self._qgis_manager and hasattr(self._qgis_manager, "tasks"):
            try:
                return self._qgis_manager.tasks()
            except Exception:
                pass
        if self._fallback_manager:
            return self._fallback_manager.tasks()
        return []

    def count(self) -> int:
        if self._qgis_manager:
            try:
                return len(self._qgis_manager.tasks())
            except Exception:
                pass
        if self._fallback_manager:
            return self._fallback_manager.count()
        return 0

    def cancel_all(self):
        if self._qgis_manager and hasattr(self._qgis_manager, "cancelAll"):
            try:
                self._qgis_manager.cancelAll()
                return
            except Exception:
                pass
        if self._fallback_manager:
            self._fallback_manager.cancel_all()

    def shutdown(self, wait: bool = True):
        if self._fallback_manager:
            self._fallback_manager.shutdown(wait=wait)

    @property
    def qgis_manager(self):
        return self._qgis_manager

    @property
    def fallback_manager(self):
        return self._fallback_manager


# ── Decorator (Celery-like) ─────────────────────────────────────────────────

def task(
    _func: Optional[Callable] = None,
    description: str = "Task",
    bind: bool = False,
    can_cancel: bool = True,
    on_finished: Optional[Callable] = None,
    flags: Any = None,
    base: Optional[type] = None,
) -> Union[TaskWrapper, Callable[[Callable], TaskWrapper]]:
    """
    Decorator to create a task from function — Celery-like.

    Can be used with or without arguments:

        @task
        def my_task(x, y):
            return x + y

        @task("My heavy work", bind=True, can_cancel=True)
        def my_task(self, x, y):
            self.set_progress(50)
            if self.is_canceled():
                return None
            return x + y

        # Synchronous
        result = my_task(4, 4)

        # Async (Celery-like)
        async_result = my_task.delay(4, 4)
        print(async_result.get())

        async_result = my_task.apply_async(args=(4, 4), countdown=1)
        print(async_result.ready())

        # Signature
        sig = my_task.s(4, 4)
        sig.delay()

    Args:
        description: task description (QGIS task description)
        bind: if True, first arg is task instance (like Celery bind=True)
        can_cancel: if task can be canceled
        on_finished: callback(exception, result)
        flags: QGIS task flags
        base: base class for task (not used in fallback, for QGIS compatibility)

    Returns:
        TaskWrapper with delay/apply_async/s/si methods
    """

    def decorator(func: Callable) -> TaskWrapper:
        # If description is actually function (when used as @task without parens)
        # Handle that case
        desc = description
        if callable(desc) and not isinstance(desc, str):
            # This case shouldn't happen here, but handle
            pass

        # Determine bind automatically if not specified and first param is task-like
        use_bind = bind
        if not bind:
            try:
                sig = inspect.signature(func)
                params = list(sig.parameters.values())
                if params and params[0].name in ("task", "self", "celery_task", "qgis_task", "bind_task"):
                    # Auto-bind if first param looks like task
                    use_bind = True
            except Exception:
                pass

        wrapper = TaskWrapper(
            func=func,
            description=desc if isinstance(desc, str) else getattr(func, "__name__", "Task"),
            bind=use_bind,
            can_cancel=can_cancel,
            on_finished=on_finished,
            flags=flags,
            base=base,
        )
        return wrapper

    if _func is not None and callable(_func):
        # Used as @task without parentheses
        return decorator(_func)

    return decorator


# Alias for Celery compatibility
shared_task = task
celery_task = task


class _CeleryApp:
    """Minimal Celery-like app for @app.task decorator."""

    def task(self, *args, **kwargs):
        return task(*args, **kwargs)

    def shared_task(self, *args, **kwargs):
        return task(*args, **kwargs)


# Global app instance — like Celery app
app = _CeleryApp()
celery_app = app


# ── Processing Alg Runner Task ──────────────────────────────────────────────

class ProcessingAlgRunnerTask:
    """
    Wrapper around QgsProcessingAlgRunnerTask — runs processing alg in background.

    Example:
        from qgis.core import QgsProcessingContext, QgsProcessingFeedback
        from qgis_sdk.tasks import ProcessingAlgRunnerTask, TaskManager

        context = QgsProcessingContext()
        feedback = QgsProcessingFeedback()
        params = {...}
        task = ProcessingAlgRunnerTask("qgis:randompointsinextent", params, context, feedback)
        task.executed.connect(lambda successful, results: print(results))
        TaskManager.instance().add_task(task)
    """

    def __init__(self, alg_id_or_instance: Union[str, Any], params: Dict[str, Any], context: Any, feedback: Any, on_executed: Optional[Callable] = None):
        self.alg_id_or_instance = alg_id_or_instance
        self.params = params
        self.context = context
        self.feedback = feedback
        self._qgis_task = None
        self._fallback_task = None

        QgsProcessingTask = _get_qgis_processing_task()
        if QgsProcessingTask:
            try:
                if isinstance(alg_id_or_instance, str):
                    from qgis.core import QgsApplication  # type: ignore

                    alg = QgsApplication.processingRegistry().algorithmById(alg_id_or_instance)
                    if alg is None:
                        raise ValueError(f"Algorithm not found: {alg_id_or_instance}")
                else:
                    alg = alg_id_or_instance

                self._qgis_task = QgsProcessingTask(alg, params, context, feedback)
                if on_executed and hasattr(self._qgis_task, "executed"):
                    self._qgis_task.executed.connect(on_executed)
            except Exception as e:
                print(f"[ProcessingAlgRunnerTask] QGIS task creation failed: {e}")
                self._qgis_task = None

        if self._qgis_task is None:

            def _run(task):
                time.sleep(0.1)
                return self.params

            self._fallback_task = _FallbackTask(
                f"Processing {alg_id_or_instance}", _run, on_finished=lambda e, r: on_executed(True, r) if on_executed and e is None else None
            )

    def add_to_manager(self, manager: Optional[TaskManager] = None):
        mgr = manager or TaskManager.instance()
        if self._qgis_task:
            if mgr.qgis_manager:
                mgr.qgis_manager.addTask(self._qgis_task)
                return self
        if self._fallback_task and mgr.fallback_manager:
            mgr.fallback_manager.add_task(self._fallback_task)
        return self

    @property
    def qgis_task(self):
        return self._qgis_task

    @property
    def fallback_task(self):
        return self._fallback_task

    @property
    def executed(self):
        if self._qgis_task and hasattr(self._qgis_task, "executed"):
            return self._qgis_task.executed

        class _MockSignal:
            def __init__(self):
                self._cbs = []

            def connect(self, cb):
                self._cbs.append(cb)

        return _MockSignal()

    def delay(self) -> AsyncResult:
        """Celery-like delay for processing task."""
        mgr = TaskManager.instance()
        if self._qgis_task and mgr.qgis_manager:
            mgr.qgis_manager.addTask(self._qgis_task)
            # Create dummy AsyncResult
            dummy = _FallbackTask(f"Processing {self.alg_id_or_instance}", lambda: self.params)
            dummy._result = self.params
            dummy._is_finished = True
            return AsyncResult(dummy)
        if self._fallback_task and mgr.fallback_manager:
            added = mgr.fallback_manager.add_task(self._fallback_task)
            return AsyncResult(added)
        return AsyncResult(self._fallback_task)

    def apply_async(self, **kwargs) -> AsyncResult:
        return self.delay()


# ── Convenience functions ───────────────────────────────────────────────────

def run_task(function: Callable, *args, description: str = "Task", on_finished: Optional[Callable] = None, bind: bool = False, **kwargs) -> Union[Task, _FallbackTask, AsyncResult]:
    """Convenience: create task from function and add to manager — returns AsyncResult."""
    task_obj = Task.from_function(description, function, *args, on_finished=on_finished, bind=bind, **kwargs)
    added = TaskManager.instance().add_task(task_obj)
    if isinstance(added, (Task, _FallbackTask)):
        return AsyncResult(added)
    return added


def add_task(task: Union[Task, Callable, TaskWrapper, Signature], *args, **kwargs) -> Union[Task, _FallbackTask, AsyncResult]:
    """Convenience: add task to global manager — Celery-like, returns AsyncResult if TaskWrapper."""
    result = TaskManager.instance().add_task(task, *args, **kwargs)
    if isinstance(result, AsyncResult):
        return result
    if isinstance(task, (TaskWrapper, Signature)):
        # Already returns AsyncResult from add_task, but fallback
        return result
    # For backwards compat, if result is Task, wrap in AsyncResult for celery-like usage
    if isinstance(result, (Task, _FallbackTask)):
        return AsyncResult(result)
    return result


def cancel_all():
    """Cancel all tasks."""
    TaskManager.instance().cancel_all()


# ── Celery-like helpers ─────────────────────────────────────────────────────

def chain(*tasks: Union[Signature, TaskWrapper]) -> Chain:
    """Create chain of tasks — Celery-like."""
    sigs = []
    for t in tasks:
        if isinstance(t, TaskWrapper):
            sigs.append(t.s())
        elif isinstance(t, Signature):
            sigs.append(t)
        else:
            # Assume callable
            sigs.append(t)
    return Chain(*sigs)


def group(*tasks: Union[Signature, TaskWrapper]) -> List[AsyncResult]:
    """Create group of tasks — simplified Celery-like, returns list of AsyncResults."""
    results = []
    for t in tasks:
        if isinstance(t, TaskWrapper):
            results.append(t.delay())
        elif isinstance(t, Signature):
            results.append(t.delay())
        elif callable(t):
            # Wrap
            results.append(TaskManager.instance().add_task(t))
    return results


__all__ = [
    "Task",
    "TaskManager",
    "ProcessingAlgRunnerTask",
    "TaskWrapper",
    "AsyncResult",
    "Signature",
    "Chain",
    "task",
    "shared_task",
    "celery_task",
    "app",
    "celery_app",
    "run_task",
    "add_task",
    "cancel_all",
    "chain",
    "group",
]
