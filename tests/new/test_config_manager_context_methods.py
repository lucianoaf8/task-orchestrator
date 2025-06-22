import sqlite3
from unittest.mock import MagicMock
import pytest
from orchestrator.core.config_manager import ConfigManager


def test_context_manager_closes(tmp_path):
    db_path = tmp_path / 'db.sqlite'
    with ConfigManager(db_path=str(db_path)) as cm:
        cm.db.execute('SELECT 1')
    with pytest.raises(sqlite3.ProgrammingError):
        cm.db.execute('SELECT 1')


def test_del_closes(tmp_path, monkeypatch):
    cm = ConfigManager(db_path=str(tmp_path / 'db.sqlite'))
    mock_db = MagicMock()
    cm.db = mock_db
    cm.__del__()
    mock_db.close.assert_called_once()
