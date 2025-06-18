"""Unit tests for TaskScheduler and CronConverter (Phase 2)."""

from __future__ import annotations

import tempfile
import sys
from types import SimpleNamespace
from pathlib import Path
from unittest import mock

import pytest

from orchestrator.core.scheduler import TaskScheduler
from orchestrator.core.task_result import TaskResult
from orchestrator.utils.cron_converter import CronConverter


@pytest.fixture()
def scheduler(tmp_path):
    """Return a TaskScheduler instance backed by an isolated SQLite DB."""

    ts = TaskScheduler()
    # Point the ConfigManager to a temporary database so we don't pollute real data
    db_path = tmp_path / "test.db"
    ts.config_manager = ts.config_manager.__class__(db_path=str(db_path))  # type: ignore[arg-type]
    return ts


def test_cron_converter_basic():
    assert CronConverter.cron_to_schtasks_params("0 6 * * *") == {"SC": "DAILY", "ST": "06:00"}
    assert CronConverter.cron_to_schtasks_params("0 8 * * 1") == {"SC": "WEEKLY", "D": "MON", "ST": "08:00"}
    assert CronConverter.cron_to_schtasks_params("0 9 1 * *") == {"SC": "MONTHLY", "D": "1", "ST": "09:00"}
    assert CronConverter.cron_to_schtasks_params("*/30 * * * *") == {"SC": "MINUTE", "MO": "30"}


def test_cron_converter_validation():
    ok, msg = CronConverter.validate_cron_expression("0 6 * * *")
    assert ok is True and msg == "OK"
    ok, _ = CronConverter.validate_cron_expression("invalid")
    assert ok is False


def test_scheduler_schedule_task(scheduler):
    # Add a dummy task
    scheduler.config_manager.add_task(
        name="dummy",
        task_type="test",
        command="python -c \"exit(0)\"",
        schedule="0 6 * * *",
        enabled=True,
    )

    with mock.patch.object(scheduler.windows_scheduler, "create_task", return_value=True) as m_create:
        ok = scheduler.schedule_task("dummy")
        assert ok is True
        m_create.assert_called_once()


def test_scheduler_unschedule(scheduler):
    with mock.patch.object(scheduler.windows_scheduler, "delete_task", return_value=True) as m_del:
        ok = scheduler.unschedule_task("dummy")
        assert ok is True
        m_del.assert_called_once()


def test_scheduler_execute_task(monkeypatch, scheduler):
    # Patch main.TaskManager.run_task_with_retry to return TaskResult
    dummy_result = TaskResult(task_name="dummy", status="SUCCESS")

    class DummyTM:  # noqa: D401
        def run_task_with_retry(self, task_name):  # noqa: D401
            return dummy_result

        def check_dependencies(self, task_name):  # noqa: D401
            return True, "OK"

    monkeypatch.setitem(sys.modules, "main", SimpleNamespace(TaskManager=DummyTM))

    result = scheduler.execute_task("dummy")
    assert isinstance(result, TaskResult)
    assert result.status == "SUCCESS"
