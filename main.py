"""Main entry point for the Task Python Orchestrator.

This module provides the command-line interface for the orchestrator.
Currently maintains the old daemon-style orchestrator for backward compatibility.
"""

import os
import sys
import time
import logging
import smtplib
import json
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from croniter import croniter
from dataclasses import dataclass

from orchestrator.core.config_manager import ConfigManager

@dataclass
class TaskResult:
    task_name: str
    status: str  # SUCCESS, FAILED, SKIPPED, RUNNING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    output: str = ""
    error: str = ""
    retry_count: int = 0

class TaskManager:
    def __init__(self, db_path: str = "data/orchestrator.db", master_password: str | None = None):
        self.config_manager = ConfigManager(db_path, master_password)
        self.running_tasks = {}
        self.setup_logging()
        # Ensure core condition tasks exist so that dependency checks work reliably.
        self._ensure_condition_tasks()
        
    def setup_logging(self):
        log_dir = self.config_manager.get_config('logging', 'directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_level = getattr(logging, self.config_manager.get_config('logging', 'level', 'INFO'))
        
        # Create daily log file
        log_file = os.path.join(log_dir, f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        
    def check_dependencies(self, task_name: str) -> tuple[bool, str]:
        """Check if all dependencies are satisfied"""
        task_config = self.config_manager.get_task(task_name)
        dependencies = task_config.get('dependencies', [])
        
        if not dependencies:
            return True, "No dependencies"
            
        failed_deps = []
        for dep in dependencies:
            dep_config = self.config_manager.get_task(dep)
            if not dep_config:
                failed_deps.append(f"{dep} (not found)")
                continue
                
            # For condition tasks, run them on-demand
            if dep_config.get('type') == 'condition':
                result = self.run_task(dep)
                if result.status != 'SUCCESS':
                    failed_deps.append(dep)
            else:
                # Check recent execution history
                history = self.config_manager.get_task_history(dep, 1)
                if not history or history[0]['status'] != 'SUCCESS':
                    failed_deps.append(dep)
        
        if failed_deps:
            return False, f"Failed dependencies: {', '.join(failed_deps)}"
        return True, "All dependencies satisfied"
    
    def _ensure_condition_tasks(self) -> None:
        """Ensure essential condition tasks are present in the DB.

        Currently registers the ``check_db_connection`` task so it can be
        invoked on-demand whenever another task lists it as a dependency.
        """
        if self.config_manager.get_task("check_db_connection"):
            return  # Already configured

        script_path = os.path.join(os.path.dirname(__file__), "scripts", "checks", "check_db_connection.py")
        command = f"{sys.executable} {script_path}"

        # Register the task as a *condition* type, executed only when requested
        # by dependency resolution (no schedule).
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

    def run_task(self, task_name: str) -> TaskResult:
        """Execute a single task"""
        if task_name in self.running_tasks:
            self.logger.warning(f"Task {task_name} is already running")
            return TaskResult(task_name, "SKIPPED", error="Task already running")
        
        task_config = self.config_manager.get_task(task_name)
        if not task_config:
            return TaskResult(task_name, "FAILED", error="Task not found")
            
        result = TaskResult(task_name, "RUNNING", start_time=datetime.now())
        self.running_tasks[task_name] = result
        self.logger.info(f"Starting task: {task_name}")
        
        try:
            # Check dependencies
            deps_ok, deps_msg = self.check_dependencies(task_name)
            if not deps_ok:
                result.status = "SKIPPED"
                result.error = deps_msg
                result.end_time = datetime.now()
                self.logger.warning(f"Task {task_name} skipped: {deps_msg}")
                return result
            
            # Execute command
            command = task_config['command']
            timeout = task_config.get('timeout', 3600)
            
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                result.exit_code = process.returncode
                result.output = stdout
                result.error = stderr
                
                if result.exit_code == 0:
                    result.status = "SUCCESS"
                    self.logger.info(f"Task {task_name} completed successfully")
                else:
                    result.status = "FAILED"
                    self.logger.error(f"Task {task_name} failed with exit code {result.exit_code}")
                    
            except subprocess.TimeoutExpired:
                process.kill()
                result.status = "FAILED"
                result.error = f"Task timed out after {timeout} seconds"
                self.logger.error(f"Task {task_name} timed out")
                
        except Exception as e:
            result.status = "FAILED"
            result.error = str(e)
            self.logger.error(f"Task {task_name} failed with exception: {e}")
        
        finally:
            result.end_time = datetime.now()
            self.running_tasks.pop(task_name, None)
            
            # Store result in database
            self.config_manager.save_task_result(result)
            
            # Send notification
            self.send_notification(result)
            
        return result
    
    def run_task_with_retry(self, task_name: str) -> TaskResult:
        """Run task with retry logic"""
        task_config = self.config_manager.get_task(task_name)
        retry_count = task_config.get('retry_count', 0)
        retry_delay = task_config.get('retry_delay', 300)
        
        for attempt in range(retry_count + 1):
            result = self.run_task(task_name)
            result.retry_count = attempt
            
            if result.status == "SUCCESS" or attempt == retry_count:
                return result
                
            if result.status == "FAILED":
                self.logger.info(f"Retrying task {task_name} in {retry_delay} seconds (attempt {attempt + 1}/{retry_count + 1})")
                time.sleep(retry_delay)
                
        return result
    
    def send_notification(self, result: TaskResult):
        """Send email notification for task result"""
        try:
            # Get email configuration
            smtp_server = self.config_manager.get_config('email', 'smtp_server', 'smtp.office365.com')
            smtp_port = int(self.config_manager.get_config('email', 'smtp_port', '587'))
            sender_email = self.config_manager.get_credential('email_username')
            password = self.config_manager.get_credential('email_password')
            recipients_json = self.config_manager.get_config('email', 'recipients', '[]')
            recipients = json.loads(recipients_json) if recipients_json else []
            
            if not all([sender_email, password, recipients]):
                self.logger.warning("Email configuration incomplete, skipping notification")
                return
            
            # Only send notifications for failures and retries
            send_on_failure = self.config_manager.get_config('email', 'send_on_failure', 'true').lower() == 'true'
            send_on_retry = self.config_manager.get_config('email', 'send_on_retry', 'true').lower() == 'true'
            send_on_success = self.config_manager.get_config('email', 'send_on_success', 'false').lower() == 'true'
            
            should_send = (
                (result.status == "FAILED" and send_on_failure) or
                (result.status == "SUCCESS" and result.retry_count > 0 and send_on_retry) or
                (result.status == "SUCCESS" and result.retry_count == 0 and send_on_success)
            )
            
            if not should_send:
                return
                
            subject = f"Task {result.task_name}: {result.status}"
            
            duration = ""
            if result.start_time and result.end_time:
                duration = str(result.end_time - result.start_time)
            
            body = f"""
Task: {result.task_name}
Status: {result.status}
Start Time: {result.start_time}
End Time: {result.end_time}
Duration: {duration}
Exit Code: {result.exit_code}
Retry Count: {result.retry_count}

Output:
{result.output}

Error:
{result.error}
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)
                self.logger.info(f"Notification sent for task {result.task_name}")
                    
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
    
    def get_next_execution_time(self, task_name: str) -> Optional[datetime]:
        """Get next scheduled execution time for a task"""
        task_config = self.config_manager.get_task(task_name)
        schedule = task_config.get('schedule') if task_config else None
        
        if not schedule:
            return None
            
        cron = croniter(schedule, datetime.now())
        return cron.get_next(datetime)
    
    def run_scheduler(self):
        """Main scheduler loop"""
        self.logger.info("Starting task scheduler")
        last_minute_check = {}
        
        while True:
            try:
                current_time = datetime.now()
                current_minute = current_time.strftime('%Y%m%d%H%M')
                
                for task_name, task_config in self.config_manager.get_all_tasks().items():
                    schedule = task_config.get('schedule')
                    if not schedule:
                        continue
                        
                    # Prevent duplicate runs within same minute
                    task_minute_key = f"{task_name}_{current_minute}"
                    if task_minute_key in last_minute_check:
                        continue
                    
                    # Check if task should run now
                    cron = croniter(schedule, current_time)
                    prev_run = cron.get_prev(datetime)
                    
                    # If the previous run time is within the last minute
                    if (current_time - prev_run).total_seconds() < 60:
                        last_minute_check[task_minute_key] = True
                        
                        # Run the task in a separate thread
                        self.logger.info(f"Scheduling task: {task_name}")
                        thread = threading.Thread(
                            target=self.run_task_with_retry, 
                            args=(task_name,)
                        )
                        thread.daemon = True
                        thread.start()
                
                # Cleanup old minute checks to prevent memory growth
                if len(last_minute_check) > 1000:
                    last_minute_check.clear()
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
                
            except KeyboardInterrupt:
                self.logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait a minute on error

def main():
    """Main entry point for the orchestrator"""
    import getpass
    
    # Get master password for encryption
    master_password = getpass.getpass("Enter master password (or press Enter for no encryption): ")
    if not master_password.strip():
        master_password = None
    
    manager = TaskManager(master_password=master_password)
    manager.run_scheduler()

if __name__ == "__main__":
    main()