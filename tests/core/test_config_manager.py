import sqlite3
from orchestrator.core.config_manager import ConfigManager


def test_add_and_get_task(tmp_path):
    db = tmp_path / "db.sqlite"
    cm = ConfigManager(db_path=str(db))
    cm.add_task("demo", "shell", "echo 1", schedule="0 0 * * *")
    task = cm.get_task("demo")
    assert task and task["command"] == "echo 1"


def test_store_and_get_credential(tmp_path):
    db = tmp_path / "db.sqlite"
    cm = ConfigManager(db_path=str(db), master_password="pass")
    cm.store_credential("key", "secret")
    assert cm.get_credential("key") == "secret"
