"""Service layer package initialisation.

Provides dependency-injection helpers to obtain *singleton* service
instances throughout the application.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from orchestrator.core.config_manager import ConfigManager

from .scheduling_service import SchedulingService
from .task_service import TaskService
from .notification_service import NotificationService

__all__ = [
    "get_task_service",
    "get_scheduling_service",
    "get_notification_service",
]


@lru_cache(maxsize=1)
def get_scheduling_service() -> SchedulingService:  # noqa: D401
    return SchedulingService()


@lru_cache(maxsize=1)
def get_task_service() -> TaskService:  # noqa: D401
    return TaskService(config_manager=ConfigManager(), scheduling_service=get_scheduling_service())


@lru_cache(maxsize=1)
def get_notification_service() -> NotificationService:  # noqa: D401
    return NotificationService()
