import pytest
from orchestrator.services.task_service import TaskService
from orchestrator.core.exceptions import ValidationError, OrchestratorError, SchedulingError
from orchestrator.services.scheduling_service import SchedulingService


class DummyCfg:
    def __init__(self):
        self.tasks = {}
    def get_task(self, name):
        return self.tasks.get(name)
    def add_task_with_scheduling(self, data):
        if data.get('boom'):
            raise RuntimeError('x')
        if data.get('sched_err'):
            raise SchedulingError('fail')
        self.tasks[data['name']] = data
    def get_all_tasks(self):
        return {'a': {'name': 'a'}}


class DummySched(SchedulingService):
    def __init__(self):
        super().__init__(scheduler=None)


def make_service():
    return TaskService(config_manager=DummyCfg(), scheduling_service=DummySched())


def test_get_and_list():
    svc = make_service()
    svc._cfg.tasks['x'] = {'name': 'x'}
    assert svc.get_task('x') == {'name': 'x'}
    assert svc.list_tasks() == {'a': {'name': 'a'}}


def test_create_task_edge_cases():
    svc = make_service()
    with pytest.raises(AttributeError):
        svc.create_task(['bad'])
    with pytest.raises(ValidationError):
        svc.create_task({'command': 'c'})
    with pytest.raises(SchedulingError):
        svc.create_task({'name': 'n', 'sched_err': True})
    with pytest.raises(OrchestratorError):
        svc.create_task({'name': 'n', 'boom': True})
