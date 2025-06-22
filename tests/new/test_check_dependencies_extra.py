from types import SimpleNamespace
from unittest import mock
import builtins

import scripts.checks.check_dependencies as chk

class DummyCM:
    def __init__(self, deps):
        self.task={'dependencies':deps}
    def get_task(self,name):
        return self.task


def test_check_command_not_found(monkeypatch):
    monkeypatch.setattr('subprocess.run', lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    ok, reason = chk._check_command('none')
    assert not ok and 'not found' in reason


def test_check_url(monkeypatch):
    resp = mock.Mock(ok=True, status_code=200)
    monkeypatch.setattr(chk.requests, 'get', lambda *a, **k: resp)
    ok, reason = chk._check_url('http://a')
    assert ok and 'HTTP 200' in reason


def test_main_complete(monkeypatch):
    monkeypatch.setattr(chk, 'ConfigManager', lambda: DummyCM(['file:/tmp']))
    monkeypatch.setattr(chk.os.path, 'exists', lambda p: True)
    assert chk.main(['t']) == 0
