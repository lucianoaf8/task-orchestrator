from types import SimpleNamespace
from unittest import mock
import pytest

from orchestrator.core.execution_engine import ExecutionEngine, ValidationError
from orchestrator.core.task_result import TaskResult

class DummyCM:
    def __init__(self, task):
        self.task = task
        self.db = mock.MagicMock()
        self.db.execute.return_value.fetchone.return_value = ('SUCCESS',)
    def get_task(self, name):
        return self.task
    def save_task_result(self, result):
        self.saved = result
    def get_all_tasks(self):
        return {}
    def get_task_history(self, name, limit):
        return []


def make_engine(task):
    ee = ExecutionEngine()
    ee._cfg = DummyCM(task)
    return ee


def test_execute_task_not_found():
    ee = make_engine(None)
    with pytest.raises(ValidationError):
        ee.execute_task('x')


def test_execute_task_no_command():
    ee = make_engine({'name':'x'})
    with pytest.raises(ValidationError):
        ee.execute_task('x')


def test_execute_task_dependency_fail(monkeypatch):
    task = {'name':'x','command':'echo','dependencies':['file:/nope']}
    ee = make_engine(task)
    monkeypatch.setattr('pathlib.Path.exists', lambda self: False)
    result = ee.execute_task('x')
    assert result.status == 'SKIPPED'


def test_check_dependencies_branches(monkeypatch):
    task = {'dependencies':['task:other','file:/tmp','url:http://a','cmd:echo 1','bad']}
    ee = make_engine(task)
    monkeypatch.setattr(ee, '_task_success_last_run', lambda name: name=='other')
    monkeypatch.setattr('pathlib.Path.exists', lambda p: True)
    head = mock.MagicMock(status_code=200)
    monkeypatch.setattr('requests.head', lambda *a, **k: head)
    monkeypatch.setattr('subprocess.run', lambda *a, **k: SimpleNamespace(returncode=0))
    ok,msg = ee._check_dependencies(task)
    assert ok and msg=='OK'

