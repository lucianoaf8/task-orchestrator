from orchestrator.services.task_service import TaskService
from orchestrator.services.scheduling_service import SchedulingService
from orchestrator.core.config_manager import ConfigManager

class DummySched(SchedulingService):
    def __init__(self):
        super().__init__(scheduler=None)
        self.scheduled = []
    def schedule_task(self, name, command, cron):
        self.scheduled.append(name)
        return True
    def unschedule_task(self, name):
        self.scheduled.append(f'un-{name}')
        return True


def test_create_task(tmp_path):
    cm = ConfigManager(db_path=str(tmp_path / 'db.sqlite'))
    sched = DummySched()
    svc = TaskService(config_manager=cm, scheduling_service=sched)
    data = {'name': 'demo', 'task_type': 'shell', 'command': 'echo', 'schedule': '0 0 * * *', 'enabled': False}
    res = svc.create_task(data)
    assert res['success'] and res['task']['name'] == 'demo'
