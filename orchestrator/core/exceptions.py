"""Unified error hierarchy for Orchestrator components."""
from __future__ import annotations

from typing import Any, Dict, Optional

__all__ = [
    "OrchestratorError",
    "ValidationError",
    "ConfigurationError",
    "SchedulingError",
]


class OrchestratorError(Exception):
    """Base-class for *all* orchestrator specific exceptions."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context: Dict[str, Any] = context or {}

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.error_code or 'ERR'}: {self.message}"


class ValidationError(OrchestratorError):
    """User input or configuration did not pass validation."""


class ConfigurationError(OrchestratorError):
    """Raised when critical configuration is missing or invalid."""


class SchedulingError(OrchestratorError):
    """Windows Task Scheduler related failure."""
