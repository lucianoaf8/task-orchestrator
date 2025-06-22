from unittest.mock import MagicMock
import orchestrator.services.notification_service as ns
from orchestrator.services import get_task_service, get_notification_service


def test_notification_service_send(monkeypatch):
    logger = MagicMock()
    monkeypatch.setattr(ns.logging, 'getLogger', lambda *a, **k: logger)
    service = ns.NotificationService()
    service.send('ch', 'msg', context={'a': 1})
    logger.info.assert_called_once_with('[NOTIFY:%s] %s – %s', 'ch', 'msg', {'a': 1})


def test_singletons_same_instance():
    get_task_service.cache_clear()
    get_notification_service.cache_clear()
    svc1 = get_task_service()
    svc2 = get_task_service()
    notif1 = get_notification_service()
    notif2 = get_notification_service()
    assert svc1 is svc2
    assert notif1 is notif2
