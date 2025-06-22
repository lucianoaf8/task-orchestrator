"""Stub notification service – e-mails / Slack will be implemented later."""
from __future__ import annotations

import logging
from typing import Any, Dict

__all__ = ["NotificationService"]


class NotificationService:  # noqa: R0903
    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)

    def send(self, channel: str, message: str, *, context: Dict[str, Any] | None = None) -> None:  # noqa: D401
        self._log.info("[NOTIFY:%s] %s – %s", channel, message, context)
