import sqlite3
from unittest import mock
import pytest

from orchestrator.core.config_manager import ConfigManager, TransactionError


def test_validate_config(tmp_path):
    db = tmp_path / 'db.sqlite'
    cm = ConfigManager(db_path=str(db))
    with pytest.raises(TypeError):
        cm._validate_config('email', 'smtp_port', 'bad')
    with pytest.raises(ValueError):
        cm._validate_config('email', 'smtp_port', 0)
    assert cm._validate_config('misc', 'unknown', 'x') == 'x'


def test_add_task_with_scheduling(tmp_path, monkeypatch):
    db = tmp_path / 'db.sqlite'
    cm = ConfigManager(db_path=str(db))
    monkeypatch.setattr(cm, '_schedule_task', lambda name: True)
    cm.add_task_with_scheduling({'name':'t', 'task_type':'shell', 'command':'c', 'enabled':True, 'schedule':'0 0 * * *'})
    assert cm.get_task('t')


def test_add_task_with_scheduling_failure(tmp_path, monkeypatch):
    db = tmp_path / 'db.sqlite'
    cm = ConfigManager(db_path=str(db))
    monkeypatch.setattr(cm, '_schedule_task', lambda n: False)
    with pytest.raises(TransactionError):
        cm.add_task_with_scheduling({'name':'t', 'task_type':'shell', 'command':'c', 'enabled':True, 'schedule':'0 0 * * *'})


def test_get_tasks_paginated(tmp_path):
    cm = ConfigManager(db_path=str(tmp_path/'db.sqlite'))
    for i in range(3):
        cm.add_task(f't{i}', 'shell', 'cmd', schedule=None)
    tasks = cm.get_tasks_paginated(limit=2, offset=1, enabled_only=False, fields=['name'])
    assert len(tasks) == 2 and 'name' in tasks[0]

def test_init_db_handles_corruption(tmp_path, capsys):
    db_file = tmp_path / 'db.sqlite'
    db_file.write_text('not a database')
    cm = ConfigManager(db_path=str(db_file))
    backups = list(tmp_path.glob('db.sqlite.corrupt-*'))
    assert len(backups) == 1
    assert db_file.exists()
    out = capsys.readouterr().out
    assert 'corrupted database file' in out
    cm.close()
