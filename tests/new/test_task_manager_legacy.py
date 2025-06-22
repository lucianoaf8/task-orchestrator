import importlib
import sys
import types
from types import SimpleNamespace
from dataclasses import dataclass


def _import_task_manager(monkeypatch, tasks):
    cm_mod = types.ModuleType('orchestrator.core.config_manager')
    class DummyCM:
        def __init__(self, master_password=None):
            self.tasks = tasks
        def get_task(self, name):
            return self.tasks.get(name)
    cm_mod.ConfigManager = DummyCM

    tr_mod = types.ModuleType('orchestrator.core.task_result')
    @dataclass
    class TaskResult:
        task_name: str
        status: str
        start_time: object = None
        end_time: object = None
        exit_code: int | None = None
        output: str = ''
        error: str = ''
        retry_count: int = 0
    tr_mod.TaskResult = TaskResult

    core_pkg = types.ModuleType('orchestrator.core')
    core_pkg.__path__ = []
    core_pkg.config_manager = cm_mod
    core_pkg.task_result = tr_mod

    monkeypatch.setitem(sys.modules, 'orchestrator.core', core_pkg)
    monkeypatch.setitem(sys.modules, 'orchestrator.core.config_manager', cm_mod)
    monkeypatch.setitem(sys.modules, 'orchestrator.core.task_result', tr_mod)

    sys.modules.pop('orchestrator.legacy.task_manager', None)
    return importlib.import_module('orchestrator.legacy.task_manager')


def test_task_not_found(monkeypatch):
    mod = _import_task_manager(monkeypatch, {})
    tm = mod.TaskManager()
    res = tm.run_task_with_retry('x')
    assert res.status == 'FAILED' and 'Task not found' in res.error


def test_task_no_command(monkeypatch):
    mod = _import_task_manager(monkeypatch, {'a': {'command': ''}})
    tm = mod.TaskManager()
    res = tm.run_task_with_retry('a')
    assert res.status == 'FAILED' and 'No command' in res.error


def test_task_success(monkeypatch):
    mod = _import_task_manager(monkeypatch, {'a': {'command': 'cmd'}})
    tm = mod.TaskManager()
    comp = SimpleNamespace(returncode=0, stdout='out', stderr='')
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: comp)
    res = tm.run_task_with_retry('a')
    assert res.status == 'SUCCESS' and res.output == 'out'


def test_task_failed_exit(monkeypatch):
    mod = _import_task_manager(monkeypatch, {'a': {'command': 'cmd'}})
    tm = mod.TaskManager()
    comp = SimpleNamespace(returncode=1, stdout='', stderr='err')
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: comp)
    res = tm.run_task_with_retry('a')
    assert res.status == 'FAILED' and res.exit_code == 1


def test_task_exception(monkeypatch):
    mod = _import_task_manager(monkeypatch, {'a': {'command': 'cmd'}})
    tm = mod.TaskManager()
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('boom')))
    res = tm.run_task_with_retry('a')
    assert res.status == 'FAILED' and 'boom' in res.error


def test_check_dependencies(monkeypatch):
    mod = _import_task_manager(monkeypatch, {})
    tm = mod.TaskManager()
    ok, msg = tm.check_dependencies('a')
    assert ok and msg == 'OK'

