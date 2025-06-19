"""Wrapper around Windows *schtasks.exe* commands.

Only minimal functionality is implemented at this stage to unblock
imports and unit-test stubs.  Detailed error handling and extended
parameters will be fleshed out in subsequent sub-phases of *Phase 2*.
"""

from __future__ import annotations

import json
import os
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
        # If env var set, run in simulation mode (skip actual schtasks calls)
        self.simulate = bool(os.environ.get("ORC_SIMULATE_SCHEDULER", ""))
        if self.simulate:
            self.logger.info("WindowsScheduler running in simulation mode – no real tasks will be created.")

    # ------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------
    def create_task(
        self,
        task_name: str,
        command: str,  # This will be ignored - we use orc.py
        schedule_trigger: Dict[str, str],
        description: Optional[str] = None,
    ) -> bool:
        """Create Windows scheduled task that calls orc.py --task task_name"""
        
        full_name = self.TASK_PREFIX + task_name
        
        # Determine project root directory
        import inspect
        import os
        current_file = inspect.getfile(inspect.currentframe())
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

        # Ensure executable path (python) is quoted if contains spaces
        python_exe = os.path.join(project_root, ".venv", "Scripts", "python.exe") if (
            os.path.exists(os.path.join(project_root, ".venv", "Scripts", "python.exe"))
        ) else "python"

        # Build command invoking orc.py from the project root via cmd so that the
        # task runs in the correct working directory without relying on an
        # unsupported schtasks parameter.
        orc_command_inner = f'"{python_exe}" "{os.path.join(project_root, "orc.py")}" --task {task_name}'
        orc_command = f'cmd /c "cd /d {project_root} && {orc_command_inner}"'

        cmd = CREATE_CMD_BASE + [
            "/TN",
            str(Path(self.TASK_PATH) / full_name),
            "/TR",
            orc_command,
        ]

        # Optionally elevate privileges if explicitly requested via env var
        if os.environ.get("ORC_SCHEDULER_RUNAS_SYSTEM") and not self.simulate:
            cmd += ["/RL", "HIGHEST", "/RU", "SYSTEM"]

        # Append schedule parameters from CronConverter result
        for flag, value in schedule_trigger.items():
            if value is True or value == "":
                cmd.append(f"/{flag.upper()}")
            else:
                cmd += [f"/{flag.upper()}", str(value)]

        # (Optional) log description locally but not pass invalid flag
        if description:
            self.logger.info("Task description: %s", description)
        

        
        self.logger.info(f"Creating Windows task with command: {orc_command}")
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

        return [
            task
            for task in tasks
            if task.get("TaskName", "").lstrip("\\").startswith(self.TASK_PATH.lstrip("\\") + self.TASK_PREFIX)
        ]

    # ------------------------------------------------------------
    # Extra helpers – useful for Phase-2 success criteria
    # ------------------------------------------------------------
    def enable_task(self, task_name: str) -> bool:
        """Enable an existing scheduled task (no-op if already enabled)."""

        full_name = self.TASK_PREFIX + task_name
        cmd = [
            "schtasks",
            "/Change",
            "/TN",
            str(Path(self.TASK_PATH) / full_name),
            "/ENABLE",
        ]
        return self._run(cmd)

    def disable_task(self, task_name: str) -> bool:
        """Disable an existing scheduled task (no-op if already disabled)."""

        full_name = self.TASK_PREFIX + task_name
        cmd = [
            "schtasks",
            "/Change",
            "/TN",
            str(Path(self.TASK_PATH) / full_name),
            "/DISABLE",
        ]
        return self._run(cmd)

    def get_task_status(self, task_name: str) -> Dict[str, str] | None:
        """Return raw task info from *schtasks* as a dict or **None** if absent."""

        full_name = self.TASK_PREFIX + task_name
        success, stdout = self._run(
            QUERY_CMD_BASE + ["/TN", str(Path(self.TASK_PATH) / full_name)],
            capture_output=True,
        )
        if not success or not stdout:
            return None
        try:
            task_list = json.loads(stdout)
            return task_list[0] if task_list else None
        except json.JSONDecodeError:
            self.logger.warning("Could not parse schtasks JSON output for single task")
            return None

    # ------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------
    def _run(self, cmd: List[str], capture_output: bool = False):  # type: ignore[override]
        """Execute *schtasks.exe* returning success flag and optional stdout."""

        # Short-circuit when in simulation mode
        if getattr(self, "simulate", False):
            self.logger.debug("Simulated schtasks run: %s", " ".join(cmd))
            return (True, "") if capture_output else True

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
