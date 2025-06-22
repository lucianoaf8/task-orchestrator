from types import SimpleNamespace
from unittest import mock

import orchestrator.web.dashboard as dash


def test_main_runs_app(monkeypatch):
    fake_app = SimpleNamespace(run=mock.MagicMock())
    monkeypatch.setattr(dash, "create_app", lambda: fake_app)
    dash.main(host="h", port=1234, debug=False)
    fake_app.run.assert_called_once_with(host="h", port=1234, debug=False)
