import os
from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.environment import get_config_with_env_override


def test_env_override(monkeypatch, tmp_path):
    db = tmp_path / "db.sqlite"
    cm = ConfigManager(db_path=str(db))
    cm.store_config('email', 'smtp_server', 'db.example')
    monkeypatch.setenv('ORC_EMAIL_SMTP_SERVER', 'env.example')
    val = get_config_with_env_override(cm, 'email', 'smtp_server')
    assert val == 'env.example'
