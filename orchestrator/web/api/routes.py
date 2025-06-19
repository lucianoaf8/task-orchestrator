import subprocess
import sys
import os
from pathlib import Path
from flask import Blueprint, request, jsonify
from orchestrator.core.config_manager import ConfigManager
from croniter import croniter

# Create API blueprint and utility helpers
api_bp = Blueprint("api", __name__, url_prefix="/api")
CM = ConfigManager()


def _json(payload: dict, status: int = 200):
    """Return JSON response with given status."""
    return jsonify(payload), status


def _success(payload: dict, status: int = 200):
    """Standard success wrapper (adds status key)."""
    payload.setdefault("status", "success")
    return _json(payload, status)


def _validate_cron(cron_expr: str):
    """Validate cron expression; return None if valid else error str."""
    try:
        croniter(cron_expr)
        return None
    except Exception as exc:
        return str(exc)


# Add this helper function at the top of the file
def call_orc_py(operation: str, task_name: str = None) -> tuple[bool, str]:
    """
    Call orc.py subprocess and return (success, message)
    This aligns with the documented flow where web API triggers orc.py
    """
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        cmd = [sys.executable, 'orc.py']
        
        if operation == 'schedule' and task_name:
            cmd.extend(['--schedule', task_name])
        elif operation == 'unschedule' and task_name:
            cmd.extend(['--unschedule', task_name])
        elif operation == 'list':
            cmd.append('--list')
        else:
            return False, f"Invalid operation: {operation}"
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        
        return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
        
    except Exception as e:
        return False, str(e)

# Update the existing add_or_update_task function
@api_bp.post("/tasks")
def add_or_update_task():
    """Create or update task and immediately schedule it via orc.py"""
    data = request.get_json(force=True)
    required = {"name", "type", "command"}
    missing = required - data.keys()
    if missing:
        return _json({"error": f"Missing fields: {', '.join(missing)}"}, 400)

    if (cron := data.get("schedule")) and (err := _validate_cron(cron)):
        return _json({"error": f"Invalid cron: {err}"}, 400)

    # Save to database
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
    
    # Schedule via orc.py if enabled and has schedule
    scheduled_now = False
    schedule_message = ""
    if data.get("enabled", True) and data.get("schedule"):
        scheduled_now, schedule_message = call_orc_py('schedule', data["name"])
    
    return _success({
        "message": f"Task {data['name']} saved", 
        "scheduled": scheduled_now,
        "schedule_details": schedule_message
    })

# Update scheduling endpoints
@api_bp.post("/tasks/<task_name>/schedule")
def schedule(task_name: str):
    """Schedule task via orc.py"""
    success, message = call_orc_py('schedule', task_name)
    return _success({"scheduled": success, "message": message})

@api_bp.delete("/tasks/<task_name>/unschedule")
def unschedule(task_name: str):
    """Unschedule task via orc.py"""
    success, message = call_orc_py('unschedule', task_name)
    return _success({"unscheduled": success, "message": message})

@api_bp.get("/tasks/scheduled")
def list_scheduled():
    """List scheduled tasks via orc.py"""
    success, output = call_orc_py('list')
    if success:
        # Parse orc.py output into structured data
        lines = output.strip().split('\n')
        tasks = []
        for line in lines:
            if ':' in line and not line.startswith('Scheduled Tasks:') and not line.startswith('-'):
                parts = line.strip().split(':')
                if len(parts) >= 2:
                    task_name = parts[0].strip()
                    status = parts[1].strip()
                    tasks.append({"TaskName": task_name, "Status": status})
        
        return _success({"scheduled_tasks": tasks})
    else:
        return _json({"error": f"Failed to list tasks: {output}"}, 500)