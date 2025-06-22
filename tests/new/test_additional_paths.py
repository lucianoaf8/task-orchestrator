import json
import types
from types import SimpleNamespace
import pytest
import subprocess
from unittest import mock

import orchestrator.cli as cli
from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.execution_engine import ExecutionEngine
from orchestrator.core.scheduler import TaskScheduler
from orchestrator.core.task_result import TaskResult
from orchestrator.utils import cron_converter
from orchestrator.utils.windows_scheduler import WindowsScheduler
from orchestrator.web.api import routes
import orchestrator.web.app as webapp

# ---------------------------------------------------------------------------
# CLI entry and password prompting
# ---------------------------------------------------------------------------

def test_cli_main_interactive_password(monkeypatch):
    args = SimpleNamespace(command='schedule', task='t', all=False, list=False,
                           validate=None, check_deps=False, password=None)
    parser = SimpleNamespace(parse_args=lambda: args, print_help=lambda *_: None)
    monkeypatch.setattr(cli, 'create_parser', lambda: parser)
    monkeypatch.setattr(cli.getpass, 'getpass', lambda prompt: 'pw')
    called = {}
    class DummyTS(TaskScheduler):
        def __init__(self, master_password=None):
            called['pw'] = master_password
    monkeypatch.setattr(cli, 'TaskScheduler', DummyTS)
    monkeypatch.setattr(cli, 'handle_schedule_command', lambda a, s: 0)
    with pytest.raises(SystemExit) as exc:
        cli.cli_main()
    assert exc.value.code == 0
    assert called['pw'] == 'pw'


def test_main_calls_cli_main(monkeypatch):
    called = {}
    monkeypatch.setattr(cli, 'cli_main', lambda: called.setdefault('x', True))
    cli.main()
    assert called['x'] is True

# ---------------------------------------------------------------------------
# ConfigManager helpers
# ---------------------------------------------------------------------------

def test_save_task_result_and_close(tmp_path):
    cm = ConfigManager(db_path=str(tmp_path/'db.sqlite'))
    cm.add_task('t','shell','cmd')
    result = TaskResult(task_name='t', status='SUCCESS')
    cm.save_task_result(result)
    count = cm.db.execute('SELECT COUNT(*) FROM task_results').fetchone()[0]
    dummy = types.SimpleNamespace(close=mock.Mock(side_effect=RuntimeError("x")))
    cm.db = dummy
    cm.close()  # should not raise
    assert dummy.close.called

def test_context_manager_enter_exit(tmp_path, monkeypatch):
    cm = ConfigManager(db_path=str(tmp_path/'db.sqlite'))
    flag = {}
    monkeypatch.setattr(cm, 'close', lambda: flag.setdefault('closed', True))
    with cm as cm2:
        assert cm2 is cm
    assert flag['closed'] is True

# ---------------------------------------------------------------------------
# ExecutionEngine helper
# ---------------------------------------------------------------------------

def test_task_success_last_run(tmp_path):
    cm = ConfigManager(db_path=str(tmp_path/'db.sqlite'))
    cm.add_task('a','t','cmd')
    cm.db.execute("INSERT INTO task_results (task_name, status) VALUES ('a','SUCCESS')")
    cm.db.commit()
    ee = ExecutionEngine()
    ee._cfg = cm
    assert ee._task_success_last_run('a') is True
    assert ee._task_success_last_run('b') is False

# ---------------------------------------------------------------------------
# Scheduler edge cases
# ---------------------------------------------------------------------------

def test_schedule_task_missing(tmp_path):
    ts = TaskScheduler()
    ts.config_manager = ts.config_manager.__class__(db_path=str(tmp_path/'db.sqlite'))
    ts.windows_scheduler = mock.Mock(create_task=lambda *a, **k: True)
    assert ts.schedule_task('none') is False
    ts.config_manager.add_task('a','t','c')
    assert ts.schedule_task('a') is False


def test_check_and_validate(tmp_path):
    ts = TaskScheduler()
    ts.config_manager = ts.config_manager.__class__(db_path=str(tmp_path/'db.sqlite'))
    ts.execution_engine = mock.Mock(_check_dependencies=lambda cfg: (True,'OK'))
    ts.config_manager.add_task('a','t','c')
    ok,_ = ts.check_dependencies('a')
    assert ok
    assert ts.validate_task_config('a')[0] is True
    assert ts.validate_task_config('missing')[0] is False

# ---------------------------------------------------------------------------
# Cron validation edge cases
# ---------------------------------------------------------------------------

def test_validate_cron_invalid():
    ok, msg = cron_converter.CronConverter.validate_cron_expression('61 0 * * *')
    assert not ok and msg

# ---------------------------------------------------------------------------
# WindowsScheduler edge paths
# ---------------------------------------------------------------------------

def test_run_timeout(monkeypatch):
    ws = WindowsScheduler()
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd='x', timeout=1)
    monkeypatch.setattr(subprocess, 'run', boom)
    assert ws._run(['schtasks']) is False


def test_get_task_info_none(monkeypatch):
    ws = WindowsScheduler()
    monkeypatch.setattr(ws, '_run', lambda *a, **k: (False, ''))
    assert ws.get_task_info('t') is None

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def test_call_orc_py_and_list(monkeypatch):
    cm = types.SimpleNamespace(get_task=lambda n: {'command':'c','schedule':'*'} if n=='a' else None,
                               get_all_tasks=lambda: {})
    sched = types.SimpleNamespace(schedule_task=lambda n,c,s: True,
                                  unschedule_task=lambda n: True,
                                  list_tasks=lambda: {'x':'y'})
    monkeypatch.setattr(routes, 'CM', cm)
    monkeypatch.setattr(routes, 'SCHEDULER', sched)
    ok,msg = routes.call_orc_py('schedule','a')
    assert ok and msg=='scheduled'
    ok,msg = routes.call_orc_py('unschedule','a')
    assert ok and msg=='unscheduled'
    ok,msg = routes.call_orc_py('list')
    assert ok and json.loads(msg)=={'x':'y'}
    ok,msg = routes.call_orc_py('schedule','missing')
    assert not ok and msg=='Task not found'
    ok,msg = routes.call_orc_py('bad')
    assert not ok and 'Invalid' in msg


def test_list_scheduled_parsing(monkeypatch, app):
    monkeypatch.setattr(routes, 'call_orc_py', lambda op: (True, '[{"TaskName":"T"}]'))
    with app.test_request_context('/'):
        resp, status = routes.list_scheduled()
    assert status==200 and resp.get_json()['scheduled_tasks'][0]['TaskName']=='T'

    def as_text(_op):
        return True, 'Foo: Ready\n- ignored'
    monkeypatch.setattr(routes, 'call_orc_py', as_text)
    with app.test_request_context('/'):
        resp, status = routes.list_scheduled()
    assert resp.get_json()['scheduled_tasks'][0]['TaskName']=='Foo'

    monkeypatch.setattr(routes, 'call_orc_py', lambda op: (False, 'err'))
    with app.test_request_context('/'):
        resp, status = routes.list_scheduled()
    assert status==500

# ---------------------------------------------------------------------------
# Web app error branches
# ---------------------------------------------------------------------------

def test_get_tasks_and_history_errors(app, monkeypatch):
    monkeypatch.setattr(webapp.config_manager, 'get_all_tasks', mock.Mock(side_effect=RuntimeError('x')))
    with app.test_request_context('/api/tasks'):
        resp, status = webapp.get_tasks()
        assert status == 500
    monkeypatch.setattr(webapp.config_manager, 'get_task_history', mock.Mock(side_effect=RuntimeError('x')))
    with app.test_request_context('/api/tasks/a/history'):
        resp, status = webapp.get_task_history('a')
        assert status == 500

@pytest.fixture()
def app():
    app = webapp.create_app()
    app.testing = True
    return app
