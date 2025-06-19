"""Legacy compatibility shims.

This package was re-introduced during Phase-2 validation solely to satisfy
imports that remain in the codebase (`TaskScheduler.execute_task` et al.) while
the new execution layer is still under development.

It provides a minimal `TaskManager` implementation that executes a task's
configured command via *subprocess* and returns a proper
`orchestrator.core.task_result.TaskResult` so that existing flow validation
scripts succeed.

Once the new core execution engine fully replaces the legacy path, this module
can be deleted.
"""

from __future__ import annotations

from importlib import import_module

from .task_manager import TaskManager  # noqa: F401 – re-export for external use

__all__: list[str] = [
    "TaskManager",
]
