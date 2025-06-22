"""High-level scheduling service – wraps WindowsScheduler with consistent API."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from orchestrator.utils.windows_scheduler import WindowsScheduler
from orchestrator.core.exceptions import SchedulingError
from orchestrator.utils.cron_converter import CronConverter

__all__ = ["SchedulingService"]


class SchedulingService:  # noqa: R0903 – thin wrapper
    """Provides scheduling operations decoupled from UI / ConfigManager."""

    def __init__(self, scheduler: Optional[WindowsScheduler] = None) -> None:
        self._scheduler = scheduler or WindowsScheduler()
        self._log = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # CRUD wrappers -----------------------------------------------------
    # ------------------------------------------------------------------
    def schedule_task(self, task_name: str, command: str, cron: str) -> bool:
        params = CronConverter.cron_to_schtasks_params(cron)
        ok = self._scheduler.create_task(task_name, command, params, f"Orchestrator – {task_name}")
        if not ok:
            raise SchedulingError(f"Failed to schedule task {task_name}")
        return ok

    def unschedule_task(self, task_name: str) -> bool:
        if not self._scheduler.delete_task(task_name):
            raise SchedulingError(f"Failed to unschedule task {task_name}")
        return True

    def change_task(self, task_name: str, cron: Optional[str] = None, command: Optional[str] = None) -> bool:
        if cron:
            params = CronConverter.cron_to_schtasks_params(cron)
            self.unschedule_task(task_name)
            return self.schedule_task(task_name, command or "", cron)
        return self._scheduler.change_task(task_name, schedule_trigger=None, new_command=command)

    def task_exists(self, task_name: str) -> bool:
        return self._scheduler.task_exists(task_name)

    def list_tasks(self) -> List[Dict[str, str]]:
        return self._scheduler.list_orchestrator_tasks()
