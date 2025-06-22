"""Add foreign keys, indexes, and cascades for data integrity."""
from __future__ import annotations

from .migration_base import MigrationBase


class Migration0002AddConstraints(MigrationBase):
    version = 2
    description = "Add FK constraints, indexes, and cascade deletes"

    def up(self) -> None:  # noqa: D401
        self._exec(
            """
            PRAGMA foreign_keys = OFF; -- required for SQLite to alter tables

            CREATE TEMPORARY TABLE task_results_backup AS SELECT * FROM task_results;
            DROP TABLE task_results;

            CREATE TABLE task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                status TEXT,
                start_time TEXT,
                end_time TEXT,
                exit_code INTEGER,
                output TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (task_name) REFERENCES tasks (name) ON DELETE CASCADE
            );

            INSERT INTO task_results SELECT * FROM task_results_backup;
            DROP TABLE task_results_backup;

            -- Useful indexes
            CREATE INDEX IF NOT EXISTS idx_task_results_name_time ON task_results(task_name, start_time);
            CREATE INDEX IF NOT EXISTS idx_tasks_enabled ON tasks(enabled) WHERE enabled = 1;

            PRAGMA foreign_keys = ON;
            """
        )

    def down(self) -> None:  # noqa: D401
        self._exec(
            """
            PRAGMA foreign_keys = OFF;

            CREATE TEMPORARY TABLE task_results_backup AS SELECT * FROM task_results;
            DROP TABLE task_results;

            CREATE TABLE task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                status TEXT,
                start_time TEXT,
                end_time TEXT,
                exit_code INTEGER,
                output TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0
            );

            INSERT INTO task_results SELECT * FROM task_results_backup;
            DROP TABLE task_results_backup;

            DROP INDEX IF EXISTS idx_task_results_name_time;
            DROP INDEX IF EXISTS idx_tasks_enabled;

            PRAGMA foreign_keys = ON;
            """
        )
