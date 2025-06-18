"""Daily Salesforce summary email task.

This script queries Salesforce for daily metrics (placeholder implementation)
and emails a summary to recipients configured in the orchestrator database.

Credentials must be stored securely via ``ConfigManager.store_credential`` and
referenced by *credential name* only; no secret values appear in plaintext.

Environment variables that override configuration values will be read if set.

Exit codes:
0 – success
1 – failure (exception or non-200 HTTP response)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from smtplib import SMTP
from typing import Any, Dict

import requests
from requests.exceptions import RequestException

# Add project root to PYTHONPATH when executed directly via ``python scripts/...``
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from orchestrator.core.config_manager import ConfigManager  # noqa: E402


def get_config_value(cm: ConfigManager, section: str, key: str, *, default: str | None = None) -> str | None:
    """Return orchestrator config value with env-var override."""
    env_key = f"{section.upper()}_{key.upper()}"
    return os.getenv(env_key) or cm.get_config(section, key, default)


def fetch_salesforce_data(cm: ConfigManager) -> Dict[str, Any]:
    """Fetch data from Salesforce REST API.

    *This is a placeholder implementation.* Adjust the SOQL query or REST
    endpoint as needed. Assumes that a credential named ``sf_access_token`` is
    stored via :py:meth:`ConfigManager.store_credential`.
    """
    instance_url = get_config_value(cm, "salesforce", "instance_url")
    access_token = cm.get_credential("sf_access_token")
    if not instance_url or not access_token:
        raise RuntimeError("Salesforce instance URL or access token missing; store them via ConfigManager.")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Example: SOQL query for Opportunity totals – replace with real query.
    soql = "SELECT COUNT(Id) total FROM Opportunity WHERE CloseDate = TODAY"
    url = f"{instance_url}/services/data/v59.0/query?q={requests.utils.quote(soql)}"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
    except RequestException as exc:
        raise RuntimeError(f"Salesforce API request failed: {exc}") from exc

    return resp.json()


def build_email_body(sf_data: Dict[str, Any]) -> str:
    """Return a plain-text email body given Salesforce data."""
    total = sf_data.get("records", [{}])[0].get("total", "N/A")
    today_str = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    return (
        f"Salesforce Daily Report – {today_str}\n"
        f"===================================\n\n"
        f"Opportunities created today: {total}\n\n"
        "(Add more metrics here as needed.)\n"
    )


def send_email(cm: ConfigManager, body: str) -> None:
    """Send email using SMTP credentials stored in orchestrator config."""
    smtp_server = get_config_value(cm, "email", "smtp_server", default="smtp.office365.com")
    smtp_port = int(get_config_value(cm, "email", "smtp_port", default="587"))
    sender_email = cm.get_credential("email_username")
    password = cm.get_credential("email_password")
    recipients_json = get_config_value(cm, "email", "recipients", default="[]")
    recipients = json.loads(recipients_json) if recipients_json else []

    if not all([sender_email, password, recipients]):
        raise RuntimeError("Incomplete email configuration; ensure username, password and recipients are set.")

    msg = MIMEText(body)
    msg["Subject"] = "Salesforce Daily Report"
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)

    with SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)


# --------------------------- CLI entry -------------------------------------

if __name__ == "__main__":
    SCRIPT = os.path.abspath(sys.argv[0])
    try:
        cm = ConfigManager()
        sf_data = fetch_salesforce_data(cm)
        email_body = build_email_body(sf_data)
        send_email(cm, email_body)
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001  # Allow broad catch for CLI exit code
        # Avoid printing secrets – only generic message.
        sys.stderr.write(f"[ERROR] {SCRIPT}: {exc}\n")
        sys.exit(1)
