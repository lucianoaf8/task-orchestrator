from orchestrator.services.scheduling_service import SchedulingService


class DummyScheduler:
    def __init__(self):
        self.calls = []
    def create_task(self, name, cmd, params, desc):
        self.calls.append(('create', name, params))
        return True
    def delete_task(self, name):
        self.calls.append(('delete', name))
        return True
    def change_task(self, task_name, schedule_trigger=None, new_command=None):
        self.calls.append(('change', schedule_trigger, new_command))
        return True
    def task_exists(self, name):
        return name == 'yes'
    def list_orchestrator_tasks(self):
        return []


def test_change_task_only_command():
    ds = DummyScheduler()
    svc = SchedulingService(ds)
    assert svc.change_task('t', command='cmd')
    assert ('change', None, 'cmd') in ds.calls


def test_change_task_with_cron(monkeypatch):
    ds = DummyScheduler()
    svc = SchedulingService(ds)
    called = {}
    monkeypatch.setattr(svc, 'unschedule_task', lambda name: called.setdefault('uns', name))
    monkeypatch.setattr(svc, 'schedule_task', lambda name, command, cron: called.setdefault('sched', (name, cron)))
    svc.change_task('t', cron='0 0 * * *', command='c')
    assert called['uns'] == 't'
    assert called['sched'][0] == 't'
    assert ('change', None, 'c') not in ds.calls


def test_task_exists():
    svc = SchedulingService(DummyScheduler())
    assert svc.task_exists('yes')
