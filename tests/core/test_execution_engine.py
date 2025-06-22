from unittest import mock
import subprocess

from orchestrator.core.execution_engine import ExecutionEngine, _parse_dependencies
from orchestrator.core.task_result import TaskResult


def test_parse_dependencies():
    assert _parse_dependencies('["a","b"]') == ['a', 'b']
    assert _parse_dependencies([]) == []


def test_execute_once_success(monkeypatch):
    ee = ExecutionEngine()
    completed = subprocess.CompletedProcess('cmd', 0, 'out', 'err')
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: completed)
    result = ee._execute_once('t', 'cmd', 10, 0)
    assert result.status == 'SUCCESS' and result.output == 'out'


def test_execute_once_timeout(monkeypatch):
    ee = ExecutionEngine()
    def raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd='cmd', timeout=1)
    monkeypatch.setattr(subprocess, 'run', raise_timeout)
    result = ee._execute_once('t', 'cmd', 1, 0)
    assert result.status == 'FAILED' and 'Timeout' in result.error
