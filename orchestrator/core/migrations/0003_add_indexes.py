"""Add performance indexes for tasks and task_results (Phase C1)."""
from __future__ import annotations

from .migration_base import MigrationBase


class Migration0003AddIndexes(MigrationBase):
    """Create indexes improving frequent query patterns."""

    version = 3
    description = "Add indexes on tasks.enabled and task_results (task_name, status)"

    def up(self) -> None:  # noqa: D401
        self._exec(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_enabled ON tasks (enabled);
            CREATE INDEX IF NOT EXISTS idx_task_results_task_status
                ON task_results (task_name, status);
            """
        )

    def down(self) -> None:  # noqa: D401
        self._exec(
            """
            DROP INDEX IF EXISTS idx_task_results_task_status;
            DROP INDEX IF EXISTS idx_tasks_enabled;
            """
        )
