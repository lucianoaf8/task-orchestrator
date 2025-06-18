"""Legacy → Windows Task Scheduler migration helpers (Phase-5)."""
from __future__ import annotations

import logging
from typing import Dict, List

from orchestrator.core.scheduler import TaskScheduler
from orchestrator.core.config_manager import ConfigManager

__all__ = ["LegacyMigration"]

logger = logging.getLogger(__name__)


class LegacyMigration:  # noqa: R0903 – utility wrapper
    """Provide a minimal migration path from the _old_ continuous loop."""

    def __init__(self) -> None:
        self.scheduler = TaskScheduler()
        self.cm = ConfigManager()

    # ------------------------------------------------------------------
    # Detection helpers
    # ------------------------------------------------------------------
    def detect_legacy_process(self) -> bool:  # noqa: D401
        """Stub: return **False** until legacy loop is formally deprecated."""
        # Actual detection could look for old PID file, etc.
        return False

    # ------------------------------------------------------------------
    # Migration operations
    # ------------------------------------------------------------------
    def migrate_all_tasks(self) -> Dict[str, bool]:  # noqa: D401
        """Schedule every enabled task in Windows Task Scheduler."""
        results: Dict[str, bool] = {}
        for name in self.cm.get_all_tasks().keys():
            ok = self.scheduler.schedule_task(name)
            results[name] = ok
        return results

    def validate_migration(self) -> bool:  # noqa: D401
        """Simple validation – all enabled tasks must now exist in scheduler."""
        tasks: List[str] = list(self.cm.get_all_tasks().keys())
        for name in tasks:
            if not self.scheduler.task_exists(name):
                logger.error("Task %s missing after migration", name)
                return False
        return True

    def rollback_migration(self) -> None:  # noqa: D401
        """Delete all orchestrator tasks – restores pre-migration state."""
        for name in self.cm.get_all_tasks().keys():
            self.scheduler.unschedule_task(name)

    # ------------------------------------------------------------------
    # Convenience entry point
    # ------------------------------------------------------------------
    def migrate(self) -> bool:  # noqa: D401
        """High-level helper used by CLI (main.py migrate)."""
        results = self.migrate_all_tasks()
        if all(results.values()):
            return self.validate_migration()
        logger.error("Migration failed for: %s", [k for k, v in results.items() if not v])
        return False
