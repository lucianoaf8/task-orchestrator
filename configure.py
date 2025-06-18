"""Configure the orchestrator.

This module provides a command-line interface (CLI) that allows users to
initialise or update the application configuration stored in the SQLite
database.  Credentials are handled securely through `ConfigManager`, and no
secrets are persisted in plain text.
"""

from __future__ import annotations

import argparse
import getpass
from typing import Optional

from orchestrator.core.config_manager import ConfigManager


def configure(master_password: Optional[str] | None = None) -> ConfigManager:  # noqa: D401
    """Run the interactive configuration wizard.

    Args:
        master_password: Optional master password used to derive the symmetric
            key for credential encryption. If *None*, the user is prompted for
            a password via the terminal.

    Returns:
        ConfigManager: An instance connected to the backing SQLite database.
    """

    if master_password is None:
        master_password = getpass.getpass("Master password: ")

    config = ConfigManager(master_password=master_password)

    # Interactive configuration steps would go here – keep it minimal for now.
    print("Configure e-mail settings, VPN checks, etc. (not yet implemented)")

    return config


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments using :pymod:`argparse`."""

    parser = argparse.ArgumentParser(
        description="Interactive configuration utility for the task orchestrator.",
    )
    parser.add_argument(
        "--password",
        "-p",
        dest="password",
        help="Master password to use instead of prompting interactively.",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    return parser.parse_args()


def main() -> None:
    """Entry-point wrapper that translates CLI args to :func:`configure`."""

    args = _parse_args()
    configure(master_password=args.password)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Graceful exit on Ctrl-C.
        print("\nConfiguration aborted by user.")
        raise SystemExit(130)