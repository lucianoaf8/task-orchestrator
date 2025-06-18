"""Utility functions and helpers.

This package exposes helpers from the relocated `configure.py`, now
found at `orchestrator.utils.configure`. Importing
`orchestrator.utils` automatically makes the `configure` module
available for convenience, preserving backward compatibility with
`import configure` usages inside the code-base.
"""

from importlib import import_module as _import_module

# Lazy import to avoid unnecessary overhead if configure is unused
try:
    configure = _import_module(__name__ + ".configure")  # noqa: N812
except ModuleNotFoundError:  # pragma: no cover – theoretical
    configure = None  # type: ignore

from .windows_scheduler import WindowsScheduler  # noqa: F401  (re-export)
from .cron_converter import CronConverter  # noqa: F401

__all__ = [
    "configure",
    "WindowsScheduler",
    "CronConverter",
]