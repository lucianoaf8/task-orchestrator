"""Wrapper around Windows *schtasks.exe* commands.

Only minimal functionality is implemented at this stage to unblock
imports and unit-test stubs.  Detailed error handling and extended
parameters will be fleshed out in subsequent sub-phases of *Phase 2*.
"""

from __future__ import annotations

import json
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional

__all__ = ["WindowsScheduler"]

CREATE_CMD_BASE = ["schtasks", "/Create"]
DELETE_CMD_BASE = ["schtasks", "/Delete", "/F"]
QUERY_CMD_BASE = ["schtasks", "/Query", "/FO", "JSON"]  # JSON output simplifies parsing


class WindowsScheduler:  # noqa: R0903 – thin wrapper
    """A *very light* wrapper around *schtasks.exe*.

    The API purposefully hides platform-specific details from higher-level
    orchestrator code.  For now, JSON parsing is used for `/Query` because it
    avoids brittle column parsing.  Windows 10 & later support this flag.
    """

    # Double final backslash to avoid unterminated raw-string issue
    TASK_PATH = r"\Orchestrator\\"  # folder in Task Scheduler
    TASK_PREFIX = "Orc_"

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------
    def create_task(
        self,
        task_name: str,
        command: str,
        schedule_trigger: Dict[str, str],
        description: Optional[str] = None,
    ) -> bool:
        """Create or replace a scheduled task.

        Parameters are *very* trimmed down for now: only basic triggers (daily,
        hourly, minute) supported via `schedule_trigger` mapping produced by
        :pyclass:`orchestrator.utils.cron_converter.CronConverter`.
        """

        full_name = self.TASK_PREFIX + task_name
        cmd = CREATE_CMD_BASE + [
            "/TN",
            str(Path(self.TASK_PATH) / full_name),
            "/TR",
            command,
            "/RL",
            "HIGHEST",
        ]

        if description:
            cmd += ["/RU", "SYSTEM", "/DE", description]
        else:
            cmd += ["/RU", "SYSTEM"]

        # Append schedule parameters (already validated)
        for flag, value in schedule_trigger.items():
            cmd += [f"/{flag.upper()}", str(value)] if value else [f"/{flag.upper()}"]

        return self._run(cmd)

    def delete_task(self, task_name: str) -> bool:
        """Delete the task if it exists (idempotent)."""

        full_name = self.TASK_PREFIX + task_name
        cmd = DELETE_CMD_BASE + ["/TN", str(Path(self.TASK_PATH) / full_name)]
        return self._run(cmd)

    def task_exists(self, task_name: str) -> bool:
        """Return True if task is present in Windows Task Scheduler."""

        full_name = self.TASK_PREFIX + task_name
        cmd = QUERY_CMD_BASE + ["/TN", str(Path(self.TASK_PATH) / full_name)]
        return self._run(cmd, capture_output=True)[0]

    def list_orchestrator_tasks(self) -> List[dict]:
        """List all tasks created by the orchestrator (Orc_*)."""

        success, stdout = self._run(QUERY_CMD_BASE + ["/TN", self.TASK_PATH], capture_output=True)
        if not success or not stdout:
            return []

        try:
            tasks = json.loads(stdout)
        except json.JSONDecodeError:
            self.logger.warning("Could not parse schtasks JSON output")
            return []

        return [task for task in tasks if task.get("TaskName", "").startswith(self.TASK_PATH + self.TASK_PREFIX)]

    # ------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------
    def _run(self, cmd: List[str], capture_output: bool = False):  # type: ignore[override]
        """Execute *schtasks.exe* returning success flag and optional stdout."""

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=False,
                encoding="utf-8",
            )
            if result.returncode == 0:
                if capture_output:
                    return True, result.stdout
                return True

            self.logger.error("schtasks.exe failed (%s): %s", result.returncode, " ".join(cmd))
        except FileNotFoundError:
            self.logger.error("schtasks.exe not found – Windows Scheduler features unavailable")
        except Exception as exc:  # pragma: no cover – unexpected
            self.logger.exception("Unexpected error running schtasks: %s", exc)

        return (False, "") if capture_output else False
