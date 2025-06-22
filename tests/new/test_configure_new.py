import sys
from unittest import mock
import pytest

import orchestrator.utils.configure as cfg


def test_configure_interactive(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, 'ConfigManager', lambda master_password=None: 'CM')
    monkeypatch.setattr(cfg.getpass, 'getpass', lambda prompt: 'pw')
    assert cfg.configure() == 'CM'


def test_parse_args(monkeypatch):
    monkeypatch.setattr('sys.argv', ['cfg', '-p', 'x'])
    ns = cfg._parse_args()
    assert ns.password == 'x'


def test_main(monkeypatch):
    m_cfg = mock.Mock()
    monkeypatch.setattr(cfg, 'configure', m_cfg)
    monkeypatch.setattr(cfg, '_parse_args', lambda: mock.Mock(password='pw'))
    cfg.main()
    m_cfg.assert_called_once_with(master_password='pw')
