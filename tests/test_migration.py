"""Migration process tests (Phase-6)."""
from __future__ import annotations



from tools.migration import LegacyMigration


def test_migrate_all_tasks_calls_scheduler(monkeypatch):  # noqa: D401
    mig = LegacyMigration()
    monkeypatch.setattr(mig.cm, "get_all_tasks", lambda: {"a": {}, "b": {}})

    calls = {}

    def fake_schedule(name):  # noqa: D401
        calls[name] = True
        return True

    monkeypatch.setattr(mig.scheduler, "schedule_task", fake_schedule)

    res = mig.migrate_all_tasks()
    assert res == {"a": True, "b": True}
    assert len(calls) == 2


def test_validate_migration(monkeypatch):  # noqa: D401
    mig = LegacyMigration()
    monkeypatch.setattr(mig.cm, "get_all_tasks", lambda: {"x": {}, "y": {}})
    monkeypatch.setattr(mig.scheduler, "task_exists", lambda n: n == "x")
    assert mig.validate_migration() is False
