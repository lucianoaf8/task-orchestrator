from datetime import datetime, timedelta
from orchestrator.core.task_result import TaskResult


def test_json_cycle():
    start = datetime.now()
    end = start + timedelta(seconds=5)
    tr = TaskResult('task', 'SUCCESS', start_time=start, end_time=end)
    json_str = tr.to_json()
    new = TaskResult.from_json(json_str)
    assert new.start_time == start and new.end_time == end and new.task_name == 'task'
