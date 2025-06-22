"""Service encapsulating task CRUD + validation + scheduling integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.exceptions import ValidationError, OrchestratorError, SchedulingError
from .scheduling_service import SchedulingService

__all__ = ["TaskService"]


class TaskService:  # noqa: R0903 – slim façade over ConfigManager
    def __init__(
        self,
        *,
        config_manager: Optional[ConfigManager] = None,
        scheduling_service: Optional[SchedulingService] = None,
    ) -> None:
        self._cfg = config_manager or ConfigManager()
        self._sched = scheduling_service or SchedulingService()
        self._log = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate, persist and (optionally) schedule a new task."""
        name = task_data.get("name")
        if not name:
            raise ValidationError("Task name required", error_code="TASK_NAME_MISSING")
        if self._cfg.get_task(name):
            raise ValidationError(
                f"Task {name} already exists", error_code="TASK_ALREADY_EXISTS", context={"task": name}
            )

        # Persist + schedule atomically via ConfigManager helper
        try:
            self._cfg.add_task_with_scheduling(task_data)
        except SchedulingError:
            raise  # propagate as-is
        except Exception as exc:
            raise OrchestratorError("Failed creating task", context={"task": name}) from exc

        return {"success": True, "task": self._cfg.get_task(name)}

    def update_task(self, name: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        task = self._cfg.get_task(name)
        if not task:
            raise ValidationError("Task not found", error_code="TASK_NOT_FOUND", context={"task": name})

        task.update(updates)
        # Persist update
        self._cfg.add_task(**task)

        # Handle scheduling change
        if "schedule" in updates:
            if task["enabled"] and task["schedule"]:
                self._sched.change_task(name, cron=task["schedule"], command=task["command"])
            else:
                self._sched.unschedule_task(name)
        elif "enabled" in updates and not task["enabled"]:
            self._sched.unschedule_task(name)

        return {"success": True, "task": task}

    def get_task(self, name: str) -> Dict[str, Any] | None:  # noqa: D401
        return self._cfg.get_task(name)

    def list_tasks(self) -> Dict[str, Dict[str, Any]]:  # noqa: D401
        return self._cfg.get_all_tasks()

    def delete_task(self, name: str) -> bool:  # noqa: D401
        if not self._cfg.get_task(name):
            raise ValidationError("Task not found", error_code="TASK_NOT_FOUND", context={"task": name})
        # Disable & unschedule
        self._cfg.add_task(name=name, task_type="", command="", enabled=False)
        self._sched.unschedule_task(name)
        return True
