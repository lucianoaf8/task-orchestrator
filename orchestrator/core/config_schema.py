"""Declarative configuration *schema* used by :class:`ConfigManager`.

The schema is intentionally small for the MVP.  Additional sections /
keys can be added incrementally as new features land.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Tuple, Union

Validator = Callable[[Any], Any]
SchemaEntry = Dict[str, Union[type, bool, Tuple[int, int], Validator]]


def _validate_email_list(value: Any) -> Any:  # pragma: no cover – trivial
    if not isinstance(value, list):
        raise ValueError("Expected list of email addresses")
    # *Very* light-weight validation – ensure contains '@'
    for addr in value:
        if "@" not in addr:
            raise ValueError(f"Invalid email: {addr}")
    return value


CONFIG_SCHEMA: Dict[str, Dict[str, Dict[str, Any]]] = {
    "email": {
        "smtp_server": {"type": str, "required": True},
        "smtp_port": {"type": int, "range": (1, 65535), "required": True},
        "recipients": {"type": list, "validator": _validate_email_list},
    }
}
