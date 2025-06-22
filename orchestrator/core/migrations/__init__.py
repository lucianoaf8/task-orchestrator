"""Database migration framework for the Orchestrator.

Usage
-----
```
conn = sqlite3.connect(path)
apply_pending_migrations(conn)
```

The :pydata:`schema_version` table records the version of the latest
successful migration.  Each migration is represented by a Python module
living in the :pymod:`orchestrator.core.migrations` package and must
contain exactly one subclass of
:class:`orchestrator.core.migrations.migration_base.MigrationBase`.

Migration discovery happens at runtime via :pymod:`importlib`. The file
name **must** start with ``<version>_`` where ``<version>`` is a
zero-padded, *incrementing* integer (e.g. ``0001_initial_schema.py``).
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from sqlite3 import Connection
from typing import Final, List, Type

from .migration_base import MigrationBase

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------


def _iter_migration_modules() -> List[str]:
    """Return *sorted* list of fully-qualified migration module names."""
    pkg_path = Path(__file__).parent
    modules = []
    for module_info in pkgutil.iter_modules([str(pkg_path)]):
        # Expect: 0001_initial_schema, 0002_add_constraints …
        if module_info.name == "__init__" or module_info.ispkg:
            continue
        modules.append(module_info.name)
    modules.sort()  # lexical order fine due to zero-padded prefix
    return [f"{__name__}.{m}" for m in modules]


def _discover_migrations() -> List[Type[MigrationBase]]:
    """Import and return migration classes ordered by ``version``."""
    migrations: List[Type[MigrationBase]] = []
    for module_name in _iter_migration_modules():
        module = importlib.import_module(module_name)
        for attr in vars(module).values():
            if (
                isinstance(attr, type)
                and issubclass(attr, MigrationBase)
                and attr is not MigrationBase
            ):
                migrations.append(attr)
    # Sort by the *version* attribute (int)
    migrations.sort(key=lambda cls: cls.version)  # type: ignore[attr-defined]
    return migrations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def apply_pending_migrations(conn: Connection) -> None:
    """Apply all migrations newer than the current ``schema_version``."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    current_version_row = conn.execute(
        "SELECT MAX(version) FROM schema_version"
    ).fetchone()
    current_version: int = current_version_row[0] if current_version_row and current_version_row[0] else 0

    _LOGGER.info("Current schema version: %s", current_version)

    for migration_cls in _discover_migrations():
        if migration_cls.version <= current_version:
            continue  # already applied

        migration = migration_cls(conn)
        _LOGGER.info("Applying migration %s", migration)
        try:
            with conn:
                migration.up()
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (migration_cls.version,),
                )
        except Exception:  # noqa: BLE001 — want to log *any* error
            _LOGGER.exception("Migration %s failed. Rolling back.", migration)
            raise

    _LOGGER.info("Schema up-to-date.")
