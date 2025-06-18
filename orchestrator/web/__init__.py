"""Web interface for the orchestrator."""

from .app import create_app
from .dashboard import main as dashboard_main  # relocated dashboard entrypoint

__all__ = ['create_app', 'dashboard_main']