"""Task-7 Final System Validation script.

Re-implements the checklist commands from *changes-validations.md* so they can
be executed in a single run.
"""

from __future__ import annotations

import subprocess
import sys

from orchestrator.core.config_manager import ConfigManager
from main import trigger_orc_scheduling


def main() -> None:  # noqa: D401
    print("=== Final System Validation ===")

    cm = ConfigManager()
    cm.add_task(
        "final_test",
        "data_job",
        "echo final validation",
        "0 8 * * *",
        enabled=True,
    )
    print("✓ Task database integration working")

    success = trigger_orc_scheduling("final_test")
    print(f"✓ main.py -> orc.py integration: {success}")
    if not success:
        sys.exit(1)

    result = subprocess.run(
        [sys.executable, "orc.py", "--task", "final_test"],
        capture_output=True,
        text=True,
    )
    ok_exec = result.returncode == 0
    print(f"✓ orc.py execution: {ok_exec}")
    if not ok_exec:
        print(result.stderr)
        sys.exit(1)

    history = cm.get_task_history("final_test", 1)
    ok_log = bool(history and history[0]["status"] == "SUCCESS")
    print(f"✓ Result logging: {ok_log}")

    if not ok_log:
        sys.exit(1)

    print("=== System Validation Complete ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
