"""Convert *nix cron expressions to parameters for *schtasks.exe*.

Only a subset of cron syntax is supported: minute, hour, day-of-month,
month, day-of-week.  Advanced features such as @reboot or seconds are
**not** handled here.  Unsupported expressions raise ``ValueError``.
"""

from __future__ import annotations

import logging
import re
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

        expr = cron_expression.strip()
        # -------------------------------
        # Windows-style schedule parsing
        # -------------------------------
        # Pattern 1: Daily HH:MM
        m_daily = re.fullmatch(r"(\d{1,2}):(\d{2})", expr)
        if m_daily:
            h, m = map(int, m_daily.groups())
            return {"SC": "DAILY", "ST": f"{h:02d}:{m:02d}"}

        # Pattern 2: Weekly DAY HH:MM (e.g. MON 08:00)
        m_weekly = re.fullmatch(r"(?i)(SUN|MON|TUE|WED|THU|FRI|SAT)\s+(\d{1,2}):(\d{2})", expr)
        if m_weekly:
            dow, h, m = m_weekly.groups()
            return {"SC": "WEEKLY", "D": dow.upper(), "ST": f"{int(h):02d}:{int(m):02d}"}

        # Pattern 3: Monthly N HH:MM (e.g. 15 09:30)
        m_monthly = re.fullmatch(r"([1-9]|[12]\d|3[01])\s+(\d{1,2}):(\d{2})", expr)
        if m_monthly:
            day, h, m = m_monthly.groups()
            return {"SC": "MONTHLY", "D": day, "ST": f"{int(h):02d}:{int(m):02d}"}

        # -------------------------------------------
        # Legacy cron syntax (backwards compatibility)
        # -------------------------------------------
        fields = expr.split()
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

        # Validate new Windows-style formats first
        if re.fullmatch(r"(\d{1,2}):(\d{2})", cron_expression.strip()):
            return True, "OK"
        if re.fullmatch(r"(?i)(SUN|MON|TUE|WED|THU|FRI|SAT)\s+(\d{1,2}):(\d{2})", cron_expression.strip()):
            return True, "OK"
        if re.fullmatch(r"([1-9]|[12]\d|3[01])\s+(\d{1,2}):(\d{2})", cron_expression.strip()):
            return True, "OK"

        # Fallback to cron expression validation for backward compatibility
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
