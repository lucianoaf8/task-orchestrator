"""Additional coverage for CronConverter helpers and support scripts (Phase-6)."""
from __future__ import annotations

import sys
from datetime import datetime
from types import SimpleNamespace
from unittest import mock

import pytest

from orchestrator.utils.cron_converter import CronConverter
from orchestrator.utils.windows_scheduler import WindowsScheduler

# ---------------------------------------------------------------------------
# CronConverter extra helpers
# ---------------------------------------------------------------------------

def test_get_next_run_time_valid():  # noqa: D401
    ts = CronConverter.get_next_run_time("*/30 * * * *")
    assert isinstance(ts, datetime)


def test_get_next_run_time_invalid():  # noqa: D401
    assert CronConverter.get_next_run_time("not a cron") is None

# ---------------------------------------------------------------------------
# WindowsScheduler enable/disable/status
# ---------------------------------------------------------------------------

@pytest.fixture()
def ws(monkeypatch):  # noqa: D401
    """Return scheduler with patched _run."""
    sch = WindowsScheduler()
    # default: success, empty stdout
    monkeypatch.setattr(sch, "_run", lambda *a, **k: (True, "{}") if k.get("capture_output") else True)
    return sch


def test_enable_disable_task(ws):  # noqa: D401
    assert ws.enable_task("foo") is True
    assert ws.disable_task("foo") is True


def test_get_task_status_parses_json(monkeypatch):  # noqa: D401
    sch = WindowsScheduler()

    sample_json = '[{"TaskName":"\\\\Orchestrator\\\\Orc_test","Status":"Ready"}]'
    monkeypatch.setattr(sch, "_run", lambda *a, **k: (True, sample_json))

    st = sch.get_task_status("test")
    assert st and st["Status"] == "Ready"

# ---------------------------------------------------------------------------
# Dependency checker and cleanup utilities
# ---------------------------------------------------------------------------

from scripts.checks import check_dependencies as chk_dep  # noqa: E402
from tools import cleanup as cln  # noqa: E402


def test_check_dependencies_all_ok(monkeypatch):  # noqa: D401
    task = {"dependencies": ["file:C:/exists.txt", "command:python -V"]}

    # Fake ConfigManager returning our task
    class DummyCM:  # noqa: D401
        def get_task(self, _):  # noqa: D401
            return task

    monkeypatch.setattr(chk_dep, "ConfigManager", lambda *a, **k: DummyCM())
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr("subprocess.run", lambda *a, **k: SimpleNamespace(returncode=0, stdout=b"", stderr=b""))

    assert chk_dep.main(["whatever"]) == 0


def test_check_dependencies_failure(monkeypatch):  # noqa: D401
    task = {"dependencies": ["file:C:/missing.txt"]}

    class DummyCM:  # noqa: D401
        def get_task(self, _):  # noqa: D401
            return task

    monkeypatch.setattr(chk_dep, "ConfigManager", lambda *a, **k: DummyCM())
    monkeypatch.setattr("os.path.exists", lambda p: False)

    assert chk_dep.main(["foo"]) == 1


def test_cleanup_legacy(monkeypatch):  # noqa: D401
    sample = '\n'.join([
        '"Image Name","PID","Session Name","Session#","Mem Usage","Status","User Name","CPU Time","Window Title"',
        '"python.exe","1234","Console","1","10,000 K","","","0:00:00","main.py"',
    ])
    monkeypatch.setattr(cln.subprocess, "check_output", lambda *a, **k: sample)
    killed = []
    monkeypatch.setattr(cln.os, "kill", lambda pid, sig: killed.append(pid))

    assert cln.cleanup_legacy() == 1
    assert killed == [1234]
