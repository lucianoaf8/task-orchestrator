"""End-to-end API workflow test (Phase-6)."""
from __future__ import annotations

from typing import Dict, List

import pytest
from flask.testing import FlaskClient

from orchestrator.utils.windows_scheduler import WindowsScheduler


@pytest.fixture()
def client(monkeypatch) -> FlaskClient:  # noqa: D401
    """Flask test-client with WindowsScheduler mocked in-memory."""

    fake_tasks: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # In-memory replacements for WindowsScheduler methods
    # ------------------------------------------------------------------
    def _create(self, name, cmd, params, desc):  # noqa: D401
        fake_tasks[name] = {"cmd": cmd, "params": params, "desc": desc}
        return True

    def _delete(self, name):  # noqa: D401
        return fake_tasks.pop(name, None) is not None

    def _list(self):  # noqa: D401
        return [{"TaskName": n, "Status": "Ready"} for n in fake_tasks]

    def _exists(self, name):  # noqa: D401
        return name in fake_tasks

    monkeypatch.setattr(WindowsScheduler, "create_task", _create, raising=True)
    monkeypatch.setattr(WindowsScheduler, "delete_task", _delete, raising=True)
    monkeypatch.setattr(WindowsScheduler, "list_orchestrator_tasks", _list, raising=True)
    monkeypatch.setattr(WindowsScheduler, "task_exists", _exists, raising=True)

    # Provide Flask app
    from orchestrator.web.app import app  # imported late so monkeypatch takes effect first

    app.config.update(TESTING=True)
    return app.test_client()


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------

def test_full_create_schedule_unschedule(client: FlaskClient):  # noqa: D401
    """Create task via API, ensure it is scheduled, then unschedule."""

    new_task = {
        "name": "e2e_sample",
        "type": "python",
        "command": "python -c \"print('ok')\"",
        "schedule": "*/5 * * * *",
        "enabled": True,
    }

    # 1. Create & auto-schedule
    resp = client.post("/api/tasks", json=new_task)
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["status"] == "success" and payload["scheduled"] is True

    # 2. List scheduled tasks – should contain our task
    resp = client.get("/api/tasks/scheduled")
    data = resp.get_json()
    names: List[str] = [t["TaskName"] for t in data["scheduled_tasks"]]
    assert "e2e_sample" in names

    # 3. Scheduler status endpoint reflects counts
    resp = client.get("/api/system/scheduler-status")
    meta = resp.get_json()
    assert meta["scheduled"] >= 1

    # 4. Unschedule task
    resp = client.delete("/api/tasks/e2e_sample/unschedule")
    assert resp.status_code == 200 and resp.get_json()["unscheduled"] is True

    # 5. Verify removal
    resp = client.get("/api/tasks/scheduled")
    names = [t["TaskName"] for t in resp.get_json()["scheduled_tasks"]]
    assert "e2e_sample" not in names
