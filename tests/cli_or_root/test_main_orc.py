from types import SimpleNamespace
from unittest import mock

import main as mainmod
import orc as orcmod


def test_trigger_orc_scheduling(monkeypatch):
    cp = SimpleNamespace(returncode=0, stdout="", stderr="")
    recorded = {}
    def fake_run(cmd, **kw):
        recorded['cmd'] = cmd
        return cp
    monkeypatch.setattr(mainmod.subprocess, 'run', fake_run)
    ok = mainmod.trigger_orc_scheduling('foo')
    assert ok is True
    assert 'orc.py' in ' '.join(recorded['cmd'])

    cp.returncode = 1
    assert mainmod.trigger_orc_scheduling('foo') is False


def test_main_dispatch(monkeypatch):
    calls = []
    monkeypatch.setattr(mainmod, 'show_dashboard', lambda: calls.append('dash'))
    monkeypatch.setattr(mainmod, 'show_status', lambda: calls.append('status'))
    monkeypatch.setattr(mainmod, 'interactive_mode', lambda: calls.append('interactive'))
    def fake_cli():
        calls.append('cli')
    monkeypatch.setattr('orchestrator.cli.cli_main', fake_cli)

    monkeypatch.setattr(mainmod.sys, 'argv', ['main.py', 'status'])
    mainmod.main()
    assert calls == ['status']

    calls.clear()
    monkeypatch.setattr(mainmod.sys, 'argv', ['main.py'])
    mainmod.main()
    assert calls == ['interactive']


def test_orc_schedule_task_operation(monkeypatch):
    dummy = SimpleNamespace(
        config_manager=SimpleNamespace(get_task=lambda n: {'name': n, 'command': 'c', 'schedule': '* * * * *'}),
        validate_task_config=lambda n: (True, 'ok'),
        schedule_task=lambda n: True,
    )
    monkeypatch.setattr(orcmod, 'TaskScheduler', lambda: dummy)
    logger = mock.Mock()
    assert orcmod.schedule_task_operation('foo', logger) is True

    dummy.config_manager.get_task = lambda n: None
    assert orcmod.schedule_task_operation('foo', logger) is False


def test_orc_update_no_args(monkeypatch):
    logger = mock.Mock()
    assert orcmod.update_task_operation('foo', None, None, logger) is False
