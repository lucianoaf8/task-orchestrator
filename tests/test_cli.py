import json
from types import SimpleNamespace
from unittest import mock
import pytest

import orchestrator.cli as cli

class DummyScheduler:
    def __init__(self):
        self.called = {}
    def validate_task_config(self, name):
        return True, 'OK'
    def check_dependencies(self, name):
        return True, 'OK'
    def execute_task(self, name):
        from orchestrator.core.task_result import TaskResult
        return TaskResult(task_name=name, status='SUCCESS')


class DummyTaskService:
    def __init__(self):
        self.tasks = {'foo': {'command': 'cmd', 'schedule': '0 0 * * *'}}
    def list_tasks(self):
        return self.tasks
    def get_task(self, name):
        return self.tasks.get(name)

class DummySchedulingService:
    def __init__(self):
        self.scheduled = []
    def list_tasks(self):
        return [{'TaskName': 'foo', 'Status': 'Ready'}]
    def schedule_task(self, name, cmd, cron):
        self.scheduled.append(name)
        return True
    def unschedule_task(self, name):
        self.scheduled.append(f'un-{name}')
        return True


def make_args(**kwargs):
    defaults = {'command': 'schedule', 'task': None, 'all': False, 'list': False, 'validate': None, 'check_deps': False, 'password': None}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_handle_schedule_list(capsys, monkeypatch):
    ts = DummyTaskService()
    ss = DummySchedulingService()
    monkeypatch.setattr(cli, 'get_task_service', lambda: ts)
    monkeypatch.setattr(cli, 'get_scheduling_service', lambda: ss)
    code = cli.handle_schedule_command(make_args(list=True), DummyScheduler())
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out[0]['TaskName'] == 'foo'


def test_handle_schedule_single(monkeypatch, capsys):
    ts = DummyTaskService()
    ss = DummySchedulingService()
    monkeypatch.setattr(cli, 'get_task_service', lambda: ts)
    monkeypatch.setattr(cli, 'get_scheduling_service', lambda: ss)
    code = cli.handle_schedule_command(make_args(task='foo'), DummyScheduler())
    assert code == 0
    assert ss.scheduled == ['foo']
    assert 'Scheduled' in capsys.readouterr().out


def test_cli_main_dispatch(monkeypatch):
    monkeypatch.setattr(cli, 'create_parser', lambda: mock.Mock(parse_args=lambda: make_args(command='dashboard')))
    with mock.patch.object(cli, 'handle_dashboard_command', return_value=0) as m:
        with pytest.raises(SystemExit) as exc:
            cli.cli_main()
        assert exc.value.code == 0
        m.assert_called_once()
