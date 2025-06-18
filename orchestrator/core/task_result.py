"""Dataclass representing the outcome of a task executed via the orchestrator.

This file is part of *Phase 2* of the project-transformation plan and should
remain **framework-agnostic** – it contains no Windows-specific logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

__all__ = ["TaskResult"]


@dataclass
class TaskResult:
    """Standardised task execution result.

    All timestamps are *naive* ``datetime`` objects in local time. Persisting
    to and from the database should convert them to ISO-8601 strings; that
    logic is handled in :pymeth:`to_dict` / :pycmeth:`from_dict`.
    """

    task_name: str
    status: str  # SUCCESS, FAILED, SKIPPED, RUNNING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    output: str = ""
    error: str = ""
    retry_count: int = 0

    # ---------------------------------------------------------------------
    # Convenience helpers
    # ---------------------------------------------------------------------
    @property
    def duration(self) -> Optional[timedelta]:
        """Return *end_time – start_time* if both are set."""

        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    # ------------------------------------------------------------------
    # Serialisation helpers – keep JSON-safe for storage or API output.
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Convert the dataclass to a *plain* dict suitable for JSON."""

        data = asdict(self)
        if self.start_time:
            data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        return data

    def to_json(self) -> str:
        """Dump :pyfunc:`to_dict` result to a JSON string."""

        return json.dumps(self.to_dict(), default=str)

    # ------------------------------------------------------------------
    # Class helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        """Create instance from dictionary (timestamps may be ISO strings)."""

        start = data.get("start_time")
        end = data.get("end_time")

        if isinstance(start, str):
            data["start_time"] = datetime.fromisoformat(start)
        if isinstance(end, str):
            data["end_time"] = datetime.fromisoformat(end)
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "TaskResult":
        """Inverse of :pymeth:`to_json`."""

        return cls.from_dict(json.loads(json_str))
