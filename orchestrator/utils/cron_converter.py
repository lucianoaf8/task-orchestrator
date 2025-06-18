"""Convert *nix cron expressions to parameters for *schtasks.exe*.

Only a subset of cron syntax is supported: minute, hour, day-of-month,
month, day-of-week.  Advanced features such as @reboot or seconds are
**not** handled here.  Unsupported expressions raise ``ValueError``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict

from croniter import croniter, CroniterBadCronError

__all__ = ["CronConverter"]

logger = logging.getLogger(__name__)


class CronConverter:  # noqa: D101 – documented in module docstring
    @staticmethod
    def cron_to_schtasks_params(cron_expression: str) -> Dict[str, str]:
        """Translate a cron string to *schtasks.exe* flags.

        Returns a dict mapping flag → value (may be empty string for flags that
        are switches).  Currently implemented rules:

        * Every-day, same-time → `/SC DAILY /ST HH:MM`
        * Specific weekday → `/SC WEEKLY /D MON /ST HH:MM`
        * Specific day-of-month (1–31) → `/SC MONTHLY /D N /ST HH:MM`
        * Minute frequency (*/N) → `/SC MINUTE /MO N`
        """

        fields = cron_expression.strip().split()
        if len(fields) != 5:
            raise ValueError("Cron expression must have 5 fields (minute hour dom month dow)")

        minute, hour, dom, month, dow = fields

        if minute.startswith("*/") and all(x == "*" for x in (hour, dom, month, dow)):
            # every N minutes
            interval = minute[2:]
            if not interval.isdigit():
                raise ValueError("Invalid minute interval in cron expression")
            return {"SC": "MINUTE", "MO": interval}

        if all(x == "*" for x in (dom, month, dow)):
            # daily at specific hh:mm
            return {"SC": "DAILY", "ST": f"{int(hour):02d}:{int(minute):02d}"}

        if dow != "*" and all(x == "*" for x in (dom, month)):
            # weekly on weekday code
            dow_map = [
                "SUN",
                "MON",
                "TUE",
                "WED",
                "THU",
                "FRI",
                "SAT",
            ]
            try:
                dow_int = int(dow)
            except ValueError:
                raise ValueError("Day-of-week must be numeric 0–6") from None
            if not 0 <= dow_int <= 6:
                raise ValueError("Day-of-week must be 0–6")
            return {
                "SC": "WEEKLY",
                "D": dow_map[dow_int],
                "ST": f"{int(hour):02d}:{int(minute):02d}",
            }

        if dom != "*" and all(x == "*" for x in (dow,)):
            # monthly on fixed day
            if not dom.isdigit() or not 1 <= int(dom) <= 31:
                raise ValueError("Day-of-month must be 1–31")
            return {
                "SC": "MONTHLY",
                "D": dom,
                "ST": f"{int(hour):02d}:{int(minute):02d}",
            }

        raise ValueError("Unsupported cron expression for Windows scheduler")

    # ---------------------------------------------------------
    # Helper methods (non-essential but useful for UI, tests…)
    # ---------------------------------------------------------
    @staticmethod
    def validate_cron_expression(cron_expression: str):
        """Return (bool, message) indicating validity of cron string."""

        try:
            croniter(cron_expression)
            return True, "OK"
        except CroniterBadCronError as exc:
            return False, str(exc)

    @staticmethod
    def get_next_run_time(cron_expression: str):
        """Compute next execution time for display purposes."""

        try:
            itr = croniter(cron_expression, datetime.now())
            return itr.get_next(datetime)
        except CroniterBadCronError:
            return None
