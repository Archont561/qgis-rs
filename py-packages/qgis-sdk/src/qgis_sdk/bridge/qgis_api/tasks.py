"""qgis_sdk.bridge.qgis_api.tasks — tasks API for JS."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get_task_manager():
    try:
        from qgis.core import QgsApplication
        return QgsApplication.taskManager()
    except ImportError:
        return None


class TasksAPI:
    def __init__(self, plugin=None, iface=None):
        self.plugin = plugin
        self.iface = iface
        # For fallback without QGIS, we can use our own TaskManager
        self._fallback_tm = None

    def _get_registry_task(self, task_name: str):
        try:
            from qgis_sdk.plugin.registry import registry
            return registry.get_task(task_name)
        except Exception:
            return None

    def run(self, task_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Trigger a @task decorated job by name. Returns task_id."""
        params = params or {}
        wrapper = self._get_registry_task(task_name)
        if not wrapper:
            # Try plugin instance
            if self.plugin:
                try:
                    # Look for attribute on plugin class
                    # Could be method
                    maybe = getattr(self.plugin, task_name, None) or getattr(self.plugin.__class__, task_name, None)
                    if maybe:
                        # If it's TaskWrapper, use it
                        from qgis_sdk.tasks import TaskWrapper
                        if isinstance(maybe, TaskWrapper):
                            wrapper = maybe
                except Exception:
                    pass

        if not wrapper:
            raise ValueError(f"Task {task_name} not found")

        try:
            result = wrapper.delay(**params) if isinstance(params, dict) else wrapper.delay(*params)
            task_id = result.id
            return {"task_id": str(task_id), "status": result.state, "name": task_name}
        except Exception as e:
            raise RuntimeError(f"Failed to run task {task_name}: {e}") from e

    def list(self) -> List[Dict[str, Any]]:
        tm = _get_task_manager()
        if not tm:
            # Fallback
            try:
                from qgis_sdk.tasks import TaskManager
                tm = TaskManager.instance()
                tasks = tm.tasks()
                return [{"id": str(getattr(t, 'id', '')), "description": getattr(t, 'description', ''), "status": "running"} for t in tasks]
            except Exception:
                return []

        try:
            tasks = tm.tasks()
            result = []
            for t in tasks:
                try:
                    desc = t.description() if hasattr(t, "description") else str(t)
                    tid = t.id() if hasattr(t, "id") else str(id(t))
                    status = t.status() if hasattr(t, "status") else 0
                    result.append({"id": str(tid), "description": desc, "status": status})
                except Exception:
                    continue
            return result
        except Exception:
            return []

    def cancel(self, task_id: str) -> bool:
        tm = _get_task_manager()
        if not tm:
            try:
                from qgis_sdk.tasks import TaskManager
                tm_fallback = TaskManager.instance()
                for t in tm_fallback.tasks():
                    if str(getattr(t, 'id', '')) == str(task_id) or str(t.id) == str(task_id):
                        try:
                            t.cancel()
                            return True
                        except Exception:
                            pass
                return False
            except Exception:
                return False

        try:
            for t in tm.tasks():
                try:
                    tid = t.id() if hasattr(t, "id") else t.id()
                    if str(tid) == str(task_id):
                        t.cancel()
                        return True
                except Exception:
                    continue
            return False
        except Exception:
            return False
