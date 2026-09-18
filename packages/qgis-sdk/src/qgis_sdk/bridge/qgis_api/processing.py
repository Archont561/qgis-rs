"""qgis_sdk.bridge.qgis_api.processing — processing API for JS."""

from __future__ import annotations

from typing import Any, Dict


class ProcessingAPI:
    def __init__(self, iface=None):
        self.iface = iface

    def run(self, alg_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run processing alg — returns task_id if background, or result dict."""
        try:
            # Try to run via QgsProcessingAlgRunnerTask
            from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsApplication
            from qgis_sdk.tasks import ProcessingAlgRunnerTask, TaskManager

            context = QgsProcessingContext()
            feedback = QgsProcessingFeedback()

            # If iface has mapCanvas etc, set project
            try:
                from qgis.core import QgsProject
                context.setProject(QgsProject.instance())
            except Exception:
                pass

            task = ProcessingAlgRunnerTask(alg_id, params, context, feedback)
            # For simplicity, run via task manager and return queued
            # In real QGIS, executed signal will have results
            TaskManager.instance().add_task(task)

            # Try to get task id
            qtask = task.qgis_task or task.fallback_task
            tid = getattr(qtask, 'id', str(id(qtask)))
            if callable(tid):
                try:
                    tid = tid()
                except Exception:
                    tid = str(id(qtask))

            return {"task_id": str(tid), "status": "queued", "alg_id": alg_id}
        except Exception as e:
            # Fallback: try direct processing
            try:
                import processing
                result = processing.run(alg_id, params)
                return {"status": "success", "result": result, "alg_id": alg_id}
            except Exception as e2:
                return {"status": "error", "error": str(e2), "alg_id": alg_id, "details": str(e)}
