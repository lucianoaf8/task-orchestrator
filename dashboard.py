#!/usr/bin/env python3
"""Dashboard entry point for the Task Python Orchestrator.

This script starts the web dashboard interface.
"""

from orchestrator.web.app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(host='localhost', port=5000, debug=True)