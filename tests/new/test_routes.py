from types import SimpleNamespace
from unittest import mock
import json
import pytest

from flask import Flask
from orchestrator.web.api import routes

class DummySched:
    def __init__(self):
        self.ops=[]
    def schedule_task(self, name, cmd, cron):
        self.ops.append(('sched', name))
        return True
    def unschedule_task(self, name):
        self.ops.append(('uns', name))
        return True
    def list_tasks(self):
        return [{'TaskName':'t','Status':'Ready'}]

class DummyCM:
    def __init__(self):
        self.tasks={'t':{'command':'c','schedule':'0 0 * * *'}}
        self.added=None
    def add_task(self, **kw):
        self.added=kw
    def get_task(self, name):
        return self.tasks.get(name)
    def get_all_tasks(self):
        return self.tasks

@pytest.fixture(autouse=True)
def _setup(monkeypatch):
    orig_cm = routes.CM
    orig_sched = routes.SCHEDULER
    monkeypatch.setattr(routes, 'CM', DummyCM())
    monkeypatch.setattr(routes, 'SCHEDULER', DummySched())
    yield
    routes.CM = orig_cm
    routes.SCHEDULER = orig_sched

def call(view, *args, **kw):
    with app.test_request_context(*args, **kw):
        resp = view()
        if isinstance(resp, tuple):
            resp[0].status_code = resp[1]
            return resp[0]
        return resp

app = Flask(__name__)
app.register_blueprint(routes.api_bp)

@pytest.fixture()
def client():
    app.testing = True
    with app.test_client() as cl:
        yield cl


def test_add_or_update_missing():
    resp = call(routes.add_or_update_task, '/api/tasks', method='POST', json={'name':'x'})
    assert resp.status_code==400


def test_add_or_update_success(monkeypatch):
    resp = call(routes.add_or_update_task, '/api/tasks', method='POST', json={'name':'t','type':'shell','command':'c','schedule':'0 0 * * *','enabled':True})
    assert resp.status_code==200
    assert routes.CM.added['name']=='t'
    assert routes.SCHEDULER.ops[0]==('sched','t')


def test_schedule_unschedule_list():
    resp=call(lambda: routes.schedule('t'), '/api/tasks/t/schedule')
    assert resp.get_json()['scheduled']
    resp=call(lambda: routes.unschedule('t'), '/api/tasks/t/unschedule', method='DELETE')
    assert resp.get_json()['unscheduled']
    resp=call(routes.list_scheduled, '/api/tasks/scheduled')
    assert resp.get_json()['scheduled_tasks'][0]['TaskName']=='t'


def test_health_and_scheduler_status():
    resp=call(routes.health, '/api/health')
    assert resp.status_code==200
    resp=call(routes.scheduler_status, '/api/system/scheduler-status')
    assert resp.get_json()['configured']==1
