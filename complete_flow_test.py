"""Complete Flow Validation Test Script

This script programmatically validates the full lifecycle of a task in the
orchestrator system, from creation, scheduling (via orc.py), execution, result
logging, and finally cleanup of the Windows scheduled task.

The script follows exactly the validation plan outlined in
`changes-validations.md` Task 5.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

try:
    from orchestrator.core.config_manager import ConfigManager
except ImportError as exc:  # pragma: no cover
    print(f"❌ Unable to import ConfigManager: {exc}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _run(cmd: list[str] | str, *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    """Execute *cmd* and return the completed process.

    Args:
        cmd: Command (list or string) to execute via *subprocess.run*.
        capture: If *True*, captures stdout/stderr; otherwise they inherit the
            current process streams.
    """
    if isinstance(cmd, str):
        cmd_list = cmd.split()
    else:
        cmd_list = cmd

    return subprocess.run(
        cmd_list,
        capture_output=capture,
        text=True,
        shell=False,
        check=False,
    )


def _print_success(msg: str) -> None:
    print(f"\u2713 {msg}")  # ✓


def _print_fail(msg: str) -> None:
    print(f"\u2717 {msg}")  # ✗


# ---------------------------------------------------------------------------
# Validation Steps
# ---------------------------------------------------------------------------

def test_complete_flow() -> bool:
    print("=== Complete Flow Validation Test ===")

    # Step 1: Create task and trigger scheduling
    print("Step 1: Creating and scheduling test task...")
    try:
        cm = ConfigManager()
        cm.add_task(
            name="flow_test_task",
            task_type="data_job",
            command="echo \"Flow test successful\"",
            schedule="0 6 * * *",
            enabled=True,
        )
        _print_success("Task saved to database")

        from main import trigger_orc_scheduling  # local import to avoid cycles

        success = trigger_orc_scheduling("flow_test_task")
        if success:
            _print_success("Scheduling via orc.py succeeded")
        else:
            _print_fail("Scheduling via orc.py failed")
            return False
    except Exception as exc:  # pragma: no cover
        _print_fail(f"Step 1 failed: {exc}")
        return False

    # Step 2: Verify Windows Task creation
    print("\nStep 2: Verifying Windows Task...")
    result = _run([
        "schtasks",
        "/query",
        "/tn",
        r"\Orchestrator\Orc_flow_test_task",
    ])
    if result.returncode == 0:
        _print_success("Windows Task exists")
    else:
        _print_fail("Windows Task not found")
        return False

    # Step 3: Test execution via orc.py
    print("\nStep 3: Testing task execution...")
    result = _run(["python", "orc.py", "--task", "flow_test_task"])
    if result.returncode == 0:
        _print_success("Task execution successful")
    else:
        _print_fail(f"Task execution failed: {result.stderr.strip()}")
        return False

    # Step 4: Verify execution logging
    print("\nStep 4: Verifying execution logging...")
    try:
        history = cm.get_task_history("flow_test_task", 1)
        if history and history[0]["status"] == "SUCCESS":
            _print_success("Task execution logged successfully")
        else:
            _print_fail("Task execution not logged properly")
            return False
    except Exception as exc:  # pragma: no cover
        _print_fail(f"Step 4 failed: {exc}")
        return False

    # Cleanup
    print("\nCleaning up...")
    _run(["python", "orc.py", "--unschedule", "flow_test_task"], capture=False)
    _print_success("Cleanup complete")

    return True


if __name__ == "__main__":
    succeeded = test_complete_flow()
    if succeeded:
        print("\n🎉 COMPLETE FLOW TEST PASSED")
        sys.exit(0)
    else:
        print("\n❌ COMPLETE FLOW TEST FAILED")
        sys.exit(1)
