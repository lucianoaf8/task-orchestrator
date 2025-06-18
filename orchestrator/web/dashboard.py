#!/usr/bin/env python3
"""Dashboard entry point for the Task Python Orchestrator.

This script starts the web dashboard interface.
"""

from orchestrator.web.app import create_app


def main(host: str = "localhost", port: int = 5000, debug: bool = True):
    """Launch the Flask dashboard.

    Provides an entry point that can be imported (`orchestrator.web.dashboard.main`).
    """

    app = create_app()
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main()