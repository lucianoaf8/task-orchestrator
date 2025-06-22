from orchestrator.services.scheduling_service import SchedulingService

class DummyWS:
    def __init__(self):
        self.created = []
        self.deleted = []
    def create_task(self, name, cmd, params, desc):
        self.created.append(name)
        return True
    def delete_task(self, name):
        self.deleted.append(name)
        return True
    def change_task(self, *a, **k):
        return True
    def task_exists(self, name):
        return True
    def list_orchestrator_tasks(self):
        return [{'TaskName': 'x', 'Status': 'Ready'}]


def test_schedule_and_unschedule():
    svc = SchedulingService(DummyWS())
    assert svc.schedule_task('a', 'cmd', '0 0 * * *')
    assert svc.unschedule_task('a')
