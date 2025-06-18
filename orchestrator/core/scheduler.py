"""Unified TaskScheduler implementation (Phase 2).

This class is responsible for translating high-level orchestration
requests (schedule / unschedule / execute) into concrete operations
via the :class:`orchestrator.utils.windows_scheduler.WindowsScheduler`.

Only a *minimal* stub is provided for now so that imports resolve and
unit tests can be written while Windows-specific behaviour is added
incrementally in later sub-phases.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.task_result import TaskResult
from orchestrator.utils.cron_converter import CronConverter
from orchestrator.utils.windows_scheduler import WindowsScheduler

__all__ = ["TaskScheduler"]


class TaskScheduler:  # noqa: R0903 – intentionally minimal scaffold
    """Unified task scheduler & executor wrapper."""

    def __init__(self, master_password: Optional[str] = None):
        self.config_manager = ConfigManager(master_password=master_password)
        self.windows_scheduler = WindowsScheduler()
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Scheduling operations (invoked by CLI / API)
    # ------------------------------------------------------------------
    def schedule_task(self, task_name: str) -> bool:  # noqa: D401
        """Schedule *one* task – returns True on success."""
        task = self.config_manager.get_task(task_name)
        if not task:
            self.logger.error("Task %s not found", task_name)
            return False

        if not task.get("schedule"):
            self.logger.warning("Task %s has no schedule; skipping", task_name)
            return False

        params = CronConverter.cron_to_schtasks_params(task["schedule"])
        cmd = task["command"]
        description = f"Orchestrator – {task_name}"
        return self.windows_scheduler.create_task(task_name, cmd, params, description)

    def schedule_all_tasks(self) -> Dict[str, bool]:
        """Schedule every *enabled* task; map name → success bool."""
        results: Dict[str, bool] = {}
        for name in self.config_manager.get_all_tasks().keys():
            results[name] = self.schedule_task(name)
        return results

    def unschedule_task(self, task_name: str) -> bool:
        """Remove task from Windows Task Scheduler."""
        return self.windows_scheduler.delete_task(task_name)

    def list_scheduled_tasks(self) -> List[dict]:
        """Return information about scheduled orchestrator tasks."""
        return self.windows_scheduler.list_orchestrator_tasks()

    # ------------------------------------------------------------------
    # Execution path (called *by* Windows Task Scheduler)
    # ------------------------------------------------------------------
    def execute_task(self, task_name: str) -> TaskResult:  # noqa: D401
        """Execute a task immediately and return its :class:`TaskResult`."""
        # For now reuse legacy TaskManager execution path until Phase 3.
        from main import TaskManager  # type: ignore  # local import to sidestep circular deps

        manager = TaskManager()
        legacy_result = manager.run_task_with_retry(task_name)
        # Convert to new TaskResult dataclass if needed
        if isinstance(legacy_result, TaskResult):
            return legacy_result
        return TaskResult.from_dict(legacy_result.to_dict())

    # Placeholder helpers ------------------------------------------------
    def check_dependencies(self, task_name: str) -> tuple[bool, str]:
        """Stub – dependency checks handled in legacy TaskManager for now."""
        from main import TaskManager  # type: ignore

        return TaskManager().check_dependencies(task_name)

    def validate_task_config(self, task_name: str) -> tuple[bool, str]:
        """Very light validation of task config."""
        task = self.config_manager.get_task(task_name)
        if not task:
            return False, "Task not found"
        if not task.get("command"):
            return False, "Missing command"
        return True, "OK"
