"""Task-6 Web API Flow Test

Automates the validation steps described in *changes-validations.md* – Task 6.
Starts a Flask instance on port 5002, talks to the API, verifies Windows Task
creation, and cleans up.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://localhost:5002"


def main() -> None:  # noqa: D401
    print("=== Web API Flow Test ===")

    # ------------------------------------------------------------------
    # Step 0 – launch Flask app in a background process
    # ------------------------------------------------------------------
    print("Starting web server (background)…")
    project_root = Path(__file__).resolve().parent
    web_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "flask",
            "--app",
            "orchestrator.web.app:create_app",
            "run",
            "--port",
            "5002",
        ],
        cwd=str(project_root),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        time.sleep(5)  # allow server to bind

        # --------------------------------------------------------------
        # Test-1: create task via API
        # --------------------------------------------------------------
        print("Creating task via API…")
        resp = requests.post(
            f"{BASE_URL}/api/tasks",
            json={
                "name": "api_flow_test",
                "type": "data_job",
                "command": "echo \"API flow test\"",
                "schedule": "0 7 * * *",
                "enabled": True,
            },
            timeout=10,
        )
        if resp.status_code != 200 or not resp.json().get("scheduled"):
            raise RuntimeError(f"Task creation failed → {resp.status_code}: {resp.text}")
        print("✓ Task created & scheduled")

        # --------------------------------------------------------------
        # Test-2: verify Windows Task exists
        # --------------------------------------------------------------
        print("Verifying Windows task exists…")
        result = subprocess.run(
            [
                "schtasks",
                "/query",
                "/tn",
                r"\Orchestrator\Orc_api_flow_test",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError("Scheduled task not found in Windows")
        print("✓ Windows task present")

        # --------------------------------------------------------------
        # Test-3: list scheduled tasks via API
        # --------------------------------------------------------------
        print("Listing scheduled tasks via API…")
        resp = requests.get(f"{BASE_URL}/api/tasks/scheduled", timeout=10)
        if resp.status_code != 200 or "scheduled_tasks" not in resp.json():
            raise RuntimeError("/tasks/scheduled endpoint did not return expected data")
        print(f"✓ API lists {len(resp.json()['scheduled_tasks'])} tasks")

        print("\n🎉 WEB API FLOW TEST PASSED")
        exit_code = 0

    except Exception as exc:
        print(f"\n❌ WEB API FLOW TEST FAILED – {exc}")
        exit_code = 1

    finally:
        # Cleanup – unschedule & stop server
        subprocess.run([sys.executable, "orc.py", "--unschedule", "api_flow_test"], cwd=str(project_root))
        web_proc.terminate()
        web_proc.wait(timeout=5)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
