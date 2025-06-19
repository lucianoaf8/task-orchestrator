from datetime import datetime, timedelta
from orchestrator.core.task_result import TaskResult


def test_serialization_roundtrip():
    start = datetime(2020, 1, 1, 0, 0, 0)
    end = datetime(2020, 1, 1, 0, 5, 0)
    tr = TaskResult(task_name="demo", status="SUCCESS", start_time=start, end_time=end, exit_code=0)
    js = tr.to_json()
    restored = TaskResult.from_json(js)
    assert restored.task_name == "demo"
    assert restored.exit_code == 0
    assert restored.duration == timedelta(minutes=5)
