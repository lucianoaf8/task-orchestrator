from types import SimpleNamespace
from unittest import mock
import pytest

import orchestrator.web.app as webapp

@pytest.fixture()
def app():
    app = webapp.create_app()
    app.testing = True
    return app


def request_context(app, url, method='POST', json=None):
    with app.test_request_context(url, method=method, json=json):
        rv = None
        if url.startswith('/api/tasks') and method=='POST' and 'delete' not in url:
            rv = webapp.add_or_update_task()
        elif url.startswith('/api/tasks') and method=='DELETE':
            rv = webapp.delete_task(url.rsplit('/',1)[1])
        return rv


def test_add_update_and_delete(app, monkeypatch):
    webapp.config_manager = mock.Mock()
    webapp.config_manager.get_task.return_value = {'type':'shell','command':'c','schedule':None,'timeout':0,'retry_count':0,'retry_delay':0,'dependencies':[]}
    resp = request_context(app,'/api/tasks',json={'name':'t','type':'shell','command':'c'})
    assert resp.json['status']=='success'
    resp = request_context(app,'/api/tasks/t',method='DELETE')
    assert resp.json['status']=='success'
