"""Tests for qgis_sdk.tasks — Celery-like API + QGIS TaskManager wrapper.

Uses project's own testing fixtures: fake_task_manager, fake_task, fake_async_result,
fake_task_wrapper, fake_iface, fake_action_factory.
"""

from __future__ import annotations

import time

import pytest

pytest_plugins = ["qgis_sdk.testing"]


# ── TaskManager ─────────────────────────────────────────────────────────────

def test_task_manager_fallback():
    from qgis_sdk.tasks import TaskManager

    mgr = TaskManager.instance()
    assert hasattr(mgr, "add_task")
    assert hasattr(mgr, "tasks")
    assert hasattr(mgr, "count")
    assert hasattr(mgr, "cancel_all")

    mgr2 = TaskManager.instance()
    assert mgr is mgr2


def test_task_from_function():
    from qgis_sdk.tasks import Task

    def do_work(task, wait_time=0):
        for i in range(5):
            task.set_progress(i * 20)
            if task.is_canceled():
                return None
        return {"result": 42}

    results = []

    def on_finished(exception, result):
        results.append((exception, result))

    task = Task.from_function("My task", do_work, wait_time=0, on_finished=on_finished, bind=True)
    assert task.description == "My task"
    assert hasattr(task, "set_progress")
    assert hasattr(task, "is_canceled")


# ── Celery-like API ─────────────────────────────────────────────────────────

def test_task_decorator_celery_like(fake_task_manager):
    """Test @task decorator with celery-like delay/apply_async — uses fake_task_manager fixture."""
    from qgis_sdk.tasks import task

    @task("My decorated task", bind=True, can_cancel=True)
    def my_task(self, value=10):
        self.set_progress(50)
        return value * 2

    # Direct call — synchronous, like Celery direct call
    result = my_task(21)
    assert result == 42

    # delay — async, returns AsyncResult
    async_result = my_task.delay(21)
    assert async_result.get() == 42
    assert async_result.ready()
    assert async_result.successful()
    assert not async_result.failed()
    assert async_result.state == "SUCCESS"
    assert async_result.result == 42
    assert async_result.id is not None

    # apply_async — more control, like Celery
    async_result2 = my_task.apply_async(args=(10,), kwargs={}, description="Custom task")
    assert async_result2.get() == 20
    assert async_result2.state == "SUCCESS"

    # apply_async with countdown
    async_result3 = my_task.apply_async(args=(5,), countdown=0.01)
    assert async_result3.get() == 10

    # s() — signature, like Celery
    sig = my_task.s(10)
    async_result4 = sig.delay()
    assert async_result4.get() == 20

    # si() — immutable signature
    sig2 = my_task.si(15)
    async_result5 = sig2.delay()
    assert async_result5.get() == 30
    # si ignores new args
    async_result6 = sig2.delay(999)
    assert async_result6.get() == 30


def test_task_decorator_without_bind(fake_task_manager):
    """Test @task without bind — function doesn't receive task arg."""
    from qgis_sdk.tasks import task

    @task("Simple task")
    def add(x, y):
        return x + y

    # Direct call
    assert add(4, 4) == 8

    # delay
    async_result = add.delay(4, 4)
    assert async_result.get() == 8
    assert async_result.ready()
    assert async_result.successful()


def test_task_decorator_variants():
    """Test @task used with and without parentheses."""
    from qgis_sdk.tasks import task

    @task
    def my_task1(x, y):
        return x + y

    assert my_task1(2, 3) == 5
    assert my_task1.delay(2, 3).get() == 5

    @task("Custom description", bind=True)
    def my_task2(self, x):
        self.set_progress(100)
        return x * 2

    assert my_task2(5) == 10
    assert my_task2.delay(5).get() == 10


def test_async_result_api(fake_async_result, fake_task):
    """Test AsyncResult API — celery-like."""
    # Uses fixtures fake_async_result and fake_task
    assert fake_async_result.ready()
    assert fake_async_result.successful()
    assert not fake_async_result.failed()
    assert fake_async_result.state == "SUCCESS"
    assert fake_async_result.get() == 42
    assert fake_async_result.result == 42
    assert fake_async_result.id is not None

    # wait() alias
    assert fake_async_result.wait() == 42

    # revoke
    fake_task.cancel()
    assert fake_task.is_canceled()


def test_task_wrapper_fixture(fake_task_wrapper):
    """Test TaskWrapper fixture — celery-like."""
    assert fake_task_wrapper(4, 4) == 8
    async_result = fake_task_wrapper.delay(4, 4)
    assert async_result.get() == 8
    assert async_result.state == "SUCCESS"

    sig = fake_task_wrapper.s(10, 20)
    assert sig.delay().get() == 30

    sig2 = fake_task_wrapper.si(5, 5)
    assert sig2.delay().get() == 10
    # Immutable ignores new args
    assert sig2.delay(100, 100).get() == 10


def test_chain_and_group(fake_task_manager):
    """Test chain and group — celery-like."""
    from qgis_sdk.tasks import task, chain, group

    @task
    def add(x, y=0):
        return x + y

    @task
    def mul(x, y=1):
        return x * y

    # Chain: add(2,2)=4, then add(3) => 4+3=7 (previous result passed as first arg)
    c = chain(add.s(2, 2), add.s(3))
    result = c()
    assert result == 7

    # Chain with mul: add(2,3)=5, mul(2) => 5*2=10
    c2 = chain(add.s(2, 3), mul.s(2))
    assert c2() == 10

    # Group
    results = group(add.s(1, 1), add.s(2, 2), add.s(3, 3))
    assert len(results) == 3
    assert results[0].get() == 2
    assert results[1].get() == 4
    assert results[2].get() == 6


def test_run_task_convenience():
    from qgis_sdk.tasks import run_task

    results = []

    def do_work(task):
        return 123

    def on_finished(exc, result):
        results.append(result)

    async_result = run_task(do_work, description="Convenience task", on_finished=on_finished, bind=True)
    # run_task returns AsyncResult now
    assert async_result.get() == 123
    time.sleep(0.1)
    assert len(results) >= 1
    assert results[0] == 123


# ── FakeTask and FakeTaskManager (using fixtures) ───────────────────────────

def test_fake_task(fake_task):
    """Uses fake_task fixture."""
    # fake_task fixture returns FakeTask with default
    assert fake_task.description == "Task"
    assert not fake_task.is_finished()

    # Custom task via fixture factory
    from qgis_sdk.testing import FakeTask

    def work(task, value):
        task.set_progress(50)
        return value * 2

    t = FakeTask("Test task", work, value=10, on_finished=lambda e, r: None, bind=True)
    assert t.description == "Test task"
    assert not t.is_finished()
    result = t._execute()
    assert result == 20
    assert t.is_finished()
    assert t.progress() == 50
    assert t.state == "SUCCESS"

    # Test delay — celery-like (use kwarg to avoid duplicate)
    async_res = t.delay(value=20)
    assert async_res.get() == 40
    assert async_res.state == "SUCCESS"


def test_fake_task_manager(fake_task_manager):
    """Uses fake_task_manager fixture — celery-like."""
    results = []

    def work(task):
        return 42

    def on_finished(exc, result):
        results.append(result)

    from qgis_sdk.testing import FakeTask

    t = FakeTask("My task", work, on_finished=on_finished, bind=True)
    async_result = fake_task_manager.add_task(t)

    assert len(results) == 1
    assert results[0] == 42
    assert len(fake_task_manager.added_tasks) == 1
    assert fake_task_manager.count() == 0
    assert async_result.get() == 42
    assert async_result.state == "SUCCESS"

    # Test callable — returns AsyncResult
    results2 = []

    def work2():
        results2.append(99)
        return 99

    async_res2 = fake_task_manager.add_task(work2, description="Callable task")
    assert len(results2) == 1
    assert async_res2.get() == 99


def test_fake_task_manager_with_wrapper(fake_task_manager, fake_task_wrapper):
    """Test FakeTaskManager with TaskWrapper — celery-like."""
    async_result = fake_task_manager.add_task(fake_task_wrapper, 10, 20)
    assert async_result.get() == 30
    assert len(fake_task_manager.added_tasks) >= 1


def test_fake_task_cancel(fake_task):
    from qgis_sdk.testing import FakeTask

    t = FakeTask("Cancelable task", lambda task: 42, can_cancel=True, bind=True)
    assert t.can_cancel()
    assert not t.is_canceled()
    t.cancel()
    assert t.is_canceled()
    assert t._state == "REVOKED"


# ── Integration with Plugin (using fixtures) ─────────────────────────────────

def test_task_with_fake_iface(fake_iface, fake_action_factory, fake_task_manager):
    """Plugin uses task manager with fake iface — uses fixtures."""
    from qgis_sdk import Plugin, action, toolbar
    from qgis_sdk.testing import FakeTask

    class MyPlugin(Plugin):
        name = "test_task_plugin"
        version = "0.1.0"

        @toolbar("Test")
        @action(tooltip="Run task")
        def run_task_action(self, iface):
            def work(task):
                task.set_progress(100)
                return {"status": "done"}

            def on_finished(exc, result):
                iface.messageBar().pushMessage(f"Task {result['status']}")

            t = FakeTask("My task", work, on_finished=on_finished, bind=True)
            fake_task_manager.add_task(t)

    MyPlugin.action_factory = staticmethod(fake_action_factory)
    plugin = MyPlugin(fake_iface)
    plugin.init_gui()
    fake_iface.toolbar_icons[0].trigger()
    assert "Task done" in fake_iface.messages[0]


def test_task_celery_like_with_fake_iface(fake_iface, fake_action_factory, fake_task_manager):
    """Plugin using celery-like API with fixtures."""
    from qgis_sdk import Plugin, action, toolbar
    from qgis_sdk.tasks import task

    @task(bind=True)
    def my_background_task(self, value=10):
        self.set_progress(50)
        return {"status": "done", "value": value}

    class MyPlugin(Plugin):
        name = "test_celery_plugin"
        version = "0.1.0"

        @toolbar("Test")
        @action(tooltip="Run celery task")
        def run_celery_task(self, iface):
            # Using celery-like delay
            async_result = my_background_task.delay(42)

            def on_done():
                # In real QGIS, you'd connect to finished signal
                # For test, get result synchronously
                result = async_result.get()
                iface.messageBar().pushMessage(f"Task {result['status']} {result['value']}")

            on_done()

    MyPlugin.action_factory = staticmethod(fake_action_factory)
    plugin = MyPlugin(fake_iface)
    plugin.init_gui()
    fake_iface.toolbar_icons[0].trigger()
    assert "Task done 42" in fake_iface.messages[0]


def test_processing_alg_runner_task():
    from qgis_sdk.tasks import ProcessingAlgRunnerTask

    class FakeContext:
        pass

    class FakeFeedback:
        pass

    task = ProcessingAlgRunnerTask("qgis:randompointsinextent", {"POINTS_NUMBER": 10}, FakeContext(), FakeFeedback())
    assert task is not None
    assert hasattr(task, "qgis_task")
    assert hasattr(task, "fallback_task")
    assert hasattr(task, "delay")
    assert hasattr(task, "apply_async")
