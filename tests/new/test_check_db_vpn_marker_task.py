import importlib
import sys
import types
from types import SimpleNamespace

import pytest


def _import_check_db(monkeypatch, engine):
    sa = types.ModuleType('sqlalchemy')
    sa.create_engine = lambda *a, **k: engine
    sa_engine = types.ModuleType('sqlalchemy.engine')
    sa_engine.Engine = type('Engine', (), {})
    sa.engine = sa_engine
    monkeypatch.setitem(sys.modules, 'sqlalchemy.engine', sa_engine)
    monkeypatch.setitem(sys.modules, 'sqlalchemy', sa)

    cm_mod = types.ModuleType('orchestrator.core.config_manager')
    class DummyCM:
        def __init__(self, master_password=None):
            pass
        def get_credential(self, name):
            return None
        def get_config(self, section, key, default=None):
            return None
    cm_mod.ConfigManager = DummyCM
    monkeypatch.setitem(sys.modules, 'orchestrator.core.config_manager', cm_mod)

    sys.modules.pop('scripts.checks.check_db_connection', None)
    return importlib.import_module('scripts.checks.check_db_connection')


class DummyEngine:
    def __init__(self, ok=True):
        self.ok = ok
    def connect(self):
        if not self.ok:
            raise Exception('fail')
        class Ctx:
            def __enter__(self_inner):
                return self_inner
            def __exit__(self_inner, exc_type, exc, tb):
                pass
        return Ctx()


def test_check_db_connection(monkeypatch):
    engine = DummyEngine()
    mod = _import_check_db(monkeypatch, engine)
    assert mod.check_db_connection(engine) is True
    bad = DummyEngine(ok=False)
    assert mod.check_db_connection(bad) is False


def test_get_db_engine_direct_success(monkeypatch):
    engine = DummyEngine()
    mod = _import_check_db(monkeypatch, engine)
    monkeypatch.setattr(mod, 'check_db_connection', lambda e: True)
    monkeypatch.setattr(mod, 'create_engine', lambda dsn, **k: engine)
    monkeypatch.setenv('DB_SERVER', 'srv')
    monkeypatch.setenv('DB_PORT', '3306')
    monkeypatch.setenv('DB_NAME', 'db')
    monkeypatch.setenv('DB_USER', 'u')
    monkeypatch.setenv('DB_PASSWORD', 'p')
    eng = mod.get_db_engine('s')
    assert eng is engine


def test_get_db_engine_vpn_retry(monkeypatch):
    engine = DummyEngine()
    mod = _import_check_db(monkeypatch, engine)
    calls = {'cnt':0}
    def fake_check(e):
        calls['cnt'] += 1
        return calls['cnt'] == 2
    monkeypatch.setattr(mod, 'check_db_connection', fake_check)
    monkeypatch.setattr(mod, 'create_engine', lambda dsn, **k: engine)
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: None)
    monkeypatch.setenv('DB_SERVER', 'srv')
    monkeypatch.setenv('DB_PORT', '1')
    monkeypatch.setenv('DB_NAME', 'db')
    monkeypatch.setenv('DB_USER', 'u')
    monkeypatch.setenv('DB_PASSWORD', 'p')
    eng = mod.get_db_engine('s')
    assert eng is engine and calls['cnt'] == 2


def test_get_db_engine_fail(monkeypatch):
    engine = DummyEngine()
    mod = _import_check_db(monkeypatch, engine)
    monkeypatch.setattr(mod, 'check_db_connection', lambda e: False)
    monkeypatch.setattr(mod, 'create_engine', lambda dsn, **k: engine)
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setattr(mod, 'send_error_log', lambda *a, **k: calls.append(a))
    monkeypatch.setenv('DB_SERVER', 'srv')
    monkeypatch.setenv('DB_PORT', '3306')
    monkeypatch.setenv('DB_NAME', 'db')
    monkeypatch.setenv('DB_USER', 'u')
    monkeypatch.setenv('DB_PASSWORD', 'p')
    calls = []
    with pytest.raises(ConnectionError):
        mod.get_db_engine('s')
    assert calls


def test_get_db_engine_bad_params(monkeypatch):
    engine = DummyEngine()
    mod = _import_check_db(monkeypatch, engine)
    monkeypatch.setattr(mod, 'send_error_log', lambda *a, **k: calls.append(a))
    calls = []
    with pytest.raises(ValueError):
        mod.get_db_engine('s')
    assert calls


def _import_check_vpn(monkeypatch):
    dns_mod = types.ModuleType('dns')
    resolver_mod = types.ModuleType('dns.resolver')
    exception_mod = types.ModuleType('dns.exception')
    class DNSException(Exception):
        pass
    resolver_mod.resolve = lambda *a, **k: None
    exception_mod.DNSException = DNSException
    dns_mod.resolver = resolver_mod
    dns_mod.exception = exception_mod
    monkeypatch.setitem(sys.modules, 'dns', dns_mod)
    monkeypatch.setitem(sys.modules, 'dns.resolver', resolver_mod)
    monkeypatch.setitem(sys.modules, 'dns.exception', exception_mod)

    sys.modules.pop('scripts.checks.check_vpn', None)
    mod = importlib.import_module('scripts.checks.check_vpn')
    return mod, DNSException


def test_vpn_interface(monkeypatch):
    mod, _ = _import_check_vpn(monkeypatch)
    monkeypatch.setattr(mod.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout='tun'))
    assert mod.check_vpn_connection() is True


def test_vpn_internal_ip(monkeypatch):
    mod, _ = _import_check_vpn(monkeypatch)
    monkeypatch.setattr(mod.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=''))
    class Sock:
        def close(self):
            pass
    monkeypatch.setattr(mod.socket, 'create_connection', lambda *a, **k: Sock())
    assert mod.check_vpn_connection() is True


def test_vpn_dns(monkeypatch):
    mod, _ = _import_check_vpn(monkeypatch)
    monkeypatch.setattr(mod.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=''))
    monkeypatch.setattr(mod.socket, 'create_connection', lambda *a, **k: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(mod.dns.resolver, 'resolve', lambda *a, **k: True)
    assert mod.check_vpn_connection() is True


def test_vpn_not_detected(monkeypatch):
    mod, DNSEx = _import_check_vpn(monkeypatch)
    monkeypatch.setattr(mod.platform, 'system', lambda: 'Linux')
    monkeypatch.setattr(mod.subprocess, 'run', lambda *a, **k: SimpleNamespace(stdout=''))
    monkeypatch.setattr(mod.socket, 'create_connection', lambda *a, **k: (_ for _ in ()).throw(OSError()))
    def raise_dns(*a, **k):
        raise DNSEx()
    monkeypatch.setattr(mod.dns.resolver, 'resolve', raise_dns)
    assert mod.check_vpn_connection() is False


def test_vpn_exception(monkeypatch):
    mod, _ = _import_check_vpn(monkeypatch)
    monkeypatch.setattr(mod.platform, 'system', lambda: (_ for _ in ()).throw(RuntimeError('boom')))
    assert mod.check_vpn_connection() is False

def test_write_marker(tmp_path):
    from scripts import write_marker as wm
    args = wm._parse_args(['--out', str(tmp_path/'m.txt'), '--marker', 'X'])
    assert args.out.endswith('m.txt') and args.marker == 'X'
    assert wm.main(['--out', str(tmp_path/'m.txt'), '--marker', 'Y']) == 0
    content = (tmp_path/'m.txt').read_text()
    assert 'SUCCESS at' in content and content.strip().endswith('Y')


def test_test_task_main(tmp_path, monkeypatch):
    from scripts import test_task
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(test_task.time, 'sleep', lambda x: None)
    res = test_task.main()
    assert res == 0
    assert not (tmp_path/'test_output.txt').exists()
