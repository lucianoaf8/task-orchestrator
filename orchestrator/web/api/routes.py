"""Flask blueprint exposing JSON API for orchestrator (Phase 4)."""
from __future__ import annotations

from typing import Any, Optional

from flask import Blueprint, jsonify, request

from orchestrator.core.scheduler import TaskScheduler
from orchestrator.utils.cron_converter import CronConverter

__all__ = ["api_bp"]

api_bp = Blueprint("api", __name__, url_prefix="/api")

# A *singleton* scheduler used by the API routes. In a real production
# setup we might use a factory or dependency-injection, but this keeps the
# dashboard simple.
SCHEDULER = TaskScheduler()
CM = SCHEDULER.config_manager


# --------------------------------------------------------------------------
# Utility helpers
# --------------------------------------------------------------------------

def _json(data: Any, status: int = 200):  # noqa: D401
    """Return *data* as Flask JSON with a status code."""

    return jsonify(data), status


def _success(data: Any | None = None):  # noqa: D401
    """Wrap *data* in a standard success envelope."""

    payload: dict[str, Any] = {"status": "success"}
    if data is not None:
        if isinstance(data, dict):
            payload.update(data)
        else:
            payload["data"] = data
    return _json(payload)


def _validate_cron(expr: str) -> Optional[str]:  # noqa: D401
    ok, msg = CronConverter.validate_cron_expression(expr)
    return None if ok else msg


# --------------------------------------------------------------------------
# Health & metadata
# --------------------------------------------------------------------------


@api_bp.get("/health")
def health() -> tuple[Any, int]:  # noqa: D401
    try:
        tasks = CM.get_all_tasks()
        return _json({
            "status": "healthy",
            "tasks_configured": len(tasks),
            "database": "connected",
        })
    except Exception as exc:  # pragma: no cover – defensive
        return _json({"status": "unhealthy", "error": str(exc)}, 500)


# --------------------------------------------------------------------------
# Task definitions (ConfigManager)
# --------------------------------------------------------------------------


@api_bp.get("/tasks")
def list_tasks():  # noqa: D401
    tasks = CM.get_all_tasks()
    for name, cfg in tasks.items():
        history = CM.get_task_history(name, 1)
        cfg["last_execution"] = history[0] if history else None
    return _success({"tasks": tasks})


@api_bp.post("/tasks")
def add_or_update_task():  # noqa: D401
    data = request.get_json(force=True)
    required = {"name", "type", "command"}
    missing = required - data.keys()
    if missing:
        return _json({"error": f"Missing fields: {', '.join(missing)}"}, 400)

    if (cron := data.get("schedule")) and (err := _validate_cron(cron)):
        return _json({"error": f"Invalid cron: {err}"}, 400)

    CM.add_task(
        name=data["name"],
        task_type=data["type"],
        command=data["command"],
        schedule=data.get("schedule"),
        timeout=data.get("timeout", 3600),
        retry_count=data.get("retry_count", 0),
        retry_delay=data.get("retry_delay", 300),
        dependencies=data.get("dependencies", []),
        enabled=data.get("enabled", True),
    )
    scheduled_now = False
    if data.get("enabled", True):
        scheduled_now = SCHEDULER.schedule_task(data["name"])
    return _success({"message": f"Task {data['name']} saved", "scheduled": scheduled_now})


@api_bp.delete("/tasks/<task_name>")
def disable_task(task_name: str):  # noqa: D401
    task = CM.get_task(task_name)
    if not task:
        return _json({"error": "Task not found"}, 404)
    task["enabled"] = False
    CM.add_task(**task)  # type: ignore[arg-type]
    return _success({"message": f"Task {task_name} disabled"})


@api_bp.get("/tasks/<task_name>/history")
def task_history(task_name: str):  # noqa: D401
    limit = request.args.get("limit", 50, type=int)
    history = CM.get_task_history(task_name, limit)
    return _success({"task_name": task_name, "history": history})


# --------------------------------------------------------------------------
# Scheduling operations (Windows Task Scheduler)
# --------------------------------------------------------------------------


@api_bp.post("/tasks/<task_name>/schedule")
def schedule(task_name: str):  # noqa: D401
    ok = SCHEDULER.schedule_task(task_name)
    return _success({"scheduled": ok})


@api_bp.delete("/tasks/<task_name>/unschedule")
def unschedule(task_name: str):  # noqa: D401
    ok = SCHEDULER.unschedule_task(task_name)
    return _success({"unscheduled": ok})


@api_bp.get("/tasks/scheduled")
def list_scheduled():  # noqa: D401
    tasks = SCHEDULER.list_scheduled_tasks()
    return _success({"scheduled_tasks": tasks})


# --------------------------------------------------------------------------
# System / Scheduler status
# --------------------------------------------------------------------------

@api_bp.get("/system/scheduler-status")
def scheduler_status():  # noqa: D401
    """Return summary information about Windows Task Scheduler integration."""
    tasks = SCHEDULER.list_scheduled_tasks()
    return _success({"configured": len(CM.get_all_tasks()), "scheduled": len(tasks), "tasks": tasks})

# --------------------------------------------------------------------------
# Manual execution
# --------------------------------------------------------------------------


@api_bp.post("/tasks/<task_name>/run")
def run_task(task_name: str):  # noqa: D401
    result = SCHEDULER.execute_task(task_name)
    return _success(result.to_dict())
