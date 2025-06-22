from types import SimpleNamespace
from unittest import mock
import orchestrator.web.app as webapp
import pytest


@pytest.fixture()
def app():
    app = webapp.create_app()
    app.testing = True
    return app


def test_dashboard_and_pages(app, monkeypatch):
    monkeypatch.setattr(webapp, 'render_template', lambda tpl: f'render:{tpl}')
    with app.test_request_context('/'):
        assert webapp.dashboard() == 'render:dashboard.html'
        assert webapp.task_manager_ui() == 'render:task-manager-ui.html'
        assert webapp.compact_scheduler_ui() == 'render:compact-task-scheduler.html'


def test_get_tasks_and_history(app, monkeypatch):
    webapp.config_manager = mock.Mock()
    webapp.config_manager.get_all_tasks.return_value = {'t': {}}
    webapp.config_manager.get_task_history.return_value = [{'status': 'S'}]
    with app.test_request_context('/api/tasks'):
        resp = webapp.get_tasks()
        assert resp.json['tasks']['t']['last_execution']['status'] == 'S'
    with app.test_request_context('/api/tasks/t/history'):
        resp = webapp.get_task_history('t')
        assert resp.json['task_name'] == 't'


def test_run_task_manually(app):
    with app.test_request_context('/api/tasks/t/run', method='POST'):
        resp = webapp.run_task_manually('t')
        assert 'execution requested' in resp.json['message']
