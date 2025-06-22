"""Light-weight *contextmanager* providing explicit database transactions.

The context manager starts a transaction on *enter* and commits on normal
exit.  If an exception occurs *within* the context the transaction is
**rolled back** and the exception re-raised.  Usage::

    from orchestrator.core.database_transaction import DatabaseTransaction

    with DatabaseTransaction(conn):
        conn.execute("INSERT …")
        conn.execute("UPDATE …")
"""
from __future__ import annotations

import logging
from sqlite3 import Connection, DatabaseError
from typing import Final

_LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class TransactionError(RuntimeError):
    """Raised when a transactional operation fails and is rolled back."""


class DatabaseTransaction:  # noqa: D101 – docstring at top of file
    def __init__(self, connection: Connection):
        self._conn: Final[Connection] = connection

    # ------------------------------------------------------------------
    # Context manager protocol
    # ------------------------------------------------------------------
    def __enter__(self):
        _LOGGER.debug("BEGIN TRANSACTION")
        self._conn.execute("BEGIN")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            _LOGGER.debug("COMMIT TRANSACTION")
            try:
                self._conn.commit()
            except DatabaseError as exc:  # pragma: no cover – rare
                _LOGGER.exception("Commit failed, rolling back.")
                self._conn.rollback()
                raise TransactionError("Commit failed") from exc
            return False  # propagate nothing
        else:
            _LOGGER.debug("ROLLBACK TRANSACTION due to %s", exc_type)
            self._conn.rollback()
            # Do *not* suppress original exception
            return False
