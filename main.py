#!/usr/bin/env python3
"""
Main entry point for Task Python Orchestrator
Manages tasks via CLI or GUI, triggers scheduling via orc.py
"""

import sys
import subprocess
import logging
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def trigger_orc_scheduling(task_name: str) -> bool:
    """
    Trigger orc.py to schedule a task after creation/edit
    This is the key integration point from the documented flow
    """
    try:
        result = subprocess.run([
            sys.executable, 'orc.py', '--schedule', task_name
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            print(f"✓ Task '{task_name}' scheduled successfully")
            return True
        else:
            print(f"✗ Failed to schedule task '{task_name}': {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error calling orc.py for task '{task_name}': {e}")
        return False

def show_dashboard():
    """Launch web dashboard"""
    try:
        from orchestrator.web.dashboard import main as dashboard_main
        print("Starting web dashboard...")
        dashboard_main()
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        return False

def show_status():
    """Show current system status"""
    print("=== Orchestrator Status ===")
    
    # Show configured tasks
    try:
        from orchestrator.core.config_manager import ConfigManager
        config_manager = ConfigManager()
        tasks = config_manager.get_all_tasks()
        print(f"Configured tasks: {len(tasks)}")
        for name, task in tasks.items():
            status = "enabled" if task.get('enabled', True) else "disabled"
            print(f"  - {name} ({task.get('type', 'unknown')}): {status}")
    except Exception as e:
        print(f"Error reading task configuration: {e}")
    
    # Show scheduled tasks via orc.py
    print("\nWindows Scheduled Tasks:")
    try:
        result = subprocess.run([
            sys.executable, 'orc.py', '--list'
        ], capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error listing scheduled tasks: {result.stderr}")
    except Exception as e:
        print(f"Error calling orc.py --list: {e}")

def interactive_mode():
    """Interactive task management mode"""
    from orchestrator.core.config_manager import ConfigManager
    
    config_manager = ConfigManager()
    
    while True:
        print("\n=== Task Orchestrator ===")
        print("1. View tasks")
        print("2. Add task")
        print("3. Edit task")
        print("4. Delete task")
        print("5. Show status")
        print("6. Launch dashboard")
        print("7. Exit")
        
        choice = input("\nEnter choice (1-7): ").strip()
        
        if choice == '1':
            # View tasks
            tasks = config_manager.get_all_tasks()
            if not tasks:
                print("No tasks configured.")
            else:
                print("\nConfigured Tasks:")
                for name, task in tasks.items():
                    status = "enabled" if task.get('enabled', True) else "disabled"
                    schedule = task.get('schedule', 'manual')
                    print(f"  {name}: {task['type']} | {schedule} | {status}")
        
        elif choice == '2':
            # Add task
            print("\n--- Add New Task ---")
            name = input("Task name: ").strip()
            if not name:
                print("Task name required.")
                continue
            
            task_type = input("Task type (data_job/condition/report/maintenance): ").strip()
            command = input("Command to execute: ").strip()
            schedule = input("Cron schedule (leave empty for manual): ").strip()
            
            if not command:
                print("Command is required.")
                continue
            
            try:
                config_manager.add_task(
                    name=name,
                    task_type=task_type or 'data_job',
                    command=command,
                    schedule=schedule if schedule else None,
                    enabled=True
                )
                print(f"✓ Task '{name}' saved to database")
                
                # Trigger scheduling via orc.py (KEY INTEGRATION POINT)
                if schedule:
                    trigger_orc_scheduling(name)
                
            except Exception as e:
                print(f"Error saving task: {e}")
        
        elif choice == '3':
            # Edit task
            name = input("Task name to edit: ").strip()
            task = config_manager.get_task(name)
            if not task:
                print(f"Task '{name}' not found.")
                continue
            
            print(f"\nCurrent task '{name}':")
            print(f"  Type: {task['type']}")
            print(f"  Command: {task['command']}")
            print(f"  Schedule: {task.get('schedule', 'manual')}")
            
            new_command = input(f"New command (current: {task['command']}): ").strip()
            new_schedule = input(f"New schedule (current: {task.get('schedule', 'manual')}): ").strip()
            
            # Update task
            task['command'] = new_command if new_command else task['command']
            task['schedule'] = new_schedule if new_schedule else task.get('schedule')
            
            try:
                config_manager.add_task(**task)
                print(f"✓ Task '{name}' updated")
                
                # Re-schedule if has schedule
                if task.get('schedule'):
                    trigger_orc_scheduling(name)
                    
            except Exception as e:
                print(f"Error updating task: {e}")
        
        elif choice == '4':
            # Delete task
            name = input("Task name to delete: ").strip()
            task = config_manager.get_task(name)
            if not task:
                print(f"Task '{name}' not found.")
                continue
            
            confirm = input(f"Delete task '{name}'? (y/N): ").strip().lower()
            if confirm == 'y':
                try:
                    # Unschedule first
                    subprocess.run([
                        sys.executable, 'orc.py', '--unschedule', name
                    ], capture_output=True, text=True, cwd=PROJECT_ROOT)
                    
                    # Disable in database
                    task['enabled'] = False
                    config_manager.add_task(**task)
                    print(f"✓ Task '{name}' deleted and unscheduled")
                    
                except Exception as e:
                    print(f"Error deleting task: {e}")
        
        elif choice == '5':
            show_status()
        
        elif choice == '6':
            show_dashboard()
            break
        
        elif choice == '7':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main entry point following documented flow"""
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == 'dashboard':
            show_dashboard()
        elif sys.argv[1] == 'status':
            show_status()
        elif sys.argv[1] == 'cli':
            # Delegate to existing CLI for advanced operations
            # Trim the 'cli' token before delegating so orchestrator.cli parser
            # receives arguments as if invoked directly.
            from orchestrator.cli import cli_main

            original_argv = sys.argv.copy()
            try:
                sys.argv = [sys.argv[0]] + sys.argv[2:]
                cli_main()
            finally:
                # Restore argv to avoid side-effects when main() returns
                sys.argv = original_argv
        else:
            print("Usage: python main.py [dashboard|status|cli]")
            print("  dashboard - Launch web interface")
            print("  status    - Show system status")
            print("  cli       - Advanced CLI operations")
            print("  (no args) - Interactive mode")
    else:
        # Interactive mode as primary interface
        interactive_mode()

if __name__ == "__main__":
    main()