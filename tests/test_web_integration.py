"""Phase 4 web-layer integration tests.

These lightweight tests validate that the new Flask API blueprint
(`/orchestrator/web/api/routes.py`) is registered correctly and that the
core endpoints behave as expected – *without* touching the real Windows
Task Scheduler.  External side-effects are stubbed out with ``unittest.mock``.
"""
from __future__ import annotations

import json
from typing import Generator

import pytest
from flask.testing import FlaskClient
from unittest.mock import MagicMock


@pytest.fixture(scope="session")
def app():
    """Return a Flask application instance configured for testing."""
    from orchestrator.web.app import create_app

    application = create_app()
    application.testing = True
    return application


@pytest.fixture()
def client(app) -> Generator[FlaskClient, None, None]:  # noqa: D401
    """Provide a test client with Windows-specific calls stubbed out."""
    # Patch Windows-scheduler interactions so tests are OS-agnostic.
    from orchestrator.web.api import routes as api_routes

    api_routes.SCHEDULER.schedule_task = MagicMock(return_value=True)  # type: ignore[assignment]
    api_routes.SCHEDULER.unschedule_task = MagicMock(return_value=True)  # type: ignore[assignment]
    api_routes.SCHEDULER.list_scheduled_tasks = MagicMock(return_value=[])  # type: ignore[assignment]

    with app.test_client() as client_ctx:
        yield client_ctx


def test_health_endpoint(client: FlaskClient):  # noqa: D401
    """`GET /api/health` returns *healthy* JSON payload."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"


def test_create_task_schedules_immediately(client: FlaskClient):  # noqa: D401
    """Posting a new task triggers immediate scheduling via TaskScheduler."""
    payload = {
        "name": "test_web_task",
        "type": "shell",
        "command": "echo hello",
        "schedule": "*/30 * * * *",
    }

    resp = client.post("/api/tasks", data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200

    body = resp.get_json()
    assert body["status"] == "success"
    assert body["scheduled"] is True


def test_unschedule_task(client: FlaskClient):  # noqa: D401
    """`DELETE /api/tasks/<name>/unschedule` responds with success JSON."""
    resp = client.delete("/api/tasks/test_web_task/unschedule")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["unscheduled"] is True


def test_scheduler_status(client: FlaskClient):  # noqa: D401
    """`GET /api/system/scheduler-status` returns configured/scheduled counts."""
    resp = client.get("/api/system/scheduler-status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "configured" in data and "scheduled" in data
