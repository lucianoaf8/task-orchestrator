"""Utility script to remove orphaned records and old history."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from sqlite3 import connect
from typing import Final

RETENTION_DAYS: Final[int] = 30


def cleanup_orphaned_records(db_path: Path = Path("data/orchestrator.db")) -> None:
    """Remove orphaned *task_results* and old history entries."""
    conn = connect(db_path)
    with conn:
        conn.execute(
            "DELETE FROM task_results WHERE task_name NOT IN (SELECT name FROM tasks)"
        )
        cutoff = (datetime.utcnow() - timedelta(days=RETENTION_DAYS)).isoformat()
        conn.execute(
            "DELETE FROM task_results WHERE start_time < ?", (cutoff,)
        )


if __name__ == "__main__":
    cleanup_orphaned_records()
