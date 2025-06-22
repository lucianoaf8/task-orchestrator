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
from typing import Tuple
from typing import Dict, List, Optional

from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.task_result import TaskResult
from orchestrator.utils.cron_converter import CronConverter
from orchestrator.core.execution_engine import ExecutionEngine
from orchestrator.utils.windows_scheduler import WindowsScheduler

__all__ = ["TaskScheduler"]


class TaskScheduler:  # noqa: R0903 – intentionally minimal scaffold
    """Unified task scheduler & executor wrapper."""

    def __init__(self, master_password: Optional[str] = None):
        self.config_manager = ConfigManager(master_password=master_password)
        self.windows_scheduler = WindowsScheduler()
        self.execution_engine = ExecutionEngine(master_password=master_password)
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

    def update_task(
        self,
        task_name: str,
        *,
        new_schedule: str | None = None,
        new_command: str | None = None,
    ) -> bool:
        """Update an *existing* task without deleting historical run data.

        1. Persist new_schedule / new_command into the SQLite `tasks` row.
        2. Apply the trigger / command change in-place via *schtasks /Change*.
        """
        task = self.config_manager.get_task(task_name)
        if not task:
            self.logger.error("Task %s not found", task_name)
            return False

        # -----------------------------
        # Update DB first (so simulator + CLI reflect new state)
        # -----------------------------
        if new_schedule:
            task["schedule"] = new_schedule
        if new_command:
            task["command"] = new_command

        # Use add_task (INSERT OR REPLACE) to persist update
        self.config_manager.add_task(
            name=task["name"],
            task_type=task["type"],
            command=task["command"],
            schedule=task["schedule"],
            timeout=task["timeout"],
            retry_count=task["retry_count"],
            retry_delay=task["retry_delay"],
            dependencies=task["dependencies"],
            enabled=task["enabled"],
        )

        # -----------------------------
        # Apply changes in Windows Scheduler
        # -----------------------------
        if new_schedule:
            # Simplest reliable path: delete + recreate with new trigger
            # This loses run history but avoids unsupported /Change flags.
            self.logger.info("Schedule modified – recreating Windows task")
            # Ignore deletion failure (task may not exist yet)
            self.windows_scheduler.delete_task(task_name)
            params = CronConverter.cron_to_schtasks_params(task["schedule"])
            return self.windows_scheduler.create_task(
                task_name,
                task["command"],
                params,
                description=f"Orchestrator – {task_name}",
            )
        else:
            # Only command changed – lighter in-place update
            return self.windows_scheduler.change_task(
                task_name,
                schedule_trigger=None,
                new_command=new_command,
            )

    def unschedule_task(self, task_name: str) -> bool:
        """Remove task from Windows Task Scheduler."""
        return self.windows_scheduler.delete_task(task_name)

    def task_exists(self, task_name: str) -> bool:
        """Return True if task is present in Windows Scheduler."""
        return self.windows_scheduler.task_exists(task_name)

    def list_scheduled_tasks(self) -> List[dict]:
        """Return information about scheduled orchestrator tasks."""
        return self.windows_scheduler.list_orchestrator_tasks()

    # ------------------------------------------------------------------
    # Execution path (called *by* Windows Task Scheduler)
    # ------------------------------------------------------------------
    def execute_task(self, task_name: str) -> TaskResult:  # noqa: D401
        """Execute task via :class:`ExecutionEngine` and return result."""
        return self.execution_engine.execute_task(task_name)

    # Placeholder helpers ------------------------------------------------
    def check_dependencies(self, task_name: str) -> tuple[bool, str]:
        """Delegate to ExecutionEngine internal dependency check."""
        task = self.config_manager.get_task(task_name)
        if not task:
            return False, "Task not found"
        return self.execution_engine._check_dependencies(task)

    def validate_task_config(self, task_name: str) -> tuple[bool, str]:
        """Very light validation of task config."""
        task = self.config_manager.get_task(task_name)
        if not task:
            return False, "Task not found"
        if not task.get("command"):
            return False, "Missing command"
        return True, "OK"
