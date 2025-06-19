import json
from datetime import datetime
from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.task_result import TaskResult


def _cm(tmp_path, password=None):
    db = tmp_path / "db.sqlite"
    return ConfigManager(db_path=str(db), master_password=password)


def test_add_get_task(tmp_path):
    cm = _cm(tmp_path)
    cm.add_task(name="t1", task_type="shell", command="echo hi", schedule="0 0 * * *")
    task = cm.get_task("t1")
    assert task and task["command"] == "echo hi"
    all_tasks = cm.get_all_tasks()
    assert "t1" in all_tasks


def test_credentials_encryption(tmp_path):
    cm = _cm(tmp_path, password="pw")
    cm.store_credential("key", "secret")
    assert cm.get_credential("key") == "secret"


def test_config_storage(tmp_path):
    cm = _cm(tmp_path)
    cm.store_config("sec", "k", "v")
    assert cm.get_config("sec", "k") == "v"


def test_task_history(tmp_path):
    cm = _cm(tmp_path)
    cm.add_task(name="t2", task_type="shell", command="echo", schedule="0 0 * * *")
    res = TaskResult(task_name="t2", status="SUCCESS", start_time=datetime.now(), end_time=datetime.now())
    cm.save_task_result(res)
    hist = cm.get_task_history("t2", 1)
    assert hist and hist[0]["task_name"] == "t2"
