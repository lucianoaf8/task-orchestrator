#!/usr/bin/env python3
"""
Orchestrator Entry Point (orc.py)
Handles both task scheduling and task execution as documented in project-flow.md
"""

import sys
import argparse
import logging
import os
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.core.scheduler import TaskScheduler
from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.task_result import TaskResult

def setup_logging():
    """Setup logging for orc.py operations"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/orc.log') if os.path.exists('logs') else logging.NullHandler()
        ]
    )
    return logging.getLogger(__name__)

def schedule_task_operation(task_name: str, logger: logging.Logger) -> bool:
    """Handle --schedule task_name operation"""
    logger.info(f"Scheduling task: {task_name}")
    
    try:
        scheduler = TaskScheduler()
        
        # Validate task exists and has required configuration
        task_config = scheduler.config_manager.get_task(task_name)
        if not task_config:
            logger.error(f"Task {task_name} not found in database")
            return False
        
        # Validate task configuration
        is_valid, validation_msg = scheduler.validate_task_config(task_name)
        if not is_valid:
            logger.error(f"Task {task_name} validation failed: {validation_msg}")
            return False
        
        # Schedule in Windows Task Scheduler
        success = scheduler.schedule_task(task_name)
        if success:
            logger.info(f"Task {task_name} successfully scheduled in Windows Task Scheduler")
        else:
            logger.error(f"Failed to schedule task {task_name} in Windows Task Scheduler")
        
        return success
        
    except Exception as e:
        logger.error(f"Error scheduling task {task_name}: {e}")
        return False

def execute_task_operation(task_name: str, logger: logging.Logger) -> bool:
    """Handle --task task_name operation (called by Windows Task Scheduler)"""
    logger.info(f"Executing task: {task_name}")
    
    try:
        scheduler = TaskScheduler()
        
        # Execute task with full lifecycle
        result = scheduler.execute_task(task_name)
        
        # Log result
        logger.info(f"Task {task_name} completed with status: {result.status}")
        if result.status == "FAILED":
            logger.error(f"Task {task_name} error: {result.error}")
        
        # Return success/failure for Windows Task Scheduler
        return result.status == "SUCCESS"
        
    except Exception as e:
        logger.error(f"Error executing task {task_name}: {e}")
        return False

def list_tasks_operation(logger: logging.Logger) -> bool:
    """Handle --list operation"""
    try:
        scheduler = TaskScheduler()
        scheduled_tasks = scheduler.list_scheduled_tasks()
        
        if not scheduled_tasks:
            print("No tasks currently scheduled in Windows Task Scheduler")
        else:
            print("Scheduled Tasks:")
            print("-" * 50)
            for task in scheduled_tasks:
                task_name = task.get('TaskName', 'Unknown').replace('\\Orchestrator\\Orc_', '')
                status = task.get('Status', 'Unknown')
                print(f"  {task_name}: {status}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return False

def unschedule_task_operation(task_name: str, logger: logging.Logger) -> bool:
    """Handle --unschedule task_name operation"""
    logger.info(f"Unscheduling task: {task_name}")
    
    try:
        scheduler = TaskScheduler()
        success = scheduler.unschedule_task(task_name)
        
        if success:
            logger.info(f"Task {task_name} successfully unscheduled")
        else:
            logger.error(f"Failed to unschedule task {task_name}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error unscheduling task {task_name}: {e}")
        return False

def main():
    """Main entry point for orc.py"""
    parser = argparse.ArgumentParser(
        description='Orchestrator Entry Point - Scheduling and Execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python orc.py --schedule my_task     # Schedule task in Windows Task Scheduler
  python orc.py --task my_task         # Execute task (called by Windows)
  python orc.py --list                 # List all scheduled tasks
  python orc.py --unschedule my_task   # Remove task from Windows scheduler
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--schedule', metavar='TASK_NAME', 
                      help='Schedule specified task in Windows Task Scheduler')
    group.add_argument('--task', metavar='TASK_NAME',
                      help='Execute specified task (called by Windows Task Scheduler)')
    group.add_argument('--list', action='store_true',
                      help='List all scheduled tasks')
    group.add_argument('--unschedule', metavar='TASK_NAME',
                      help='Remove task from Windows Task Scheduler')
    
    args = parser.parse_args()
    logger = setup_logging()
    
    # Route to appropriate operation
    if args.schedule:
        success = schedule_task_operation(args.schedule, logger)
    elif args.task:
        success = execute_task_operation(args.task, logger)
    elif args.list:
        success = list_tasks_operation(logger)
    elif args.unschedule:
        success = unschedule_task_operation(args.unschedule, logger)
    else:
        parser.print_help()
        sys.exit(1)
    
    # Exit with appropriate code for Windows Task Scheduler
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()