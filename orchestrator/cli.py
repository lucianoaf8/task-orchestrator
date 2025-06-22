"""Command-line interface for Task Python Orchestrator (Phase 3)."""
from __future__ import annotations

import argparse
import os
import getpass
import json
import sys
from typing import Any

from orchestrator.services import get_task_service, get_scheduling_service
from orchestrator.core.scheduler import TaskScheduler

from orchestrator.web.dashboard import main as dashboard_main
from orchestrator.utils.configure import main as configure_main

__all__: list[str] = [
    "cli_main",
    "main",
    "serve",
]

# ---------------------------------------------------------------------------
# Argument-parser helpers (Phase-3 spec)
# ---------------------------------------------------------------------------

def create_parser() -> argparse.ArgumentParser:  # noqa: D401
    """Return a fully-featured *argparse* parser matching the Phase-3 spec."""

    parser = argparse.ArgumentParser(description="Task Python Orchestrator")
    parser.add_argument(
        "--password",
        dest="password",
        help="Master password for encrypted credentials",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Schedule --------------------------------------------------------
    schedule_p = subparsers.add_parser("schedule", help="Task scheduling operations")
    schedule_p.add_argument("--task", help="Schedule specific task")
    schedule_p.add_argument("--all", action="store_true", help="Schedule all enabled tasks")
    schedule_p.add_argument("--list", action="store_true", help="List scheduled tasks")
    schedule_p.add_argument("--validate", metavar="TASK", help="Validate task configuration")

    # --- Unschedule ------------------------------------------------------
    unschedule_p = subparsers.add_parser("unschedule", help="Remove scheduled tasks")
    unschedule_p.add_argument("--task", required=True, help="Unschedule specific task")

    # --- Execute ---------------------------------------------------------
    execute_p = subparsers.add_parser("execute", help="Task execution operations")
    execute_p.add_argument("--task", required=True, help="Execute specific task")
    execute_p.add_argument("--check-deps", action="store_true", help="Only check dependencies")

    # --- Web / dashboard -------------------------------------------------
    subparsers.add_parser("dashboard", help="Start web dashboard")
    subparsers.add_parser("web", help="Start web interface (alias)")

    # --- Configuration ---------------------------------------------------
    subparsers.add_parser("configure", help="Run configuration wizard")

    # --- Migration -------------------------------------------------------
    migrate_p = subparsers.add_parser("migrate", help="Migration operations")
    migrate_p.add_argument("--from-legacy", action="store_true", help="Migrate from legacy loop")
    migrate_p.add_argument("--cleanup", action="store_true", help="Clean up legacy processes")

    return parser


# ---------------------------------------------------------------------------
# Command handlers -----------------------------------------------------------
# ---------------------------------------------------------------------------

def handle_schedule_command(args, scheduler: TaskScheduler) -> int:  # noqa: D401
    # Lazy init to avoid cost when not needed
    task_service = get_task_service()
    scheduling_service = get_scheduling_service()

    if args.list:
        _print_json(scheduling_service.list_tasks())
        return 0

    if args.validate:
        ok, msg = scheduler.validate_task_config(args.validate)
        print("OK" if ok else f"Invalid: {msg}")
        return 0 if ok else 1

    if args.all:
        # Schedule all enabled tasks via ConfigManager data
        result: dict[str, bool] = {}
        for name in task_service.list_tasks().keys():
            try:
                task = task_service.get_task(name)
                ok = scheduling_service.schedule_task(name, task["command"], task["schedule"])
            except Exception:
                ok = False
            result[name] = ok
        _print_json(result)
        return 0

    if args.task:
        task = task_service.get_task(args.task)
        if task is None:
            print("Task not found", file=sys.stderr)
            return 1
        try:
            ok = scheduling_service.schedule_task(args.task, task["command"], task["schedule"])
        except Exception:
            ok = False
        print("Scheduled" if ok else "Failed")
        return 0 if ok else 1

    print("No action specified; use --task/--all/--list/--validate", file=sys.stderr)
    return 1


def handle_unschedule_command(args, scheduler: TaskScheduler) -> int:  # noqa: D401
    scheduling_service = get_scheduling_service()
    ok = scheduling_service.unschedule_task(args.task)
    print("Unscheduled" if ok else "Failed")
    return 0 if ok else 1


def handle_execute_command(args, scheduler: TaskScheduler) -> int:  # noqa: D401
    if args.check_deps:
        ok, msg = scheduler.check_dependencies(args.task)
        print("OK" if ok else f"Failed: {msg}")
        return 0 if ok else 1

    result = scheduler.execute_task(args.task)
    _print_json(result.to_dict())
    return 0 if result.status == "SUCCESS" else 1


def handle_dashboard_command(_args) -> int:  # noqa: D401
    dashboard_main()
    return 0


def handle_configure_command(_args) -> int:  # noqa: D401
    configure_main()
    return 0


def handle_migrate_command(args) -> int:  # noqa: D401
    from tools.migration import migrate_from_legacy, cleanup_legacy  # lazy import

    if args.from_legacy:
        migrate_from_legacy()
    if args.cleanup:
        cleanup_legacy()
    if not (args.from_legacy or args.cleanup):
        print("No migrate action provided", file=sys.stderr)
        return 1
    return 0


def _print_json(data: Any) -> None:  # noqa: D401
    print(json.dumps(data, indent=2, default=str))


def main() -> None:  # noqa: D401
    """Entry point exposed as `orc` console script."""

    cli_main()


def serve() -> None:  # noqa: D401
    """Run the Flask dashboard (exposed as `orc-dashboard`)."""

    from orchestrator.web.app import create_app

    app = create_app()
    # Use env vars if already set, otherwise sensible defaults
    host = os.getenv("ORC_HOST", "0.0.0.0")
    port = int(os.getenv("ORC_PORT", "5000"))
    debug_flag = os.getenv("ORC_DEBUG", "false").lower() in {"1", "true", "yes", "y"}
    app.run(host=host, port=port, debug=debug_flag)


def cli_main() -> None:  # noqa: D401
    """Entry point for orchestrator CLI (Phase-3 spec)."""

    parser = create_parser()

    args = parser.parse_args()

    # Show help when no sub-command supplied
    if args.command is None:
        parser.print_help(sys.stderr)
        raise SystemExit(1)

    scheduler_cmds = {"schedule", "unschedule", "execute"}
    master_password: str | None = args.password

    # Prompt interactively only when scheduler interaction requires it
    if args.command in scheduler_cmds and master_password is None:
        master_password = getpass.getpass("Master password (leave blank if none): ") or None

    scheduler: TaskScheduler | None = None
    if args.command in scheduler_cmds:
        scheduler = TaskScheduler(master_password=master_password)

    # Dispatch to handlers ------------------------------------------------
    if args.command == "schedule":
        exit_code = handle_schedule_command(args, scheduler)  # type: ignore[arg-type]

    elif args.command == "unschedule":
        exit_code = handle_unschedule_command(args, scheduler)  # type: ignore[arg-type]

    elif args.command == "execute":
        exit_code = handle_execute_command(args, scheduler)  # type: ignore[arg-type]

    elif args.command in {"dashboard", "web"}:
        exit_code = handle_dashboard_command(args)

    elif args.command == "configure":
        exit_code = handle_configure_command(args)

    elif args.command == "migrate":
        exit_code = handle_migrate_command(args)

    else:  # pragma: no cover – should be unreachable
        parser.error("Unknown command")
        return  # pragma: no cover – safety

    raise SystemExit(exit_code)



if __name__ == "__main__":  # pragma: no cover
    cli_main()
