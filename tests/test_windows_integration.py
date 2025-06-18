"""Tests for WindowsScheduler wrapper (Phase-6).

All calls to *schtasks.exe* are mocked so these tests run on any OS.
"""
from __future__ import annotations

import json
from unittest import mock

import pytest

from orchestrator.utils.windows_scheduler import WindowsScheduler


@pytest.fixture()
def ws():  # noqa: D401
    """Return a WindowsScheduler instance with mocked subprocess."""
    return WindowsScheduler()


@mock.patch("subprocess.run")
def test_create_task_success(m_run, ws):  # noqa: D401
    m_run.return_value.returncode = 0
    ok = ws.create_task("foo", "echo 1", {"SC": "DAILY", "ST": "06:00"})
    assert ok is True
    assert m_run.called


@mock.patch("subprocess.run")
def test_delete_task_failure(m_run, ws):  # noqa: D401
    m_run.return_value.returncode = 1
    ok = ws.delete_task("bar")
    assert ok is False


@mock.patch("subprocess.run")
def test_list_tasks_parses_json(m_run, ws):  # noqa: D401
    sample = json.dumps([
        {"TaskName": r"\\Orchestrator\\Orc_test1"},
        {"TaskName": r"\\NotOurs\\Other"},
    ])
    m_run.return_value.returncode = 0
    m_run.return_value.stdout = sample

    tasks = ws.list_orchestrator_tasks()
    assert len(tasks) == 1 and tasks[0]["TaskName"].endswith("test1")
