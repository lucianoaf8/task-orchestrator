"""Wrapper around Windows *schtasks.exe* commands - FINAL WORKING VERSION

This version:
1. Removes invalid /SD flag
2. Uses cmd /c with cd to set working directory
3. Properly queries and filters tasks
4. Has detailed error logging
"""

from __future__ import annotations

import json
import os
import subprocess
import logging
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

__all__ = ["WindowsScheduler"]

CREATE_CMD_BASE = ["schtasks", "/Create"]
DELETE_CMD_BASE = ["schtasks", "/Delete", "/F"]
QUERY_CMD_BASE = ["schtasks", "/Query", "/FO", "LIST"]


class WindowsScheduler:
    """Working wrapper around schtasks.exe"""

    TASK_PATH = r"\Orchestrator"
    TASK_PREFIX = "Orc_"

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.simulate = bool(os.environ.get("ORC_SIMULATE_SCHEDULER", ""))
        if self.simulate:
            self.logger.info("WindowsScheduler running in simulation mode")

    def create_task(
        self,
        task_name: str,
        command: str,  # Ignored - we use orc.py
        schedule_trigger: Dict[str, str],
        description: Optional[str] = None,
    ) -> bool:
        """Create Windows scheduled task that calls orc.py --task task_name"""
        
        full_task_name = f"{self.TASK_PATH}\\{self.TASK_PREFIX}{task_name}"
        
        # Get project root
        import inspect
        current_file = inspect.getfile(inspect.currentframe())
        project_root = Path(current_file).parent.parent.parent.resolve()
        
        # Find Python executable
        venv_python = project_root / ".venv" / "Scripts" / "python.exe"
        python_exe = str(venv_python) if venv_python.exists() else sys.executable
        
        # Build command string for /TR – avoid extra escaping quotes
        orc_py = project_root / "orc.py"
        # Paths do not contain spaces, so quoting only the script path keeps things simple
        orc_command = f\
        
        # Build schtasks command
        cmd = CREATE_CMD_BASE + [
            "/TN", full_task_name,
            "/TR", orc_command,
            
            "/F"  # Force create (overwrite if exists)
        ]
        
        # Add schedule parameters from CronConverter
        for flag, value in schedule_trigger.items():
            if value is True or value == "":
                cmd.append(f"/{flag.upper()}")
            else:
                cmd += [f"/{flag.upper()}", str(value)]
        
        self.logger.info(f"Creating task: {full_task_name}")
        self.logger.debug(f"Task command: {orc_command}")
        self.logger.debug(f"Full schtasks command: {' '.join(cmd)}")
        
        success = self._run(cmd)
        
        if success:
            self.logger.info(f"Successfully created task: {full_task_name}")
            # Verify it was actually created
            if self.task_exists(task_name):
                self.logger.info(f"Verified task exists: {full_task_name}")
            else:
                self.logger.error(f"Task creation reported success but task not found: {full_task_name}")
                success = False
        else:
            self.logger.error(f"Failed to create task: {full_task_name}")
            
        return success

    def change_task(
        self,
        task_name: str,
        schedule_trigger: Optional[Dict[str, str]] = None,
        new_command: Optional[str] = None,
    ) -> bool:
        """Modify an existing Windows task in-place using *schtasks /Change*.

        We purposely avoid deleting the task so that Windows keeps historical
        run data. For now we support minute-based schedules (*/N) via `/RI N`
        and bump the start time (`/ST`) forward by *N* minutes to make the
        update visible immediately.  `new_command` – if provided – updates the
        `/TR` string.
        """
        full_task_name = f"{self.TASK_PATH}\\{self.TASK_PREFIX}{task_name}"
        overall_success = True

        # -----------------------------
        # Trigger change (interval)
        # -----------------------------
        if schedule_trigger:
            if schedule_trigger.get("SC") == "MINUTE":
                interval = schedule_trigger.get("MO", "1")
                # Make next start obvious: now + interval minutes
                start_time = (datetime.now() + timedelta(minutes=int(interval))).strftime("%H:%M")
                cmd = [
                    "schtasks",
                    "/Change",
                    "/TN",
                    full_task_name,
                    "/RI",
                    str(interval),
                    "/ST",
                    start_time,
                ]
                self.logger.info(
                    "Updating trigger for task %s to every %s minutes; next run at %s",
                    task_name,
                    interval,
                    start_time,
                )
                overall_success = overall_success and self._run(cmd)
            else:
                self.logger.error("change_task currently supports only minute-based schedules")
                overall_success = False

        # -----------------------------
        # Action / command change
        # -----------------------------
        if new_command:
            cmd = [
                "schtasks",
                "/Change",
                "/TN",
                full_task_name,
                "/TR",
                new_command,
            ]
            self.logger.info("Updating command for task %s", task_name)
            overall_success = overall_success and self._run(cmd)

        return overall_success

    def delete_task(self, task_name: str) -> bool:
        """Delete the task if it exists"""
        full_task_name = f"{self.TASK_PATH}\\{self.TASK_PREFIX}{task_name}"
        cmd = DELETE_CMD_BASE + ["/TN", full_task_name]
        
        self.logger.info(f"Deleting task: {full_task_name}")
        return self._run(cmd)

    def task_exists(self, task_name: str) -> bool:
        """Check if specific task exists"""
        full_task_name = f"{self.TASK_PATH}\\{self.TASK_PREFIX}{task_name}"
        cmd = QUERY_CMD_BASE + ["/TN", full_task_name]
        
        success, _ = self._run(cmd, capture_output=True)
        return success

    def list_orchestrator_tasks(self) -> List[dict]:
        """List all orchestrator tasks.

        We invoke *schtasks* once without any /TN filter and then
        post-filter the results in Python.  This avoids mismatched
        wildcard semantics across Windows versions that caused
        confusing ``"The system cannot find the file specified."``
        errors in the logs.
        """
        # Single query for *all* tasks – QUERY_CMD_BASE already includes "/FO LIST"
        success, stdout = self._run(QUERY_CMD_BASE, capture_output=True)
        if not success or not stdout:
            self.logger.debug("schtasks /Query failed – returning empty list")
            return []
        
        # schtasks LIST output is plain text – parse it into a list of task dicts.
        tasks: List[dict] = []
        current: dict[str, str] = {}
        for raw_line in stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("HostName:") and current:
                # Separator between task blocks – store previous and reset
                tasks.append(current)
                current = {}
            if ":" in line:
                key, val = line.split(":", 1)
                current[key.strip()] = val.strip()
        if current:
            tasks.append(current)
        
        task_prefix = f"{self.TASK_PATH}\\{self.TASK_PREFIX}"
        orchestrator_tasks = [
            {**t, "ShortName": t.get("TaskName", "")[len(task_prefix):]}
            for t in tasks
            if t.get("TaskName", "").startswith(task_prefix)
        ]
        self.logger.debug("Found %d orchestrator tasks", len(orchestrator_tasks))
        return orchestrator_tasks
            


    def get_task_info(self, task_name: str) -> Optional[Dict[str, str]]:
        """Return detailed information for a *single* orchestrator task.

        This helper is useful for diagnostics / monitoring without having to
        manually parse *schtasks* output everywhere in the codebase.
        """
        full_task_name = f"{self.TASK_PATH}\\{self.TASK_PREFIX}{task_name}"
        cmd = QUERY_CMD_BASE + ["/V", "/TN", full_task_name]
        success, stdout = self._run(cmd, capture_output=True)
        if not success or not stdout:
            return None

        info: Dict[str, str] = {}
        for line in stdout.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                info[key.strip()] = val.strip()
        return info or None

    def _run(self, cmd: List[str], capture_output: bool = False):
        """Execute schtasks.exe with proper error handling"""
        if self.simulate:
            self.logger.debug(f"[SIMULATE] Would run: {' '.join(cmd)}")
            if capture_output:
                if "/Query" in cmd and "/TN" not in cmd:
                    # Simulate listing all tasks
                    fake_tasks = json.dumps([{
                        "TaskName": f"{self.TASK_PATH}\\{self.TASK_PREFIX}simulated_task",
                        "Status": "Ready",
                        "Next Run Time": "1/1/2025 12:00:00 AM"
                    }])
                    return True, fake_tasks
                return True, "[]"
            return True
        
        try:
            # Log the command we're about to run
            self.logger.debug(f"Executing: {' '.join(cmd)}")
            
            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,  # Always capture to log errors
                text=True,
                check=False,
                shell=False,  # Don't use shell for security
                encoding="utf-8",
                errors="replace"
            )
            
            # Log output for debugging
            if result.returncode != 0:
                self.logger.error(f"Command failed with exit code {result.returncode}")
                if result.stderr:
                    self.logger.error(f"Error output: {result.stderr}")
                if result.stdout:
                    self.logger.debug(f"Standard output: {result.stdout}")
            
            # Return results
            if result.returncode == 0:
                if capture_output:
                    return True, result.stdout
                return True
            else:
                if capture_output:
                    return False, result.stderr or result.stdout
                return False
                
        except FileNotFoundError:
            self.logger.error("schtasks.exe not found - are you running on Windows?")
        except subprocess.TimeoutExpired:
            self.logger.error("schtasks.exe command timed out")
        except Exception as e:
            self.logger.exception(f"Unexpected error running schtasks: {e}")
        
        return (False, "") if capture_output else False
