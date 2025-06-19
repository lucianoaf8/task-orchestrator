import argparse
from orchestrator.cli import create_parser, handle_schedule_command
from orchestrator.utils.configure import configure
from orchestrator.core.config_manager import ConfigManager


def test_cli_schedule(monkeypatch):
    parser = create_parser()
    args = parser.parse_args(["schedule", "--task", "sample"]) 

    class DummyScheduler:
        def __init__(self):
            self.called = False
        def schedule_task(self, name):
            self.called = name
            return True
    sched = DummyScheduler()
    exit_code = handle_schedule_command(args, sched)
    assert exit_code == 0
    assert sched.called == "sample"


def test_configure(monkeypatch, tmp_path):
    monkeypatch.setattr("orchestrator.utils.configure.getpass.getpass", lambda _=None: "pw")
    cm = configure(master_password=None)
    assert isinstance(cm, ConfigManager)
