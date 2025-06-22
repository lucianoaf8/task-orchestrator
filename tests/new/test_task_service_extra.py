from unittest import mock
import pytest

from orchestrator.services.task_service import TaskService
from orchestrator.core.config_manager import ConfigManager
from orchestrator.services.scheduling_service import SchedulingService
from orchestrator.core.exceptions import ValidationError

class DummySched(SchedulingService):
    def __init__(self):
        super().__init__(scheduler=None)
        self.changed = []
    def change_task(self, name, cron=None, command=None):
        self.changed.append((name, cron, command))
        return True
    def unschedule_task(self, name):
        self.changed.append(('un', name))
        return True


def make_svc(tmp_path):
    cm = ConfigManager(db_path=str(tmp_path/'db.sqlite'))
    sched = DummySched()
    return TaskService(config_manager=cm, scheduling_service=sched)


def test_update_and_delete(tmp_path):
    svc = make_svc(tmp_path)
    svc._cfg.add_task('a','t','c','0 0 * * *')
    # avoid unexpected kwargs to add_task by patching it
    svc._cfg.add_task = lambda **kw: None
    res = svc.update_task('a', {'command':'x'})
    assert res['task']['command']=='x'
    svc.update_task('a', {'enabled':False})
    assert ('un','a') in svc._sched.changed
    assert svc.delete_task('a')
    with pytest.raises(ValidationError):
        svc.delete_task('missing')
