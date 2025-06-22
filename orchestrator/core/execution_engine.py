"""Cross-platform task execution engine (Phase B3).

Responsibilities:
• Validate task configuration and dependencies.
• Execute shell command with timeout, capture output / errors.
• Retry with exponential back-off respecting *retry_count* / *retry_delay*.
• Return :class:`orchestrator.core.task_result.TaskResult`.

NOTE: For Windows only right now – uses ``subprocess`` with ``shell=True``
      because existing tasks store raw command strings. Future phases may
      introduce a safer argument list model.
"""
from __future__ import annotations

import json
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests  # type: ignore  # third-party stubs unavailable

from orchestrator.core.task_result import TaskResult
from orchestrator.core.exceptions import ValidationError
from orchestrator.core.config_manager import ConfigManager

__all__ = ["ExecutionEngine"]

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _now() -> datetime:  # tiny indirection eases testing
    return datetime.now()


def _parse_dependencies(dep_json: str | List[str] | None) -> List[str]:
    if not dep_json:
        return []
    if isinstance(dep_json, list):
        return dep_json
    try:
        return json.loads(dep_json)
    except Exception:  # pragma: no cover – fallback
        return []


class ExecutionEngine:  # noqa: R0902 – many attributes but clear use
    """Concrete implementation replacing legacy *TaskManager*."""

    def __init__(self, *, master_password: str | None = None) -> None:
        self._cfg = ConfigManager(master_password=master_password)
        self._log = logging.getLogger(self.__class__.__name__)

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    def execute_task(self, task_name: str) -> TaskResult:  # noqa: D401
        """Run *task_name* respecting retries / timeout.

        Steps:
        1. Validate and fetch config.
        2. Dependency check → skip if failed.
        3. Attempt command up to *retry_count + 1* times.
        4. Persist *TaskResult* via :pyclass:`ConfigManager`.
        """
        task_cfg = self._cfg.get_task(task_name)
        if not task_cfg:
            raise ValidationError("Task not found", error_code="TASK_NOT_FOUND", context={"task": task_name})

        # Basic validation
        command: str = task_cfg.get("command", "")
        if not command:
            raise ValidationError("No command configured", error_code="TASK_NO_COMMAND", context={"task": task_name})

        # Dependency check ------------------------------------------------
        ok, dep_msg = self._check_dependencies(task_cfg)
        if not ok:
            result = TaskResult(task_name, "SKIPPED", error=f"Dependency check failed: {dep_msg}")
            self._persist_result(result)
            return result

        # Retry / execution ---------------------------------------------
        retry_count: int = int(task_cfg.get("retry_count", 0) or 0)
        retry_delay: int = int(task_cfg.get("retry_delay", 300) or 300)
        timeout: int = int(task_cfg.get("timeout", 3600) or 3600)

        attempt = 0
        while True:
            attempt += 1
            result = self._execute_once(task_name, command, timeout, attempt - 1)
            if result.status == "SUCCESS" or attempt > retry_count:
                self._persist_result(result)
                return result

            # Failed & we still have retries left
            self._log.warning(
                "Task %s failed attempt %s/%s – retrying in %ss", task_name, attempt, retry_count, retry_delay
            )
            time.sleep(retry_delay)
            retry_delay *= 2  # simple exponential back-off

    # ------------------------------------------------------------------
    # Internals ---------------------------------------------------------
    # ------------------------------------------------------------------
    def _execute_once(self, task_name: str, command: str, timeout: int, retries_so_far: int) -> TaskResult:
        start_ts = _now()
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            end_ts = _now()
            status = "SUCCESS" if completed.returncode == 0 else "FAILED"
            return TaskResult(
                task_name=task_name,
                status=status,
                start_time=start_ts,
                end_time=end_ts,
                exit_code=completed.returncode,
                output=completed.stdout,
                error=completed.stderr,
                retry_count=retries_so_far,
            )
        except subprocess.TimeoutExpired as exc:
            end_ts = _now()
            self._log.error("Task %s timed out after %ss", task_name, timeout)
            return TaskResult(
                task_name=task_name,
                status="FAILED",
                start_time=start_ts,
                end_time=end_ts,
                exit_code=None,
                output=(exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")),
                error=f"Timeout after {timeout}s",
                retry_count=retries_so_far,
            )
        except Exception as exc:  # pragma: no cover – safeguard
            end_ts = _now()
            self._log.exception("Unhandled error executing task %s", task_name)
            return TaskResult(
                task_name=task_name,
                status="FAILED",
                start_time=start_ts,
                end_time=end_ts,
                error=str(exc),
                retry_count=retries_so_far,
            )

    # Dependency checking ------------------------------------------------
    def _check_dependencies(self, task_cfg: Dict[str, Any]) -> Tuple[bool, str]:
        deps = _parse_dependencies(task_cfg.get("dependencies"))
        if not deps:
            return True, "OK"

        for dep in deps:
            dep = dep.strip()
            if dep.startswith("task:"):
                other_task = dep.split("task:", 1)[1]
                if not self._task_success_last_run(other_task):
                    return False, f"Dependency task '{other_task}' last run failed or never ran"
            elif dep.startswith("file:"):
                path = dep.split("file:", 1)[1]
                if not Path(path).exists():
                    return False, f"File '{path}' missing"
            elif dep.startswith("url:"):
                url = dep.split("url:", 1)[1]
                try:
                    resp = requests.head(url, timeout=10)
                    if resp.status_code >= 400:
                        return False, f"URL '{url}' returned {resp.status_code}"
                except Exception as exc:
                    return False, f"URL '{url}' unreachable: {exc}"
            elif dep.startswith("cmd:"):
                cmd = dep.split("cmd:", 1)[1]
                proc = subprocess.run(cmd, shell=True)
                if proc.returncode != 0:
                    return False, f"Command '{cmd}' failed with exit {proc.returncode}"
            else:
                self._log.warning("Unknown dependency format: %s", dep)
        return True, "OK"

    def _task_success_last_run(self, task_name: str) -> bool:
        """Return True if *task_name* last execution succeeded."""
        cursor = self._cfg.db.execute(
            "SELECT status FROM task_results WHERE task_name=? ORDER BY id DESC LIMIT 1", (task_name,)
        )
        row = cursor.fetchone()
        return bool(row and row[0] == "SUCCESS")

    # DB persistence ----------------------------------------------------
    def _persist_result(self, result: TaskResult) -> None:
        try:
            self._cfg.save_task_result(result)
        except Exception as exc:  # pragma: no cover – log but do not raise
            self._log.error("Failed to persist task result: %s", exc)
