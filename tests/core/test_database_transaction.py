import sqlite3

import pytest

from orchestrator.core.database_transaction import DatabaseTransaction


def test_transaction_commit(tmp_path):
    """Verify commits are persisted and connection is auto-closed."""
    with sqlite3.connect(tmp_path / "db.sqlite") as conn:
        conn.execute("CREATE TABLE t (v INT)")
        with DatabaseTransaction(conn):
            conn.execute("INSERT INTO t VALUES (1)")
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1


def test_transaction_rollback(tmp_path):
    """Verify rollbacks revert writes and connection is auto-closed."""
    with sqlite3.connect(tmp_path / "db.sqlite") as conn:
        conn.execute("CREATE TABLE t (v INT)")
        with pytest.raises(RuntimeError):
            with DatabaseTransaction(conn):
                conn.execute("INSERT INTO t VALUES (1)")
                raise RuntimeError
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
