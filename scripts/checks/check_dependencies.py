#!/usr/bin/env python3
"""Simple dependency validation utility (Phase-5).

This script is meant to be invoked by Windows Task Scheduler *before* a task
runs, ensuring that all declared dependencies for the given task are present.
It supports three dependency flavours:

1. **file:** `file:C:\path\to\resource` – path must exist.
2. **command:** `command:python --version` – command must return exit-code 0.
3. **url:** `url:https://example.com/health` – HTTP 2xx considered success.

Exit status:
* **0** – every dependency satisfied.
* **1** – one or more dependencies failed; details printed on *stderr*.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from typing import List, Tuple

try:
    import requests  # lightweight dependency; widely available
except ImportError:  # pragma: no cover
    requests = None  # type: ignore

from orchestrator.core.config_manager import ConfigManager


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_file(path: str) -> Tuple[bool, str]:
    exists = os.path.exists(path)
    return exists, "exists" if exists else "file not found"


def _check_command(cmd: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(cmd.split(), capture_output=True, timeout=15)
        ok = result.returncode == 0
        reason = result.stdout.decode().strip() if ok else result.stderr.decode().strip()
        return ok, reason or f"exit-code {result.returncode}"
    except FileNotFoundError:
        return False, "command not found"
    except Exception as exc:  # pragma: no cover – catch-all
        return False, str(exc)


def _check_url(url: str) -> Tuple[bool, str]:
    if requests is None:
        return False, "requests not installed"
    try:
        resp = requests.get(url, timeout=10)
        return resp.ok, f"HTTP {resp.status_code}"
    except Exception as exc:  # pragma: no cover
        return False, str(exc)


def _validate(dep: str) -> Tuple[bool, str]:
    if dep.startswith("file:"):
        return _check_file(dep[5:])
    if dep.startswith("command:"):
        return _check_command(dep[8:])
    if dep.startswith("url:"):
        return _check_url(dep[4:])
    # Unknown spec treated as failure
    return False, "unknown dependency type"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: List[str] | None = None) -> int:  # noqa: D401
    parser = argparse.ArgumentParser(description="Validate task dependencies")
    parser.add_argument("task_name", help="Task name as stored in ConfigManager")
    args = parser.parse_args(argv)

    cm = ConfigManager()
    task = cm.get_task(args.task_name)
    if not task:
        print(f"Error: task '{args.task_name}' not found", file=sys.stderr)
        return 1

    deps: List[str] = task.get("dependencies", [])
    if not deps:
        return 0  # no dependencies to check

    failures: List[str] = []
    for dep in deps:
        ok, reason = _validate(dep)
        if not ok:
            failures.append(f"{dep} – {reason}")

    if failures:
        print("Dependency check failed:\n" + "\n".join(failures), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
