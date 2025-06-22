from types import SimpleNamespace
import pytest

import orchestrator.web.app as webapp


@pytest.fixture()
def app():
    app = webapp.create_app()
    app.testing = True
    return app


@pytest.fixture()
def client(app):
    with app.test_client() as cl:
        yield cl


def test_health_check_success(client, monkeypatch):
    monkeypatch.setattr(webapp.config_manager, "get_all_tasks", lambda: {"a": {}})
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["tasks_configured"] == 1


def test_health_check_failure(client, monkeypatch):
    def boom():
        raise RuntimeError("db")
    monkeypatch.setattr(webapp.config_manager, "get_all_tasks", boom)
    resp = client.get("/health")
    assert resp.status_code == 500
    assert resp.get_json()["status"] == "unhealthy"


def call_cmd(app, payload):
    with app.test_request_context("/api/test-command", method="POST", json=payload):
        rv = webapp.test_command()
        if isinstance(rv, tuple):
            resp, status = rv
            resp.status_code = status
            return resp
        return rv


def test_test_command_success(app, monkeypatch):
    cp = SimpleNamespace(returncode=0, stdout="ok", stderr="")
    monkeypatch.setattr(webapp.subprocess, "run", lambda *a, **k: cp)
    resp = call_cmd(app, {"command": "echo"})
    assert resp.json["exit_code"] == 0


def test_test_command_timeout(app, monkeypatch):
    def boom(*a, **k):
        raise webapp.subprocess.TimeoutExpired(cmd="x", timeout=30)
    monkeypatch.setattr(webapp.subprocess, "run", boom)
    resp = call_cmd(app, {"command": "sleep"})
    assert resp.status_code == 400
    assert "timed out" in resp.json["error"]


def test_test_command_not_found(app, monkeypatch):
    def nf(*a, **k):
        raise FileNotFoundError
    monkeypatch.setattr(webapp.subprocess, "run", nf)
    resp = call_cmd(app, {"command": "none"})
    assert resp.status_code == 400
    assert "not found" in resp.json["error"].lower()
