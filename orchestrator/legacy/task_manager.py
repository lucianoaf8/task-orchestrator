"""Very thin legacy *compatibility shim* for the old `TaskManager` class.

Only the **minimal surface** required by `TaskScheduler` and validation tests
is implemented:

* ``run_task_with_retry`` – executes a configured command once and wraps the
  result in :class:`orchestrator.core.task_result.TaskResult`.
* ``check_dependencies`` – always returns *(True, "OK")* (dependency checks
  were handled elsewhere in legacy code and are out-of-scope for Phase-2).

The intent is to unblock flow validation without re-introducing the full legacy
codebase.  When the new execution engine lands, this entire module can be
removed.
"""

from __future__ import annotations

import subprocess
import logging
from datetime import datetime
from typing import Tuple, Dict, Any

from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.task_result import TaskResult

__all__: list[str] = [
    "TaskManager",
]


class TaskManager:  # noqa: R0903 – intentionally minimal
    """Legacy compatibility wrapper implementing *only* required methods."""

    def __init__(self, master_password: str | None = None):
        self.cm = ConfigManager(master_password=master_password)
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API expected by TaskScheduler
    # ------------------------------------------------------------------
    def run_task_with_retry(self, task_name: str) -> TaskResult:  # noqa: D401
        """Execute *task_name* once and return a :class:`TaskResult`."""

        task_cfg = self.cm.get_task(task_name)
        if not task_cfg:
            self.logger.error("Task %s not found in database", task_name)
            return TaskResult(task_name, "FAILED", error="Task not found")

        cmd: str = task_cfg.get("command", "")
        if not cmd:
            self.logger.error("Task %s has no command configured", task_name)
            return TaskResult(task_name, "FAILED", error="No command configured")

        start_ts = datetime.now()
        try:
            completed = subprocess.run(
                cmd,
                shell=True,  # Legacy tasks stored plain shell commands
                capture_output=True,
                text=True,
                check=False,
            )
            end_ts = datetime.now()
            status = "SUCCESS" if completed.returncode == 0 else "FAILED"
            return TaskResult(
                task_name=task_name,
                status=status,
                start_time=start_ts,
                end_time=end_ts,
                exit_code=completed.returncode,
                output=completed.stdout,
                error=completed.stderr,
            )
        except Exception as exc:  # pragma: no cover – safeguard
            end_ts = datetime.now()
            self.logger.exception("Unhandled error executing task %s", task_name)
            return TaskResult(
                task_name=task_name,
                status="FAILED",
                start_time=start_ts,
                end_time=end_ts,
                error=str(exc),
            )

    # Stub – always succeeds ------------------------------------------------
    def check_dependencies(self, task_name: str) -> Tuple[bool, str]:  # noqa: D401
        """Return *(True, "OK")* – placeholder until proper implementation."""

        return True, "OK"
