#!/usr/bin/env python3
"""
Comprehensive Task Simulator for Python Task Orchestrator

This standalone script tests the entire orchestration process:
1. Creates a test task using ConfigManager (CLI-only)
2. Schedules it to run within the next minute
3. Monitors task execution
4. Validates results
5. Generates a comprehensive assessment report
"""

import os
import sys
import time
import json
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator.core.config_manager import ConfigManager

@dataclass
class SimulationResult:
    """Container for simulation results"""
    timestamp: datetime
    task_name: str
    created: bool
    scheduled_time: str
    execution_detected: bool
    execution_successful: bool
    result_data: Optional[Dict]
    errors: List[str]
    warnings: List[str]
    duration_seconds: float
    
class TaskSimulator:
    """Main task simulator class"""
    
    def __init__(self, db_path: str = "data/orchestrator.db"):
        self.db_path = db_path
        self.config_manager = ConfigManager(db_path)
        self.simulation_start = datetime.now()
        self.task_name = f"test_task_sim_{int(time.time())}"
        self.results = SimulationResult(
            timestamp=self.simulation_start,
            task_name=self.task_name,
            created=False,
            scheduled_time="",
            execution_detected=False,
            execution_successful=False,
            result_data=None,
            errors=[],
            warnings=[],
            duration_seconds=0.0
        )
        
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def create_test_task(self) -> bool:
        """Create a test task scheduled to run in the next minute"""
        try:
            # Calculate next minute for execution
            next_minute = (datetime.now() + timedelta(minutes=1)).replace(second=0, microsecond=0)
            schedule_str = next_minute.strftime("%H:%M")
            
            self.results.scheduled_time = next_minute.strftime("%Y-%m-%d %H:%M:%S")
            
            # Get the test script path
            script_path = os.path.join(os.path.dirname(__file__), "scripts", "test_task.py")
            if not os.path.exists(script_path):
                self.results.errors.append(f"Test script not found: {script_path}")
                return False
            
            # Create the task using ConfigManager
            self.config_manager.add_task(
                name=self.task_name,
                task_type="test",
                command=f"python {script_path}",
                schedule=schedule_str,
                timeout=120,  # 2 minutes timeout
                retry_count=1,
                retry_delay=30,
                dependencies=[],
                enabled=True
            )
            
            # Verify task was created
            created_task = self.config_manager.get_task(self.task_name)
            if created_task:
                self.results.created = True
                self.log(f"✅ Test task created: {self.task_name}")
                self.log(f"   Scheduled for: {self.results.scheduled_time}")
                self.log(f"   Command: {created_task['command']}")
                self.log(f"   Schedule: {schedule_str}")
                return True
            else:
                self.results.errors.append("Task creation verification failed")
                return False
                
        except Exception as e:
            self.results.errors.append(f"Task creation failed: {str(e)}")
            self.log(f"❌ Task creation failed: {e}", "ERROR")
            return False
    
    def check_orchestrator_running(self) -> bool:
        """Check if the orchestrator is running"""
        try:
            # Try to find python processes running main.py or orchestrator
            result = subprocess.run(
                ["pgrep", "-f", "python.*main.py|python.*orchestrator"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                self.log("✅ Orchestrator process detected")
                return True
            else:
                self.log("⚠️  Orchestrator process not detected", "WARNING")
                self.results.warnings.append("Orchestrator process not running")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("⚠️  Process check timed out", "WARNING")
            return False
        except FileNotFoundError:
            # pgrep not available, try alternative method
            try:
                result = subprocess.run(
                    ["ps", "aux"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if "main.py" in result.stdout or "orchestrator" in result.stdout:
                    self.log("✅ Orchestrator process detected (via ps)")
                    return True
                else:
                    self.log("⚠️  Orchestrator process not detected (via ps)", "WARNING")
                    return False
            except:
                self.log("⚠️  Cannot determine orchestrator status", "WARNING")
                return False
    
    def monitor_task_execution(self, timeout_minutes: int = 5) -> bool:
        """Monitor for task execution within the timeout period"""
        self.log(f"🔍 Monitoring task execution for {timeout_minutes} minutes...")
        
        start_monitor = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)
        
        initial_history = self.config_manager.get_task_history(self.task_name, 10)
        initial_count = len(initial_history)
        
        while datetime.now() - start_monitor < timeout:
            try:
                # Check for new execution records
                current_history = self.config_manager.get_task_history(self.task_name, 10)
                
                if len(current_history) > initial_count:
                    # New execution detected
                    latest_result = current_history[0]
                    self.results.execution_detected = True
                    self.results.result_data = latest_result
                    
                    self.log(f"✅ Task execution detected!")
                    self.log(f"   Status: {latest_result.get('status', 'UNKNOWN')}")
                    self.log(f"   Start time: {latest_result.get('start_time', 'N/A')}")
                    self.log(f"   End time: {latest_result.get('end_time', 'N/A')}")
                    self.log(f"   Exit code: {latest_result.get('exit_code', 'N/A')}")
                    
                    # Check if execution was successful
                    if latest_result.get('status') == 'SUCCESS' and latest_result.get('exit_code') == 0:
                        self.results.execution_successful = True
                        self.log("✅ Task executed successfully!")
                    else:
                        self.log(f"❌ Task execution failed: {latest_result.get('status')}", "ERROR")
                        if latest_result.get('error'):
                            self.log(f"   Error: {latest_result.get('error')}", "ERROR")
                    
                    return True
                
                # Wait before next check
                time.sleep(10)
                
            except Exception as e:
                self.log(f"Error during monitoring: {e}", "ERROR")
                time.sleep(5)
        
        self.log("⏰ Monitoring timeout reached", "WARNING")
        self.results.warnings.append(f"No execution detected within {timeout_minutes} minutes")
        return False
    
    def validate_results(self) -> Dict[str, bool]:
        """Validate the simulation results"""
        validation = {
            "task_created": self.results.created,
            "orchestrator_accessible": len(self.results.errors) == 0,
            "execution_detected": self.results.execution_detected,
            "execution_successful": self.results.execution_successful,
            "database_accessible": True,
            "configuration_valid": True
        }
        
        # Test database accessibility
        try:
            all_tasks = self.config_manager.get_all_tasks()
            validation["database_accessible"] = isinstance(all_tasks, dict)
        except Exception as e:
            validation["database_accessible"] = False
            self.results.errors.append(f"Database access failed: {e}")
        
        # Test configuration validity
        try:
            task = self.config_manager.get_task(self.task_name)
            validation["configuration_valid"] = task is not None
        except Exception as e:
            validation["configuration_valid"] = False
            self.results.errors.append(f"Configuration validation failed: {e}")
        
        return validation
    
    def cleanup_test_task(self):
        """Clean up the test task"""
        try:
            # Disable the task instead of deleting for audit trail
            task = self.config_manager.get_task(self.task_name)
            if task:
                self.config_manager.add_task(
                    name=self.task_name,
                    task_type=task['type'],
                    command=task['command'],
                    schedule=task['schedule'],
                    timeout=task['timeout'],
                    retry_count=task['retry_count'],
                    retry_delay=task['retry_delay'],
                    dependencies=task['dependencies'],
                    enabled=False  # Disable the task
                )
                self.log("🧹 Test task disabled (preserved for audit)")
            
        except Exception as e:
            self.log(f"Warning: Cleanup failed: {e}", "WARNING")
            self.results.warnings.append(f"Cleanup failed: {e}")
    
    def generate_report(self) -> str:
        """Generate a comprehensive markdown report"""
        
        # Calculate total duration
        end_time = datetime.now()
        self.results.duration_seconds = (end_time - self.simulation_start).total_seconds()
        
        # Validate results
        validation = self.validate_results()
        
        # Calculate success rate
        total_checks = len(validation)
        passed_checks = sum(1 for v in validation.values() if v)
        success_rate = (passed_checks / total_checks) * 100
        
        # Determine overall status
        overall_status = "✅ PASS" if success_rate >= 80 else "❌ FAIL"
        
        report = f"""# Task Orchestrator Simulation Report

## 📊 Executive Summary

**Overall Status:** {overall_status}  
**Success Rate:** {success_rate:.1f}% ({passed_checks}/{total_checks} checks passed)  
**Simulation Duration:** {self.results.duration_seconds:.1f} seconds  
**Timestamp:** {self.results.timestamp.strftime("%Y-%m-%d %H:%M:%S")}  

---

## 🎯 Test Scenario

**Objective:** Validate end-to-end task orchestration functionality using CLI-only methods

**Test Task Details:**
- **Name:** `{self.results.task_name}`
- **Type:** Test simulation
- **Command:** `python scripts/test_task.py`
- **Scheduled Time:** {self.results.scheduled_time}
- **Expected Behavior:** Execute simple test script and return success

---

## 🔍 Validation Results

| Check | Status | Details |
|-------|--------|---------|
| Task Creation | {"✅ PASS" if validation["task_created"] else "❌ FAIL"} | ConfigManager.add_task() functionality |
| Database Access | {"✅ PASS" if validation["database_accessible"] else "❌ FAIL"} | SQLite database connectivity |
| Configuration Validity | {"✅ PASS" if validation["configuration_valid"] else "❌ FAIL"} | Task configuration integrity |
| Orchestrator Access | {"✅ PASS" if validation["orchestrator_accessible"] else "❌ FAIL"} | Core orchestration components |
| Execution Detection | {"✅ PASS" if validation["execution_detected"] else "❌ FAIL"} | Task execution monitoring |
| Execution Success | {"✅ PASS" if validation["execution_successful"] else "❌ FAIL"} | Task completion with success status |

---

## 📋 Detailed Results

### Task Creation
- **Status:** {"✅ Success" if self.results.created else "❌ Failed"}
- **Task Name:** `{self.results.task_name}`
- **Scheduled Time:** {self.results.scheduled_time}

### Execution Monitoring
- **Execution Detected:** {"Yes" if self.results.execution_detected else "No"}
- **Execution Successful:** {"Yes" if self.results.execution_successful else "No"}

"""

        # Add execution details if available
        if self.results.result_data:
            result = self.results.result_data
            report += f"""### Execution Details
- **Status:** {result.get('status', 'N/A')}
- **Start Time:** {result.get('start_time', 'N/A')}
- **End Time:** {result.get('end_time', 'N/A')}
- **Exit Code:** {result.get('exit_code', 'N/A')}
- **Retry Count:** {result.get('retry_count', 0)}

"""

        # Add errors if any
        if self.results.errors:
            report += "### ❌ Errors Encountered\n\n"
            for i, error in enumerate(self.results.errors, 1):
                report += f"{i}. {error}\n"
            report += "\n"

        # Add warnings if any
        if self.results.warnings:
            report += "### ⚠️ Warnings\n\n"
            for i, warning in enumerate(self.results.warnings, 1):
                report += f"{i}. {warning}\n"
            report += "\n"

        # Add system information
        report += f"""---

## 🔧 Environment Information

- **Python Version:** {sys.version.split()[0]}
- **Operating System:** {os.name}
- **Working Directory:** {os.getcwd()}
- **Database Path:** {self.db_path}
- **Script Location:** {__file__}

---

## 📝 Recommendations

"""

        # Add recommendations based on results
        if success_rate == 100:
            report += "✅ **All systems operational** - The task orchestrator is functioning correctly.\n\n"
        elif success_rate >= 80:
            report += "⚠️ **Minor issues detected** - The orchestrator is mostly functional but has some warnings.\n\n"
        else:
            report += "❌ **Critical issues detected** - The orchestrator requires attention before production use.\n\n"

        if not validation["task_created"]:
            report += "- Fix task creation mechanism in ConfigManager\n"
        if not validation["execution_detected"]:
            report += "- Verify orchestrator scheduler is running\n"
        if not validation["database_accessible"]:
            report += "- Check database connectivity and permissions\n"
        if self.results.warnings:
            report += "- Review and address all warnings listed above\n"

        report += f"""
---

## 🏁 Conclusion

The task orchestrator simulation completed in {self.results.duration_seconds:.1f} seconds with a {success_rate:.1f}% success rate. 

**Next Steps:**
1. Review any errors or warnings above
2. Ensure the orchestrator service is running (`python main.py`)
3. Verify database permissions and connectivity
4. Re-run simulation after addressing issues

---

*Report generated by Task Simulator v1.0 on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

        return report
    
    def run_simulation(self) -> str:
        """Run the complete simulation and return the report"""
        
        self.log("🚀 Starting Task Orchestrator Simulation")
        self.log(f"   Task name: {self.task_name}")
        self.log(f"   Database: {self.db_path}")
        
        try:
            # Step 1: Create test task
            self.log("📝 Step 1: Creating test task...")
            if not self.create_test_task():
                self.log("❌ Task creation failed, aborting simulation", "ERROR")
                return self.generate_report()
            
            # Step 2: Check if orchestrator is running
            self.log("🔍 Step 2: Checking orchestrator status...")
            self.check_orchestrator_running()
            
            # Step 3: Wait for scheduled time and monitor execution
            scheduled_time = datetime.strptime(self.results.scheduled_time, "%Y-%m-%d %H:%M:%S")
            wait_time = (scheduled_time - datetime.now()).total_seconds()
            
            if wait_time > 0:
                self.log(f"⏳ Step 3: Waiting {wait_time:.1f} seconds until scheduled time...")
                time.sleep(min(wait_time + 10, 70))  # Wait for scheduled time + buffer
            
            # Step 4: Monitor task execution
            self.log("👀 Step 4: Monitoring task execution...")
            self.monitor_task_execution(timeout_minutes=3)
            
            # Step 5: Generate report
            self.log("📊 Step 5: Generating report...")
            
        except KeyboardInterrupt:
            self.log("⚠️  Simulation interrupted by user", "WARNING")
            self.results.warnings.append("Simulation interrupted by user")
        except Exception as e:
            self.log(f"❌ Simulation failed: {e}", "ERROR")
            self.results.errors.append(f"Simulation error: {e}")
        finally:
            # Cleanup
            self.cleanup_test_task()
            self.log("✅ Simulation completed")
        
        return self.generate_report()

def main():
    """Main entry point"""
    
    print("=" * 60)
    print("  TASK ORCHESTRATOR COMPREHENSIVE SIMULATOR")
    print("=" * 60)
    print()
    
    # Initialize simulator
    simulator = TaskSimulator()
    
    # Run simulation
    report = simulator.run_simulation()
    
    # Save report to file
    report_filename = f"simulation_report_{int(time.time())}.md"
    with open(report_filename, "w") as f:
        f.write(report)
    
    print()
    print("=" * 60)
    print("  SIMULATION COMPLETE")
    print("=" * 60)
    print(f"📄 Report saved to: {report_filename}")
    print()
    print("Report preview:")
    print("-" * 40)
    print(report[:500] + "..." if len(report) > 500 else report)

if __name__ == "__main__":
    main()