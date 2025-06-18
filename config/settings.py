"""Application configuration settings."""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Database configuration
DATABASE_PATH = PROJECT_ROOT / "data" / "orchestrator.db"

# Logging configuration
LOG_DIRECTORY = PROJECT_ROOT / "logs"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

# Web interface configuration
WEB_HOST = os.getenv("WEB_HOST", "localhost")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
WEB_DEBUG = os.getenv("WEB_DEBUG", "false").lower() == "true"

# Email configuration
DEFAULT_SMTP_SERVER = "smtp.office365.com"
DEFAULT_SMTP_PORT = 587

# Task execution defaults
DEFAULT_TASK_TIMEOUT = 3600  # 1 hour
DEFAULT_RETRY_COUNT = 0
DEFAULT_RETRY_DELAY = 300  # 5 minutes

# Windows Task Scheduler configuration (for future implementation)
TASK_SCHEDULER_FOLDER = "\\Orchestrator\\"
TASK_NAME_PREFIX = "Orch_"