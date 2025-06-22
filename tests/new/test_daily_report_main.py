from unittest.mock import patch, MagicMock
import scripts.notifications.daily_report as dr
import pytest


def test_daily_report_main_exit(monkeypatch):
    fake_gen = MagicMock()
    fake_gen.send_daily_report.return_value = True
    monkeypatch.setattr(dr, 'DailyReportGenerator', lambda mp=None: fake_gen)
    with patch.object(dr.sys, 'argv', [__file__]):
        with pytest.raises(SystemExit) as exc:
            dr.main()
    assert exc.value.code == 0
    fake_gen.send_daily_report.return_value = False
    with patch.object(dr.sys, 'argv', [__file__]):
        with pytest.raises(SystemExit) as exc:
            dr.main()
    assert exc.value.code == 1
