"""Base class for all database migrations.

Each migration must inherit from ``MigrationBase`` and implement the
``up`` and ``down`` methods.  The ``version`` class attribute **must** be
an integer greater than 0 and unique across all migrations.

Migrations are run in *ascending* order by version. The orchestrator
records the version of the last successfully applied migration in the
``schema_version`` table.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from sqlite3 import Connection
from typing import Final

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class MigrationBase(ABC):
    """Abstract base-class that all migrations extend."""

    #: Unique, monotonically increasing integer identifying the migration
    version: int = 0
    #: Short human-readable description
    description: str = ""

    def __init__(self, connection: Connection) -> None:
        self._conn: Final[Connection] = connection

    # ---------------------------------------------------------------------
    # Helper functions
    # ---------------------------------------------------------------------
    def _exec(self, sql: str) -> None:  # pragma: no cover – tiny helper
        """Execute *sql* using :py:meth:`sqlite3.Connection.executescript`."""
        self._conn.executescript(sql)

    # ------------------------------------------------------------------
    # Required API
    # ------------------------------------------------------------------
    @abstractmethod
    def up(self) -> None:  # noqa: D401 – imperative verbal form is fine
        """Apply the migration (schema upgrade)."""

    @abstractmethod
    def down(self) -> None:  # noqa: D401
        """Rollback the migration (schema downgrade)."""

    # ------------------------------------------------------------------
    # Misc dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Migration v{self.version} – {self.description}>"
