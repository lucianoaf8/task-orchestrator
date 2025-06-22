from unittest.mock import MagicMock
from orchestrator.utils.windows_scheduler import WindowsScheduler


def test_change_task(monkeypatch):
    ws = WindowsScheduler()
    runner = MagicMock(return_value=True)
    monkeypatch.setattr(ws, '_run', runner)
    ws.change_task('task', schedule_trigger={'SC': 'MINUTE', 'MO': '1'}, new_command='cmd')
    assert runner.call_count == 2
    args1 = runner.call_args_list[0][0][0]
    assert '/RI' in args1 and '/ST' in args1
    args2 = runner.call_args_list[1][0][0]
    assert '/TR' in args2 and 'cmd' in args2


def test_change_task_invalid(monkeypatch):
    ws = WindowsScheduler()
    runner = MagicMock(return_value=True)
    monkeypatch.setattr(ws, '_run', runner)
    ws.change_task('task', schedule_trigger={'SC': 'DAILY'})
    assert runner.call_count == 0


def test_get_task_info(monkeypatch):
    ws = WindowsScheduler()
    output = 'HostName: PC\nTaskName: \\Orchestrator\\Orc_task\nStatus: Ready\n'
    monkeypatch.setattr(ws, '_run', lambda cmd, capture_output=True: (True, output))
    info = ws.get_task_info('task')
    assert info['TaskName'].endswith('task')
    assert info['Status'] == 'Ready'
