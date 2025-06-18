"""Script to verify a working database connection.

This script is intended to be executed by the orchestrator as a *condition* task
before other jobs that rely on a live database connection.  It will:

1. Attempt to create an SQLAlchemy engine from environment variables
   (``DB_SERVER``, ``DB_PORT``, ``DB_NAME``, ``DB_USER``, ``DB_PASSWORD``).
2. Try to connect using that engine.  If successful it exits with status ``0``.
3. If the connection fails it will attempt to invoke an auxiliary VPN script
   (path can be customised via ``VPN_CONNECT_SCRIPT`` env var, defaulting to
   ``C:\\Projects\\python_scripts\\_root\\utils\\vpn_connect.py``) up to
   **five** times, re-checking the DB connection after each attempt.
4. If the connection still cannot be established the script logs an error via
   ``send_error_log`` (a best-effort helper that writes to stderr) and exits
   with status ``1``.

The helper follows the security rules – no plaintext credentials are printed.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

# Ensure project root (two directories up) is on PYTHONPATH so that local
# execution via `python scripts/...` can import project modules.
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from orchestrator.core.config_manager import ConfigManager  # noqa: E402

# ------------------------- Helpers -----------------------------------------

def send_error_log(script: str, message: str) -> None:  # pragma: no cover
    """Best-effort error logger.

    For now this just prints to *stderr*.  In production you might e-mail or
    push this to a monitoring system.
    """
    sys.stderr.write(f"[ERROR] {script}: {message}\n")
    sys.stderr.flush()


def check_db_connection(engine: Engine) -> bool:
    """Return ``True`` if *engine* can connect, ``False`` otherwise."""
    try:
        with engine.connect():
            return True
    except Exception:  # noqa: BLE001  # Specific DB exceptions vary per driver
        return False


def get_db_engine(script_path: str) -> Engine:
    """Return a live SQLAlchemy *Engine* or raise ``ConnectionError``.

    The connection parameters are taken from environment variables as
    documented in the module docstring.  If a direct connection is not
    possible the function will run a VPN helper up to five times and retry.
    """
    try:
        master_password = os.getenv('ORCH_MASTER_PASSWORD') or os.getenv('MASTER_PASSWORD')
        cm = ConfigManager(master_password=master_password)

        if cm is None:
            raise ValueError("ConfigManager is not available.")

        def param(name: str, cred: bool = False, default: str | None = None):
            # Order of precedence: env var -> encrypted credential/config -> default
            val = os.getenv(name)
            if val:
                return val
            if cred:
                return cm.get_credential(name.lower()) or default
            return cm.get_config('db', name.lower(), default)

        server = param('DB_SERVER')
        port = int(param('DB_PORT', default='3306')) if param('DB_PORT') else 3306
        database = param('DB_NAME')
        user = param('DB_USER', cred=True)
        password = quote_plus(param('DB_PASSWORD', cred=True, default=''))

        if not all([server, port, database, user, password]):
            raise ValueError("Database connection parameters are not configured.\n"
                         "Set env vars or save them via ConfigManager.")

        dsn = f"mysql+mysqlconnector://{user}:{password}@{server}:{port}/{database}"
        engine = create_engine(dsn, pool_pre_ping=True, pool_recycle=3600)

        if check_db_connection(engine):
            print("Database connection successful.")
            return engine

        # Attempt VPN connection retries
        vpn_script = os.getenv(
            "VPN_CONNECT_SCRIPT", r"C:\\Projects\\python_scripts\\_root\\utils\\vpn_connect.py"
        )

        for attempt in range(5):
            print(f"DB connection failed. Running VPN script (Attempt {attempt + 1}/5)...")
            try:
                subprocess.run([sys.executable, vpn_script], check=False, text=True)
            except FileNotFoundError:
                print(f"VPN connect script not found at {vpn_script}")

            if check_db_connection(engine):
                print("DB connection successful after VPN attempt.")
                return engine

        raise ConnectionError("Unable to establish DB connection after 5 VPN retries.")

    except Exception as exc:
        send_error_log(script_path, str(exc))
        raise  # Let caller decide whether to exit


# --------------------------- CLI entry -------------------------------------

if __name__ == "__main__":
    SCRIPT = os.path.abspath(sys.argv[0])
    try:
        eng = get_db_engine(SCRIPT)
        # Successful connection – dispose the engine cleanly
        eng.dispose()
        sys.exit(0)
    except Exception:
        sys.exit(1)
