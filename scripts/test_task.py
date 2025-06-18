#!/usr/bin/env python3
"""
Simple test script for task simulation.
This script will be executed by the orchestrator during testing.
"""

import os
import sys
import time
import json
from datetime import datetime

def main():
    """Execute a simple test task"""
    
    # Create test output
    start_time = datetime.now()
    
    print(f"[TEST TASK] Started at: {start_time}")
    print(f"[TEST TASK] Python version: {sys.version}")
    print(f"[TEST TASK] Working directory: {os.getcwd()}")
    print(f"[TEST TASK] Script arguments: {sys.argv}")
    
    # Simulate some work
    print("[TEST TASK] Performing test operations...")
    
    # Test file operations
    test_file = "test_output.txt"
    with open(test_file, "w") as f:
        f.write(f"Test execution at {start_time}\n")
        f.write("Task simulation successful\n")
    
    print(f"[TEST TASK] Created test file: {test_file}")
    
    # Test environment variables
    print(f"[TEST TASK] PATH exists: {'PATH' in os.environ}")
    print(f"[TEST TASK] User: {os.environ.get('USER', 'unknown')}")
    
    # Simulate processing time
    time.sleep(2)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"[TEST TASK] Completed at: {end_time}")
    print(f"[TEST TASK] Duration: {duration.total_seconds()} seconds")
    
    # Clean up test file
    if os.path.exists(test_file):
        os.remove(test_file)
        print(f"[TEST TASK] Cleaned up: {test_file}")
    
    # Return success
    print("[TEST TASK] SUCCESS: Task completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())