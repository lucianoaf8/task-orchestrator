import argparse
import sys
from types import SimpleNamespace
from unittest import mock

import orchestrator.utils.configure as cfg


def test_configure_prompts_for_password(monkeypatch):
    dummy_cm = mock.MagicMock()
    monkeypatch.setattr(cfg, "ConfigManager", lambda master_password: dummy_cm)
    monkeypatch.setattr(cfg.getpass, "getpass", lambda prompt: "secret")

    result = cfg.configure()
    assert result is dummy_cm


def test_parse_args_parses_password(monkeypatch):
    monkeypatch.setattr(cfg, "ConfigManager", mock.Mock())
    monkeypatch.setattr(sys, "argv", ["prog", "--password", "pw"])
    args = cfg._parse_args()
    assert args.password == "pw"


def test_main_invokes_configure(monkeypatch):
    monkeypatch.setattr(cfg, "_parse_args", lambda: SimpleNamespace(password="pw"))
    called = {}
    def fake_configure(master_password=None):
        called["pw"] = master_password
    monkeypatch.setattr(cfg, "configure", fake_configure)
    cfg.main()
    assert called["pw"] == "pw"
