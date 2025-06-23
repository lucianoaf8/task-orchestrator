import json
import runpy
from types import SimpleNamespace
from datetime import datetime, timedelta
from unittest import mock
import subprocess
import sys

import pytest

import orchestrator.cli as cli
from orchestrator.core.task_result import TaskResult
from orchestrator.core.scheduler import TaskScheduler
from orchestrator.services.scheduling_service import SchedulingService, SchedulingError
from orchestrator.services.task_service import TaskService
from orchestrator.utils.windows_scheduler import WindowsScheduler
from orchestrator.utils.cron_converter import CronConverter
import orchestrator.utils.configure as configure
from orchestrator.core.exceptions import ValidationError


# ---- CLI additional tests ----

class FailScheduler:
    def __init__(self):
        self.executed = []
    def check_dependencies(self, name):
        return True, 'OK'
    def execute_task(self, name):
        self.executed.append(name)
        return TaskResult(task_name=name, status='FAILED')


def make_args(**kw):
    base = dict(command='execute', task='t', check_deps=False,
                password=None, all=False, list=False, validate=None,
                from_legacy=False, cleanup=False)
    base.update(kw)
    return SimpleNamespace(**base)


def test_handle_execute_command_failure(capsys):
    sched = FailScheduler()
    code = cli.handle_execute_command(make_args(), sched)
    out = json.loads(capsys.readouterr().out)
    assert code == 1 and out['task_name'] == 't'

def test_handle_schedule_task_exception(monkeypatch, capsys):
    class Svc:
        def schedule_task(self, *a, **k):
            raise Exception('boom')
    monkeypatch.setattr(cli, 'get_task_service', lambda: SimpleNamespace(get_task=lambda n: {'command':'c','schedule':'*'}))
    monkeypatch.setattr(cli, 'get_scheduling_service', lambda: Svc())
    code = cli.handle_schedule_command(make_args(command='schedule', task='t'), FailScheduler())
    assert code == 1
    assert 'Failed' in capsys.readouterr().out


def test_cli_main_other_commands(monkeypatch):
    args_list = [make_args(command='unschedule'),
                 make_args(command='configure'),
                 make_args(command='migrate', from_legacy=True)]
    calls = []
    monkeypatch.setattr(cli.getpass, 'getpass', lambda p: '')
    monkeypatch.setattr(cli, 'handle_unschedule_command', lambda a,b: calls.append('uns') or 0)
    monkeypatch.setattr(cli, 'handle_configure_command', lambda a: calls.append('cfg') or 0)
    monkeypatch.setattr(cli, 'handle_migrate_command', lambda a: calls.append('mig') or 0)
    for a in args_list:
        monkeypatch.setattr(cli, 'create_parser', lambda a=a: mock.Mock(parse_args=lambda: a))
        with pytest.raises(SystemExit) as exc:
            cli.cli_main()
        assert exc.value.code == 0
    assert calls == ['uns', 'cfg', 'mig']

# ---- ConfigManager credential paths ----
from orchestrator.core.config_manager import ConfigManager
import sqlite3

def test_store_credential_plain(tmp_path):
    cm = ConfigManager(db_path=str(tmp_path/'db.sqlite'))
    cm.store_credential('name','secret')
    assert cm.get_credential('name') == 'secret'


def test_init_db_other_error(monkeypatch, tmp_path):
    cm = ConfigManager(db_path=str(tmp_path/'db.sqlite'))
    class BadConn:
        def execute(self, *a, **k):
            raise sqlite3.DatabaseError('other')
    monkeypatch.setattr(cm, 'db', BadConn())
    with pytest.raises(sqlite3.DatabaseError):
        cm._init_db()

# ---- TaskScheduler validate_task_config ----

def test_validate_task_config_missing(tmp_path):
    sched = TaskScheduler()
    sched.config_manager = sched.config_manager.__class__(db_path=str(tmp_path/'d.sqlite'))
    sched.config_manager.add_task('a','type','',schedule=None)
    ok,msg = sched.validate_task_config('a')
    assert ok is False and 'Missing command' in msg

# ---- TaskResult duration ----
from orchestrator.core.task_result import TaskResult

def test_duration_none():
    tr = TaskResult(task_name='t', status='S')
    assert tr.duration is None

# ---- SchedulingService unschedule error ----

def test_unschedule_task_error():
    class WS:
        def delete_task(self,name):
            return False
    svc = SchedulingService(WS())
    with pytest.raises(SchedulingError):
        svc.unschedule_task('x')

# ---- TaskService update_task schedule ----

def test_task_service_update_schedule(tmp_path):
    svc = TaskService(config_manager=ConfigManager(db_path=str(tmp_path/'db.sqlite')),
                      scheduling_service=SchedulingService(scheduler=None))
    svc._cfg.add_task('a','t','c','0 0 * * *')
    svc._cfg.add_task = lambda **kw: None
    svc._sched.change_task = lambda *a, **k: True
    svc._sched.unschedule_task = lambda *a, **k: True
    res = svc.update_task('a', {'schedule':'1 0 * * *'})
    assert res['task']['schedule'] == '1 0 * * *'

    # missing task
    with pytest.raises(ValidationError):
        svc.update_task('missing', {})

# ---- Configure module __main__ ----

def test_configure_main_block(monkeypatch):
    monkeypatch.setattr(configure.getpass, 'getpass', lambda p: (_ for _ in ()).throw(KeyboardInterrupt()))
    monkeypatch.setattr(sys, 'argv', ['prog'])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module('orchestrator.utils.configure', run_name='__main__')
    assert exc.value.code == 130

# ---- CronConverter validate_cron_expression ----

def test_validate_cron_variants():
    assert CronConverter.validate_cron_expression('8:00')[0]
    assert CronConverter.validate_cron_expression('SUN 08:00')[0]
    assert CronConverter.validate_cron_expression('15 09:30')[0]
    bad = CronConverter.validate_cron_expression('invalid cron')
    assert bad[0] is False

# ---- WindowsScheduler helpers ----

def test_get_task_status_paths(monkeypatch):
    ws = WindowsScheduler()
    monkeypatch.setattr(ws, '_run', lambda cmd, capture_output=True: (True, '[{"TaskName":"x"}]'))
    status = ws.get_task_status('x')
    assert status['TaskName'] == 'x'
    monkeypatch.setattr(ws, '_run', lambda cmd, capture_output=True: (True, 'notjson'))
    assert ws.get_task_status('x') is None
    monkeypatch.setattr(ws, '_run', lambda cmd, capture_output=True: (False, ''))
    assert ws.get_task_status('x') is None


def test_run_timeout(monkeypatch):
    ws = WindowsScheduler()
    monkeypatch.delenv('ORC_SIMULATE_SCHEDULER', raising=False)
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd='x', timeout=1)
    monkeypatch.setattr(subprocess, 'run', boom)
    assert ws._run(['schtasks']) is False

# ---- Routes add_or_update_task invalid cron ----
from orchestrator.web.api import routes
from flask import Flask

@pytest.fixture()
def app():
    app = webapp.create_app()
    app.testing = True
    return app

def test_route_add_invalid_cron(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(routes.api_bp)
    monkeypatch.setattr(routes.CM, 'add_task', lambda **kw: None)
    with app.test_request_context('/api/tasks', method='POST', json={'name':'t','type':'shell','command':'c','schedule':'bad'}):
        resp = routes.add_or_update_task()
        assert resp[1] == 400

# ---- App delete_task not found ----
import orchestrator.web.app as webapp

def test_delete_task_not_found(app):
    webapp.config_manager = mock.Mock()
    webapp.config_manager.get_task.return_value = None
    with app.test_request_context('/api/tasks/missing', method='DELETE'):
        resp = webapp.delete_task('missing')
        if isinstance(resp, tuple):
            resp, status = resp
            resp.status_code = status
        assert resp.status_code == 404


# ---- Script __main__ execution ----

def test_scripts_main_blocks(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr('time.sleep', lambda x: None)
    import scripts.test_task as tt
    sys.modules.pop('scripts.test_task', None)
    monkeypatch.setattr(sys, 'argv', [tt.__file__])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(tt.__file__, run_name='__main__')
    assert exc.value.code == 0

    import scripts.write_marker as wm
    sys.modules.pop('scripts.write_marker', None)
    monkeypatch.setattr(sys, 'argv', [wm.__file__, '--out', str(tmp_path/'o.txt')])
    with pytest.raises(SystemExit) as exc2:
        runpy.run_path(wm.__file__, run_name='__main__')
    assert exc2.value.code == 0
