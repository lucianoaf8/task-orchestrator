from types import SimpleNamespace
from unittest import mock

import orchestrator.cli as cli


class DummyScheduler:
    def __init__(self):
        self.checked = False

    def check_dependencies(self, name):
        self.checked = True
        return False, "bad"

    def execute_task(self, name):
        from orchestrator.core.task_result import TaskResult
        return TaskResult(task_name=name, status="SUCCESS")


class DummySchedulingService:
    def __init__(self):
        self.unscheduled = []

    def unschedule_task(self, name):
        self.unscheduled.append(name)
        return True


def make_args(**kw):
    defaults = {"task": "foo", "check_deps": False}
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_handle_unschedule(monkeypatch, capsys):
    svc = DummySchedulingService()
    monkeypatch.setattr(cli, "get_scheduling_service", lambda: svc)
    code = cli.handle_unschedule_command(make_args(), None)
    assert code == 0
    assert svc.unscheduled == ["foo"]
    assert "Unscheduled" in capsys.readouterr().out


def test_handle_execute_check_deps(monkeypatch, capsys):
    sched = DummyScheduler()
    code = cli.handle_execute_command(make_args(check_deps=True), sched)
    assert code == 1
    assert sched.checked is True
    assert "Failed" in capsys.readouterr().out


def test_serve_uses_env(monkeypatch):
    fake_app = mock.MagicMock()
    monkeypatch.setattr("orchestrator.web.app.create_app", lambda: fake_app)
    monkeypatch.setenv("ORC_HOST", "1.2.3.4")
    monkeypatch.setenv("ORC_PORT", "123")
    monkeypatch.setenv("ORC_DEBUG", "True")
    cli.serve()
    fake_app.run.assert_called_once_with(host="1.2.3.4", port=123, debug=True)
