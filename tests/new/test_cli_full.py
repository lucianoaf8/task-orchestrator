import sys
import pytest
from types import SimpleNamespace
from unittest import mock

import orchestrator.cli as cli

class DummyScheduler:
    def __init__(self):
        self.checked = []
    def check_dependencies(self, name):
        self.checked.append(name)
        return True, 'OK'
    def execute_task(self, name):
        from orchestrator.core.task_result import TaskResult
        return TaskResult(task_name=name, status='SUCCESS')

class DummyServices:
    def __init__(self):
        self.scheduled = []
        self.unscheduled = []
    def schedule_task(self, name, cmd, cron):
        self.scheduled.append(name)
        return True
    def unschedule_task(self, name):
        self.unscheduled.append(name)
        return True
    def list_tasks(self):
        return [{'TaskName': 'foo', 'Status': 'Ready'}]

class DummyTaskService:
    def __init__(self):
        self.tasks = {'foo': {'command': 'cmd', 'schedule': '0 0 * * *'}}
    def list_tasks(self):
        return self.tasks
    def get_task(self, name):
        return self.tasks.get(name)

def make_args(**kw):
    base = dict(command='schedule', task=None, all=False, list=False, validate=None,
                 check_deps=False, password=None, from_legacy=False, cleanup=False)
    base.update(kw)
    return SimpleNamespace(**base)

def test_unschedule_command(monkeypatch, capsys):
    svc = DummyServices()
    monkeypatch.setattr(cli, 'get_scheduling_service', lambda: svc)
    code = cli.handle_unschedule_command(make_args(task='foo'), DummyScheduler())
    assert code == 0
    assert svc.unscheduled == ['foo']
    assert 'Unscheduled' in capsys.readouterr().out

def test_execute_command_check(monkeypatch, capsys):
    sch = DummyScheduler()
    code = cli.handle_execute_command(make_args(task='foo', check_deps=True), sch)
    assert code == 0 and sch.checked == ['foo']
    assert 'OK' in capsys.readouterr().out

def test_dashboard_and_configure(monkeypatch):
    dash = mock.Mock(); cfg = mock.Mock()
    monkeypatch.setattr(cli, 'dashboard_main', dash)
    monkeypatch.setattr(cli, 'configure_main', cfg)
    assert cli.handle_dashboard_command(None) == 0
    dash.assert_called_once()
    assert cli.handle_configure_command(None) == 0
    cfg.assert_called_once()

def test_migrate_command(monkeypatch, capsys):
    migrate = mock.Mock(); cleanup = mock.Mock()
    monkeypatch.setitem(sys.modules, 'tools.migration', SimpleNamespace(
        migrate_from_legacy=migrate, cleanup_legacy=cleanup))
    code = cli.handle_migrate_command(make_args(from_legacy=True, cleanup=True))
    assert code == 0
    migrate.assert_called_once(); cleanup.assert_called_once()
    code2 = cli.handle_migrate_command(make_args())
    assert code2 == 1
    assert 'No migrate action' in capsys.readouterr().err

def test_serve(monkeypatch):
    app = mock.Mock()
    monkeypatch.setenv('ORC_HOST', 'h')
    monkeypatch.setenv('ORC_PORT', '123')
    monkeypatch.setenv('ORC_DEBUG', 'true')
    monkeypatch.setattr('orchestrator.web.app.create_app', lambda: app)
    cli.serve()
    app.run.assert_called_once_with(host='h', port=123, debug=True)

def test_cli_main_dispatch(monkeypatch):
    args = make_args(command='execute', task='foo')
    monkeypatch.setattr(cli, 'create_parser', lambda: mock.Mock(parse_args=lambda: args))
    monkeypatch.setattr(cli, 'handle_execute_command', lambda a, b: 0)
    monkeypatch.setattr(cli.getpass, 'getpass', lambda prompt: '')
    with mock.patch.object(cli, 'TaskScheduler') as ts:
        with pytest.raises(SystemExit) as exc:
            cli.cli_main()
        assert exc.value.code == 0
        ts.assert_called_once()

def test_cli_main_no_command(monkeypatch):
    parser = mock.Mock()
    parser.parse_args.return_value = make_args(command=None)
    monkeypatch.setattr(cli, 'create_parser', lambda: parser)
    with pytest.raises(SystemExit) as exc:
        cli.cli_main()
    assert exc.value.code == 1
