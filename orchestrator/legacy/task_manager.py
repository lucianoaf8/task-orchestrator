from __future__ import annotations

"""Legacy continuous-loop TaskManager retained for backward compatibility.

This module was migrated from the original :pymod:`main` in order to complete
Phase 3 of the *Project-Transformation Plan* (remove continuous polling logic
from the project root while still offering an opt-in fallback daemon).
"""

import getpass
import json
import logging
import os
import smtplib
import subprocess
import sys
import threading
import time
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from croniter import croniter

from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.task_result import TaskResult

__all__ = [
    "TaskManager",
    "legacy_daemon",
]


class TaskManager:
    """Original polling implementation – **deprecated**.

    The class is preserved so that existing automation relying on the "polling"
    behaviour continues to work after the migration to Windows Task Scheduler.
    New code *must* switch to :class:`orchestrator.core.scheduler.TaskScheduler`.
    """

    def __init__(self, db_path: str | None = None, master_password: str | None = None):
        if db_path is None:
            # Default to original location (under `data/`)
            db_path = str(Path("data") / "orchestrator.db")
        self.config_manager = ConfigManager(db_path, master_password)
        self.running_tasks: dict[str, TaskResult] = {}
        self._setup_logging()
        self._ensure_condition_tasks()

    # ---------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------
    def _setup_logging(self) -> None:
        log_dir = self.config_manager.get_config("logging", "directory", "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_level = getattr(logging, self.config_manager.get_config("logging", "level", "INFO"))
        log_file = os.path.join(log_dir, f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log")
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _ensure_condition_tasks(self) -> None:
        """Register essential *condition* tasks if they are absent."""
        if self.config_manager.get_task("check_db_connection"):
            return
        script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "checks" / "check_db_connection.py"
        command = f"{sys.executable} {script_path}"
        self.config_manager.add_task(
            name="check_db_connection",
            task_type="condition",
            command=command,
            schedule=None,
            timeout=60,
            retry_count=0,
            retry_delay=0,
            dependencies=[],
            enabled=True,
        )

    # ------------------------------------------------------------------
    # Public helpers – execution path
    # ------------------------------------------------------------------
    def check_dependencies(self, task_name: str) -> tuple[bool, str]:  # noqa: D401
        task_config = self.config_manager.get_task(task_name)
        dependencies = task_config.get("dependencies", []) if task_config else []
        if not dependencies:
            return True, "No dependencies"
        failed_deps: list[str] = []
        for dep in dependencies:
            dep_config = self.config_manager.get_task(dep)
            if not dep_config:
                failed_deps.append(f"{dep} (not found)")
                continue
            if dep_config.get("type") == "condition":
                result = self.run_task(dep)
                if result.status != "SUCCESS":
                    failed_deps.append(dep)
            else:
                history = self.config_manager.get_task_history(dep, 1)
                if not history or history[0]["status"] != "SUCCESS":
                    failed_deps.append(dep)
        if failed_deps:
            return False, "Failed dependencies: " + ", ".join(failed_deps)
        return True, "All dependencies satisfied"

    def run_task(self, task_name: str) -> TaskResult:  # noqa: D401
        if task_name in self.running_tasks:
            self.logger.warning("Task %s is already running", task_name)
            return TaskResult(task_name, "SKIPPED", error="Task already running")
        task_config = self.config_manager.get_task(task_name)
        if not task_config:
            return TaskResult(task_name, "FAILED", error="Task not found")
        result = TaskResult(task_name, "RUNNING", start_time=datetime.now())
        self.running_tasks[task_name] = result
        self.logger.info("Starting task: %s", task_name)
        try:
            deps_ok, deps_msg = self.check_dependencies(task_name)
            if not deps_ok:
                result.status = "SKIPPED"
                result.error = deps_msg
                result.end_time = datetime.now()
                self.logger.warning("Task %s skipped: %s", task_name, deps_msg)
                return result
            command = task_config["command"]
            timeout = task_config.get("timeout", 3600)
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                result.exit_code = process.returncode
                result.output = stdout
                result.error = stderr
                if result.exit_code == 0:
                    result.status = "SUCCESS"
                    self.logger.info("Task %s completed successfully", task_name)
                else:
                    result.status = "FAILED"
                    self.logger.error("Task %s failed with exit code %s", task_name, result.exit_code)
            except subprocess.TimeoutExpired:
                process.kill()
                result.status = "FAILED"
                result.error = f"Task timed out after {timeout} seconds"
                self.logger.error("Task %s timed out", task_name)
        except Exception as exc:  # pragma: no cover – defensive
            result.status = "FAILED"
            result.error = str(exc)
            self.logger.exception("Task %s failed with exception", task_name)
        finally:
            result.end_time = datetime.now()
            self.running_tasks.pop(task_name, None)
            self.config_manager.save_task_result(result)
            self._send_notification(result)
        return result

    def run_task_with_retry(self, task_name: str) -> TaskResult:  # noqa: D401
        task_config = self.config_manager.get_task(task_name) or {}
        retry_count = task_config.get("retry_count", 0)
        retry_delay = task_config.get("retry_delay", 300)
        for attempt in range(retry_count + 1):
            result = self.run_task(task_name)
            result.retry_count = attempt
            if result.status == "SUCCESS" or attempt == retry_count:
                return result
            if result.status == "FAILED":
                self.logger.info(
                    "Retrying task %s in %s seconds (attempt %s/%s)",
                    task_name,
                    retry_delay,
                    attempt + 1,
                    retry_count + 1,
                )
                time.sleep(retry_delay)
        return result

    # ------------------------------------------------------------------
    # Notification helpers
    # ------------------------------------------------------------------
    def _send_notification(self, result: TaskResult) -> None:  # noqa: D401
        try:
            smtp_server = self.config_manager.get_config("email", "smtp_server", "smtp.office365.com")
            smtp_port = int(self.config_manager.get_config("email", "smtp_port", "587"))
            sender_email = self.config_manager.get_credential("email_username")
            password = self.config_manager.get_credential("email_password")
            recipients_json = self.config_manager.get_config("email", "recipients", "[]")
            recipients = json.loads(recipients_json) if recipients_json else []
            if not all([sender_email, password, recipients]):
                self.logger.warning("Email configuration incomplete, skipping notification")
                return
            send_on_failure = self.config_manager.get_config("email", "send_on_failure", "true").lower() == "true"
            send_on_retry = self.config_manager.get_config("email", "send_on_retry", "true").lower() == "true"
            send_on_success = self.config_manager.get_config("email", "send_on_success", "false").lower() == "true"
            should_send = (
                (result.status == "FAILED" and send_on_failure)
                or (result.status == "SUCCESS" and result.retry_count > 0 and send_on_retry)
                or (result.status == "SUCCESS" and result.retry_count == 0 and send_on_success)
            )
            if not should_send:
                return
            subject = f"Task {result.task_name}: {result.status}"
            duration = ""
            if result.start_time and result.end_time:
                duration = str(result.end_time - result.start_time)
            body = (
                f"Task: {result.task_name}\n"
                f"Status: {result.status}\n"
                f"Start Time: {result.start_time}\n"
                f"End Time: {result.end_time}\n"
                f"Duration: {duration}\n"
                f"Exit Code: {result.exit_code}\n"
                f"Retry Count: {result.retry_count}\n\n"
                "Output:\n" + result.output + "\n\nError:\n" + result.error
            )
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = sender_email
            msg["To"] = ", ".join(recipients)
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)
                self.logger.info("Notification sent for task %s", result.task_name)
        except Exception as exc:  # pragma: no cover – don't break execution
            self.logger.exception("Failed to send notification: %s", exc)

    # ------------------------------------------------------------------
    # Scheduler loop (legacy) --------------------------------------------
    # ------------------------------------------------------------------
    def get_next_execution_time(self, task_name: str):  # noqa: D401
        task_config = self.config_manager.get_task(task_name)
        schedule = task_config.get("schedule") if task_config else None
        if not schedule:
            return None
        cron = croniter(schedule, datetime.now())
        return cron.get_next(datetime)

    def run_scheduler(self):  # noqa: D401
        self.logger.info("Starting task scheduler (legacy polling mode)")
        last_minute_check: dict[str, bool] = {}
        while True:
            try:
                current_time = datetime.now()
                current_minute = current_time.strftime("%Y%m%d%H%M")
                for task_name, task_config in self.config_manager.get_all_tasks().items():
                    schedule = task_config.get("schedule")
                    if not schedule:
                        continue
                    key = f"{task_name}_{current_minute}"
                    if key in last_minute_check:
                        continue
                    cron = croniter(schedule, current_time)
                    prev_run = cron.get_prev(datetime)
                    if (current_time - prev_run).total_seconds() < 60:
                        last_minute_check[key] = True
                        thread = threading.Thread(target=self.run_task_with_retry, args=(task_name,))
                        thread.daemon = True
                        thread.start()
                if len(last_minute_check) > 1000:
                    last_minute_check.clear()
                time.sleep(30)
            except KeyboardInterrupt:
                self.logger.info("Scheduler stopped by user")
                break
            except Exception as exc:
                self.logger.exception("Scheduler error: %s", exc)
                time.sleep(60)


# ---------------------------------------------------------------------
# Opt-in CLI helper (kept for backward compatibility) -----------------
# ---------------------------------------------------------------------

def legacy_daemon() -> None:  # noqa: D401
    """Prompt for credentials and run the legacy scheduler."""

    master_password = getpass.getpass("Master password (blank if none): ") or None
    TaskManager(master_password=master_password).run_scheduler()
