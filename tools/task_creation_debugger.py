#!/usr/bin/env python3
"""
Task Creation Debugger - Diagnose Windows Task Scheduler issues
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

def run_command(cmd, description):
    """Run command and display results"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {' '.join(cmd)}")
    print('-'*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        
        print(f"Exit Code: {result.returncode}")
        
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def check_admin_rights():
    """Check if running with admin rights"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    print("=== TASK CREATION DEBUGGER ===")
    print(f"Time: {datetime.now()}")
    print(f"Python: {sys.executable}")
    print(f"Working Dir: {os.getcwd()}")
    print(f"Admin Rights: {check_admin_rights()}")
    
    # Test 1: Basic schtasks availability
    run_command(
        ["schtasks", "/?"],
        "Check if schtasks is available"
    )
    
    # Test 2: List all tasks (no filter)
    run_command(
        ["schtasks", "/Query", "/FO", "LIST"],
        "List all tasks (LIST format)"
    )
    
    # Test 3: Query Orchestrator folder
    run_command(
        ["schtasks", "/Query", "/TN", "\\Orchestrator\\*"],
        "Query Orchestrator folder with wildcard"
    )
    
    # Test 4: Create a simple test task
    test_task_name = f"\\Orchestrator\\Orc_debug_test_{datetime.now().strftime('%H%M%S')}"
    create_success = run_command(
        [
            "schtasks", "/Create",
            "/TN", test_task_name,
            "/TR", "cmd /c echo test",
            "/SC", "ONCE",
            "/ST", "00:00",
            "/F"
        ],
        f"Create test task: {test_task_name}"
    )
    
    if create_success:
        # Test 5: Query the created task
        run_command(
            ["schtasks", "/Query", "/TN", test_task_name, "/FO", "LIST"],
            "Query created test task"
        )
        
        # Test 6: Delete test task
        run_command(
            ["schtasks", "/Delete", "/TN", test_task_name, "/F"],
            "Delete test task"
        )
    
    # Test 7: Check Python path
    project_root = Path(__file__).parent
    orc_py = project_root / "orc.py"
    print(f"\n{'='*60}")
    print(f"PROJECT PATHS:")
    print(f"Project Root: {project_root}")
    print(f"orc.py exists: {orc_py.exists()}")
    print(f"orc.py path: {orc_py}")
    
    # Test 8: Test actual command that would be used
    if orc_py.exists():
        test_cmd = f'"{sys.executable}" "{orc_py}" --task test_task'
        print(f"\nTest command: {test_cmd}")
        
        # Try to create with actual command
        run_command(
            [
                "schtasks", "/Create",
                "/TN", "\\Orchestrator\\Orc_real_test",
                "/TR", test_cmd,
                "/SC", "DAILY",
                "/ST", "06:00",
                "/F"
            ],
            "Create task with real orc.py command"
        )
        
        # Clean up
        run_command(
            ["schtasks", "/Delete", "/TN", "\\Orchestrator\\Orc_real_test", "/F"],
            "Clean up real test task"
        )

if __name__ == "__main__":
    main()