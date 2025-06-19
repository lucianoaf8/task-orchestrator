#!/usr/bin/env python3
"""
Task Simulator - Automated Task Lifecycle Testing
Simulates user interaction to create, schedule, monitor, and verify task execution.
"""

import os
import sys
import subprocess
import time
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple
import sqlite3
import argparse

# Constants
PROJECT_ROOT = Path(__file__).resolve().parent
TIMEOUT_SECONDS = 300  # 5 minutes
POLL_INTERVAL = 10  # Check every 10 seconds
TEST_OUTPUT_DIR = PROJECT_ROOT / "test_outputs"

class TaskSimulator:
    def __init__(
        self,
        *,
        keep_task: bool = False,
        existing_task: str | None = None,
        update_schedule: str | None = None,
        marker: str | None = None,
    ):
        """Create a TaskSimulator instance.

        Args:
            keep_task: Do not remove the task after the simulation.
            existing_task: If supplied, **skip the creation step** and instead
                monitor the already-scheduled task of that name. This is handy
                when validating edits to a pre-existing task definition.
            update_schedule: For existing task: new cron schedule (e.g. "*/5 * * * *")
            marker: For existing task: append TEXT marker line to output file each run
        """
        self.keep_task = keep_task
        self.existing_task = existing_task
        self.update_schedule = update_schedule
        self.marker = marker
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.existing_task:
            self.task_name = self.existing_task
            # Output file path unknown – default to test_outputs dir but may not exist
            self.output_file = TEST_OUTPUT_DIR / f"{self.task_name}_last_output.txt"
        else:
            self.task_name = f"simulator_test_{self.timestamp}"
            self.output_file = TEST_OUTPUT_DIR / f"test_output_{self.timestamp}.txt"
        self.db_path = PROJECT_ROOT / "data" / "orchestrator.db"
        self.log_file = PROJECT_ROOT / "logs" / f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Ensure test output directory exists
        TEST_OUTPUT_DIR.mkdir(exist_ok=True)
        
        print(f"[INIT] Task Simulator initialized")
        print(f"[INIT] Task name: {self.task_name}")
        print(f"[INIT] Output file: {self.output_file}")
    
    def preflight_checks(self) -> bool:
        """Verify system is ready for simulation"""
        print("\n=== PRE-FLIGHT CHECKS ===")
        
        # Check database exists
        if not self.db_path.exists():
            print(f"[ERROR] Database not found at {self.db_path}")
            return False
        print(f"[OK] Database found: {self.db_path}")
        
        # Check main.py exists
        main_py = PROJECT_ROOT / "main.py"
        if not main_py.exists():
            print(f"[ERROR] main.py not found")
            return False
        print(f"[OK] main.py found")
        
        # Check orc.py exists
        orc_py = PROJECT_ROOT / "orc.py"
        if not orc_py.exists():
            print(f"[ERROR] orc.py not found")
            return False
        print(f"[OK] orc.py found")
        
        # Test database connection
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("SELECT COUNT(*) FROM tasks")
            conn.close()
            print("[OK] Database connection successful")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
        
        return True
    
    def create_task(self) -> bool:
        """Create task via main.py CLI"""
        print("\n=== TASK CREATION ===")
        
        # Prepare command that creates output file – use absolute Python path so that
        # Windows Task Scheduler does not rely on system %PATH%.
        python_exe = sys.executable.replace("\\", "\\\\")  # escape backslashes for cmd string
        # Use single quotes inside the Python -c string to avoid clashing with the outer double quotes
        task_command = (
            f'"{python_exe}" -c "import datetime, pathlib; '
            f'p = pathlib.Path(r\'{self.output_file}\'); '
            f'p.parent.mkdir(parents=True, exist_ok=True); '
            f'p.write_text(\'SUCCESS at \'+ str(datetime.datetime.now()))"'
        )
        
        # Prepare input for interactive mode
        # Menu: 2 (Add task), then task details, then 7 (Exit)
        user_input = f"""2
{self.task_name}
data_job
{task_command}
*/1 * * * *
7
"""
        
        print(f"[INFO] Creating task: {self.task_name}")
        print(f"[INFO] Command: {task_command}")
        print(f"[INFO] Schedule: Every minute")
        
        try:
            # Run main.py in interactive mode with piped input
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            stdout, stderr = process.communicate(input=user_input, timeout=30)
            
            # Check for success indicators
            if "Task 'simulator_test" in stdout and "saved to database" in stdout:
                print("[OK] Task saved to database")
                
                if "scheduled successfully" in stdout:
                    print("[OK] Task scheduled via orc.py")
                    return True
                else:
                    print("[ERROR] Task saved but scheduling failed")
                    print(f"[DEBUG] stdout: {stdout}")
                    return False
            else:
                print("[ERROR] Task creation failed")
                print(f"[DEBUG] stdout: {stdout}")
                print(f"[DEBUG] stderr: {stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("[ERROR] Task creation timed out")
            return False
        except Exception as e:
            print(f"[ERROR] Task creation failed: {e}")
            return False
    
    def verify_scheduling(self) -> bool:
        """Verify task is scheduled in Windows"""
        print("\n=== SCHEDULING VERIFICATION ===")
        
        # Check via orc.py --list
        try:
            result = subprocess.run(
                [sys.executable, "orc.py", "--list"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            if self.task_name in result.stdout:
                print(f"[OK] Task found in orc.py --list")
            else:
                print(f"[ERROR] Task not found in orc.py --list")
                print(f"[DEBUG] Output: {result.stdout}")
                return False
            
        except Exception as e:
            print(f"[ERROR] Failed to list tasks: {e}")
            return False
        
        # Check Windows Task Scheduler
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", f"\\Orchestrator\\Orc_{self.task_name}", "/fo", "LIST"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"[OK] Task found in Windows Task Scheduler")
                
                # Parse next run time
                for line in result.stdout.split('\n'):
                    if "Next Run Time:" in line:
                        next_run = line.split(":", 1)[1].strip()
                        print(f"[INFO] Next scheduled run: {next_run}")
                        break
                
                return True
            else:
                print(f"[ERROR] Task not found in Windows Task Scheduler")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to query Windows tasks: {e}")
            return False
    
    def monitor_execution(self) -> bool:
        """Monitor task execution until success or timeout"""
        print("\n=== EXECUTION MONITORING ===")
        print(f"[INFO] Waiting for task execution (timeout: {TIMEOUT_SECONDS}s)")
        
        start_time = time.time()
        # Record current latest DB result to require a *new* run
        baseline_db_time = self.get_latest_db_start_time()
        last_log_position = 0
        
        while time.time() - start_time < TIMEOUT_SECONDS:
            elapsed = int(time.time() - start_time)
            last_run, next_run, last_result = self.get_windows_task_times()
            print(f"\n[POLL] Checking execution status ({elapsed}s elapsed)...")
            print(f"Task: {self.task_name}")
            print(f"  Last run : {last_run or 'N/A'}")
            print(f"  Next run : {next_run or 'N/A'}")
            
            # Check 1: Output file exists
            if self.output_file.exists():
                print(f"[OK] Output file created: {self.output_file}")
                content = self.output_file.read_text()
                print(f"[OK] File content: {content}")
                
                # Verify content is correct
                if "SUCCESS at" in content:
                    print("[OK] Output file contains expected content")
                    
                    # Check database for confirmation
                    if self.check_database_result(after_time=baseline_db_time):
                        return True
                    else:
                        print("[WARN] File created but database not updated yet")
            
            # Check 2: Database task_results
            if self.check_database_result(after_time=baseline_db_time):
                print("[OK] Database shows successful execution")
                return True
            
            # Check 3: Monitor logs
            last_log_position = self.check_logs(last_log_position)
            
            # Check 4: Windows task info already fetched above; optionally log last_result
            if last_result:
                print(f"  Last result: {last_result}")
                # Fail fast if the task has already returned a non-zero result twice
                # Ignore common non-error status codes
                harmless_codes = {0, 267009, 267010, 267011}  # 0 = success, others = running/disabled/not yet run
                try:
                    code_int = int(last_result)
                except ValueError:
                    code_int = 1  # treat as generic error
                if code_int not in harmless_codes and elapsed > 30:
                    print("[ERROR] Task reported failure via Windows Scheduler (code", code_int, ")")
                    return False
            
            # Wait before next poll
            time.sleep(POLL_INTERVAL)
        
        print(f"\n[ERROR] Task execution timed out after {TIMEOUT_SECONDS} seconds")
        return False
    
    def check_database_result(self, after_time: Optional[datetime] = None) -> bool:
        """Check if task execution is recorded in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Query latest result for our task
            cursor.execute(
                """
                SELECT status, start_time, end_time, exit_code, output, error
                FROM task_results
                WHERE task_name = ?
                ORDER BY start_time DESC
                LIMIT 1
                """,
                (self.task_name,),
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                status, start_time, end_time, exit_code, output, error = result
                print(f"[DB] Task result found - Status: {status}")
                
                if status == "SUCCESS":
                    # Ensure this is a *new* run compared with baseline
                    is_new = True
                    if after_time and start_time:
                        try:
                            run_time = datetime.fromisoformat(start_time)
                            is_new = run_time > after_time
                        except Exception:
                            # If parsing fails, fall back to True to avoid false negatives
                            is_new = True
                    print(f"[DB] Start time: {start_time}")
                    print(f"[DB] End time: {end_time}")
                    print(f"[DB] Exit code: {exit_code}")
                    if is_new:
                        return True
                    print("[INFO] Success record is not newer than baseline; continuing to wait…")
                else:
                    print(f"[DB] Task failed - Error: {error}")
                    
            return False
            
        except Exception as e:
            print(f"[ERROR] Database query failed: {e}")
            return False
    
    def get_latest_db_start_time(self) -> Optional[datetime]:
        """Return timestamp of latest task_result row for this task."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT start_time FROM task_results
                WHERE task_name = ?
                ORDER BY start_time DESC
                LIMIT 1
                """,
                (self.task_name,),
            )
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                try:
                    return datetime.fromisoformat(row[0])
                except Exception:
                    return None
            return None
        except Exception:
            return None

    def check_logs(self, last_position: int) -> int:
        """Check orchestrator logs for task execution"""
        try:
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    f.seek(last_position)
                    new_lines = f.read()
                    
                    if new_lines and self.task_name in new_lines:
                        for line in new_lines.split('\n'):
                            if self.task_name in line:
                                print(f"[LOG] {line.strip()}")
                    
                    return f.tell()
            
        except Exception as e:
            print(f"[WARN] Could not read logs: {e}")
        
        return last_position
    
    def get_windows_task_times(self):
        """Return (last_run, next_run, last_result) for the Windows task."""
        try:
            result = subprocess.run(
                [
                    "schtasks",
                    "/query",
                    "/tn",
                    f"\\Orchestrator\\Orc_{self.task_name}",
                    "/fo",
                    "LIST",
                    "/v",
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return None, None, None

            last_run = next_run = last_result = None
            for line in result.stdout.split("\n"):
                if "Last Run Time:" in line:
                    val = line.split(":", 1)[1].strip()
                    if val and val.upper() != "N/A":
                        last_run = val
                elif "Next Run Time:" in line:
                    val = line.split(":", 1)[1].strip()
                    if val and val.upper() != "N/A":
                        next_run = val
                elif "Last Result:" in line:
                    val = line.split(":", 1)[1].strip()
                    if val and val != "267011":  # 267011 = Task has not yet run
                        last_result = val
            return last_run, next_run, last_result
        except Exception:
            return None, None, None

    
    def cleanup(self):
        """Clean up test artifacts"""
        print("\n=== CLEANUP ===")
        if getattr(self, 'keep_task', False) or self.existing_task:
            print("[INFO] --keep-task flag set – skipping unschedule and output-file deletion")
            return
        
        # Unschedule task
        try:
            result = subprocess.run(
                [sys.executable, "orc.py", "--unschedule", self.task_name],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            if result.returncode == 0:
                print(f"[OK] Task unscheduled")
            else:
                print(f"[WARN] Failed to unschedule task: {result.stderr}")
                
        except Exception as e:
            print(f"[ERROR] Cleanup failed: {e}")
        
        # Delete output file
        if self.output_file.exists():
            self.output_file.unlink()
            print(f"[OK] Output file deleted")
    
    def apply_updates(self) -> bool:
        """Apply schedule/command updates via `orc.py --update`."""
        print("\n=== TASK UPDATE ===")

        cmd: list[str] = [sys.executable, "orc.py", "--update", self.task_name]

        if self.update_schedule:
            cmd += ["--new-schedule", self.update_schedule]
            print(f"[INFO] Requesting schedule: {self.update_schedule}")

        if self.marker is not None:
            # Build command string executed by Windows Task Scheduler
            python_exe = sys.executable
            script_path = PROJECT_ROOT / "scripts" / "write_marker.py"
            parts = [python_exe, str(script_path), "--out", str(self.output_file)]
            if self.marker:
                parts += ["--marker", self.marker]
            new_command = subprocess.list2cmdline(parts)
            cmd += ["--new-command", new_command]
            print(f"[INFO] Requesting command : {new_command}")

        print(f"[INFO] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if result.returncode == 0:
            print("[OK] Task update succeeded")
            return True
        print("[ERROR] Task update failed")
        print(f"[DEBUG] stdout: {result.stdout}")
        print(f"[DEBUG] stderr: {result.stderr}")
        return False

    def run(self) -> int:
        """Run complete simulation"""
        print("=== TASK SIMULATOR START ===")
        print(f"[INFO] Timestamp: {datetime.now()}")
        print(f"[INFO] Project root: {PROJECT_ROOT}")
        
        try:
            # Pre-flight checks
            if not self.preflight_checks():
                return 1
            
            # Create task unless we are monitoring an existing one
            if not self.existing_task:
                if not self.create_task():
                    return 2
            else:
                print("\n=== EXISTING TASK MODE ===")
                print(f"[INFO] Monitoring existing task: {self.task_name}")
                if self.update_schedule or self.marker is not None:
                    if not self.apply_updates():
                        return 3
            
            # Verify scheduling
            if not self.verify_scheduling():
                return 3
            
            # Monitor execution
            if not self.monitor_execution():
                return 4
            
            print("\n=== SIMULATION SUCCESSFUL ===")
            print(f"[OK] Task '{self.task_name}' completed full lifecycle")
            return 0
            
        except KeyboardInterrupt:
            print("\n[ABORT] Simulation interrupted by user")
            return 5
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            return 6
        finally:
            # Always cleanup
            self.cleanup()
            print("\n=== TASK SIMULATOR END ===")


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="Task Simulator – Automated Task Lifecycle Testing")
    parser.add_argument('--keep-task', action='store_true', help='Do not unschedule or delete the task after simulation completes')
    parser.add_argument('--update-schedule', metavar='CRON', help='For existing task: new cron schedule (e.g. "*/3 * * * *")')
    parser.add_argument('--marker', metavar='TEXT', help='For existing task: append TEXT marker line to output file each run')
    parser.add_argument('--use-existing', metavar='TASK_NAME', help='Skip creation and monitor an already-scheduled task')
    args = parser.parse_args()
    simulator = TaskSimulator(
        keep_task=args.keep_task,
        existing_task=args.use_existing,
        update_schedule=args.update_schedule,
        marker=args.marker,
    )
    exit_code = simulator.run()
    
    # Print summary
    print(f"\nExit code: {exit_code}")
    print("Exit codes: 0=success, 1=preflight failed, 2=creation failed, " +
          "3=scheduling failed, 4=execution failed, 5=interrupted, 6=error")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()