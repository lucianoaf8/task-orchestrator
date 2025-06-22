import re
from datetime import datetime
import pytest

from orchestrator.utils.cron_converter import CronConverter


def test_cron_to_schtasks_windows_formats():
    assert CronConverter.cron_to_schtasks_params("8:00") == {"SC": "DAILY", "ST": "08:00"}
    assert CronConverter.cron_to_schtasks_params("Tue 9:30") == {
        "SC": "WEEKLY",
        "D": "TUE",
        "ST": "09:30",
    }
    assert CronConverter.cron_to_schtasks_params("15 7:05") == {
        "SC": "MONTHLY",
        "D": "15",
        "ST": "07:05",
    }


@pytest.mark.parametrize("expr", ["bad", "* *" ])
def test_cron_to_schtasks_invalid(expr):
    with pytest.raises(ValueError):
        CronConverter.cron_to_schtasks_params(expr)


def test_validate_cron_expression_windows_style():
    ok, msg = CronConverter.validate_cron_expression("SUN 06:00")
    assert ok is True and msg == "OK"


def test_get_next_run_time_handles_invalid():
    assert CronConverter.get_next_run_time("not a cron") is None
    ts = CronConverter.get_next_run_time("*/10 * * * *")
    assert isinstance(ts, datetime)
