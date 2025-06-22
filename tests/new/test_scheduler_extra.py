from types import SimpleNamespace
from unittest import mock

from orchestrator.core.scheduler import TaskScheduler
from orchestrator.core.task_result import TaskResult

class DummyWS:
    def __init__(self):
        self.created = []
        self.deleted = []
        self.changed = []
    def create_task(self, name, cmd, params, description=None):
        self.created.append((name, params))
        return True
    def delete_task(self, name):
        self.deleted.append(name)
        return True
    def change_task(self, task_name, schedule_trigger=None, new_command=None):
        self.changed.append((task_name, new_command))
        return True
    def list_orchestrator_tasks(self):
        return [{'TaskName':'a'}]
    def task_exists(self, name):
        return name=='a'

def make_sched(tmp_path):
    ts = TaskScheduler()
    ts.config_manager = ts.config_manager.__class__(db_path=str(tmp_path/'db.sqlite'))
    ts.windows_scheduler = DummyWS()
    ts.execution_engine = mock.MagicMock(execute_task=lambda n: TaskResult(task_name=n,status='SUCCESS'))
    return ts


def test_schedule_all_and_update(tmp_path):
    ts = make_sched(tmp_path)
    ts.config_manager.add_task('a','t','c','0 0 * * *')
    res = ts.schedule_all_tasks()
    assert res == {'a': True}
    ts.update_task('a', new_command='x')
    assert ts.windows_scheduler.changed[0]==('a','x')
    ts.update_task('a', new_schedule='1 0 * * *')
    assert ts.windows_scheduler.created[-1][0]=='a'


def test_other_ops(tmp_path):
    ts = make_sched(tmp_path)
    assert ts.unschedule_task('a')
    assert ts.task_exists('a')
    assert ts.list_scheduled_tasks()==[{'TaskName':'a'}]
    r= ts.execute_task('a')
    assert isinstance(r, TaskResult)
    assert ts.check_dependencies('missing')[0] is False
    ts.config_manager.add_task('b','t','c')
    assert ts.validate_task_config('b')[0]
