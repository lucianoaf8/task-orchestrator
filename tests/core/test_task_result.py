from datetime import datetime
from orchestrator.core.task_result import TaskResult


def test_to_from_dict():
    now = datetime.now()
    tr = TaskResult(task_name='t', status='SUCCESS', start_time=now, end_time=now)
    d = tr.to_dict()
    new = TaskResult.from_dict(d)
    assert new.start_time == tr.start_time and new.end_time == tr.end_time


def test_duration():
    start = datetime.now()
    from datetime import timedelta
    end = start + timedelta(seconds=2)
    tr = TaskResult(task_name='t', status='SUCCESS', start_time=start, end_time=end)
    assert tr.duration.total_seconds() == 2
