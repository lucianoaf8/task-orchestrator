"""Initial schema matching the ad-hoc structure previously created by
:py:meth:`ConfigManager._init_db`.

After applying this migration the database will contain all tables
required by the *current* version of the orchestrator as well as the
``schema_version`` metadata table populated with version **1**.
"""
from __future__ import annotations

from sqlite3 import Connection

from .migration_base import MigrationBase


class Migration0001InitialSchema(MigrationBase):
    """Bootstrap the database schema."""

    version = 1
    description = "Initial schema with tasks, config, credentials, task_results"

    def up(self) -> None:  # noqa: D401 – imperative style
        self._exec(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                name TEXT PRIMARY KEY,
                type TEXT,
                schedule TEXT,
                command TEXT,
                timeout INTEGER DEFAULT 3600,
                retry_count INTEGER DEFAULT 0,
                retry_delay INTEGER DEFAULT 300,
                dependencies TEXT DEFAULT '[]',
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS config (
                section TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (section, key)
            );

            CREATE TABLE IF NOT EXISTS credentials (
                name TEXT PRIMARY KEY,
                value BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                status TEXT,
                start_time TEXT,
                end_time TEXT,
                exit_code INTEGER,
                output TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (task_name) REFERENCES tasks (name)
            );
            """
        )

    def down(self) -> None:  # noqa: D401
        self._exec(
            """
            DROP TABLE IF EXISTS task_results;
            DROP TABLE IF EXISTS credentials;
            DROP TABLE IF EXISTS config;
            DROP TABLE IF EXISTS tasks;
            """
        )
