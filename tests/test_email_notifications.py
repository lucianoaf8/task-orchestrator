"""Tests for e-mail notification features.

These tests patch ``smtplib.SMTP`` so that no real
messages are delivered and validate that the notification
helpers attempt to send an e-mail for

1. Immediate failure notifications (re-using
   ``scripts.notifications.daily_email_main.send_email``).
2. The daily HTML report (``scripts.notifications.daily_report.DailyReportGenerator``).
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Lightweight stub that fulfils the subset of ConfigManager behaviour required
# by the notification scripts. No actual database or encryption is used.
# ---------------------------------------------------------------------------


class DummyConfigManager:  # pragma: no cover – trivial helper
    """Minimal stand-in for :class:`orchestrator.core.config_manager.ConfigManager`."""

    # Hard-coded secrets purely for the purpose of the unit tests
    _credentials = {
        "email_username": "noreply@example.com",
        "email_password": "dummy-password",
    }
    _config = {
        ("email", "smtp_server"): "smtp.test.local",
        ("email", "smtp_port"): "25",
        ("email", "recipients"): "[\"alerts@example.com\"]",
        ("email", "daily_report_recipients"): "[\"report@example.com\"]",
    }

    # -----------------------------
    # Credential / config accessors
    # -----------------------------
    def get_credential(self, name: str):  # noqa: D401 – test stub
        return self._credentials.get(name)

    def get_config(self, section: str, key: str, default: str | None = None):  # noqa: D401 – test stub
        return self._config.get((section, key), default)

    # -----------------------------
    # Task-history helpers (daily report)
    # -----------------------------
    def get_all_tasks(self):  # noqa: D401 – test stub
        # Return a *single* dummy task so the HTML report includes a row.
        return {
            "demo_task": {
                "name": "demo_task",
                "type": "script",
                "schedule": "0 * * * *",  # hourly cron
            }
        }

    def get_task_history(self, task_name: str, limit: int = 100):  # noqa: D401 – test stub
        # Provide one failed execution so the report includes a failure.
        return [
            {
                "start_time": "2025-06-19T00:00:00",
                "end_time": "2025-06-19T00:00:05",
                "status": "FAILED",
                "error": "Example stack trace …",
                "exit_code": 1,
                "retry_count": 0,
            }
        ]


@pytest.fixture()
def dummy_cm():
    """Provide a pre-instantiated :class:`DummyConfigManager`."""

    return DummyConfigManager()


# ---------------------------------------------------------------------------
# Patches --------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _patch_config_manager_module(module: types.ModuleType):  # pragma: no cover
    """Replace ``ConfigManager`` in *module* with our Dummy stub."""

    module.ConfigManager = DummyConfigManager  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Tests ----------------------------------------------------------------------
# ---------------------------------------------------------------------------


def test_send_email_on_failure(dummy_cm):
    """Validate that *immediate* failure notification attempts to send an e-mail."""

    # Import lazily so patching in one test does not bleed into others
    from scripts.notifications import daily_email_main as dem

    # Patch SMTP so no network connection is attempted
    with patch("smtplib.SMTP", autospec=True) as mock_smtp:
        dem.send_email(dummy_cm, "Body text")

        # Ensure a connection was attempted and send_message called
        instance = mock_smtp.return_value.__enter__.return_value
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with(
            dummy_cm.get_credential("email_username"),
            dummy_cm.get_credential("email_password"),
        )
        instance.send_message.assert_called_once()


def test_send_daily_report(dummy_cm):
    """Validate that the daily report e-mail is generated and sent."""

    from importlib import reload

    # We must patch ConfigManager *before* daily_report is imported so that the
    # class reference resolution happens correctly.
    with patch(
        "scripts.notifications.daily_report.ConfigManager",
        DummyConfigManager,
    ):
        from scripts.notifications import daily_report as dr  # pylint: disable=import-error

        reload(dr)  # ensure patch is effective in already-imported modules

        generator = dr.DailyReportGenerator()

        with patch("smtplib.SMTP", autospec=True) as mock_smtp:
            success = generator.send_daily_report()

            assert success is True
            instance = mock_smtp.return_value.__enter__.return_value
            instance.starttls.assert_called_once()
            instance.login.assert_called_once()
            instance.send_message.assert_called_once()
