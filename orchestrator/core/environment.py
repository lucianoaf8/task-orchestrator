"""Environment variable helpers used by the Orchestrator."""
from __future__ import annotations

import os
from typing import Any, Optional

from .config_schema import CONFIG_SCHEMA
from .config_manager import ConfigManager


def _get_expected_type(section: str, key: str):  # pragma: no cover
    if section in CONFIG_SCHEMA and key in CONFIG_SCHEMA[section]:
        return CONFIG_SCHEMA[section][key].get("type")
    return str  # default to string if unknown


def validate_and_convert(value: str, expected_type):  # pragma: no cover
    if expected_type is int:
        return int(value)
    if expected_type is bool:
        return value.lower() in {"1", "true", "yes"}
    return value


def get_config_with_env_override(config_mgr: ConfigManager, section: str, key: str, default: Optional[Any] = None):
    """Return configuration value with *env* override precedence.

    Order: ENV > config > default
    """
    env_key = f"ORC_{section.upper()}_{key.upper()}"
    env_value = os.getenv(env_key)
    if env_value is not None:
        expected_type = _get_expected_type(section, key)
        return validate_and_convert(env_value, expected_type)

    return config_mgr.get_config(section, key, default)
