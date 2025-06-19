import logging
from types import SimpleNamespace
from orchestrator.core.task_result import TaskResult
import orc


class DummyScheduler:
    def __init__(self):
        self.config_manager = SimpleNamespace(get_task=lambda n: {"command": "cmd", "schedule": "0 0 * * *"})
    def validate_task_config(self, n):
        return True, "OK"
    def schedule_task(self, n):
        return True
    def execute_task(self, n):
        return TaskResult(task_name=n, status="SUCCESS")
    def list_scheduled_tasks(self):
        return [{"TaskName": r"\\Orchestrator\\Orc_test", "Status": "Ready"}]
    def unschedule_task(self, n):
        return True


def test_schedule_operation(monkeypatch):
    monkeypatch.setattr(orc, "TaskScheduler", lambda: DummyScheduler())
    assert orc.schedule_task_operation("test", logging.getLogger(__name__)) is True


def test_execute_operation(monkeypatch):
    monkeypatch.setattr(orc, "TaskScheduler", lambda: DummyScheduler())
    assert orc.execute_task_operation("test", logging.getLogger(__name__)) is True


def test_list_operation(monkeypatch, capsys):
    monkeypatch.setattr(orc, "TaskScheduler", lambda: DummyScheduler())
    assert orc.list_tasks_operation(logging.getLogger(__name__)) is True
    captured = capsys.readouterr()
    assert "test" in captured.out


def test_unschedule_operation(monkeypatch):
    monkeypatch.setattr(orc, "TaskScheduler", lambda: DummyScheduler())
    assert orc.unschedule_task_operation("test", logging.getLogger(__name__)) is True
