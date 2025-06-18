"""Utility to clean up legacy continuous-loop processes (Phase-5)."""
from __future__ import annotations

import os
import signal
import subprocess
from typing import List

__all__ = ["cleanup_legacy"]


def _find_legacy_pids() -> List[int]:
    """Return PIDs of running `python main.py` legacy loop (best-effort)."""
    # Very naive implementation for Windows – relies on `tasklist` output.
    try:
        txt = subprocess.check_output(["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"], text=True)
    except Exception:
        return []

    pids: List[int] = []
    for line in txt.splitlines()[1:]:  # skip header
        parts = [p.strip("\"") for p in line.split(",")]
        if len(parts) >= 2 and parts[0].lower() == "python.exe" and "main.py" in parts[-1]:
            try:
                pids.append(int(parts[1]))
            except ValueError:
                continue
    return pids


def cleanup_legacy() -> int:  # noqa: D401
    """Terminate any residual legacy TaskManager loop processes."""
    pids = _find_legacy_pids()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except PermissionError:
            print(f"Insufficient permissions to terminate PID {pid}")
        except Exception as exc:  # pragma: no cover
            print(f"Error terminating PID {pid}: {exc}")
    return len(pids)


if __name__ == "__main__":
    count = cleanup_legacy()
    print(f"Stopped {count} legacy process(es)")
