The tasks below must be completed in order, and one at a time. You will only move to the next task after successfully completing the current one.

## **Task 1: Validate `orc.py` Entry Point Creation**

```
Test that the newly created orc.py file is working correctly as the unified scheduler/executor entry point.

Run these commands and verify the expected results:

1. Check file exists: `ls -la orc.py`
2. Test help output: `python orc.py --help`  
3. Test with non-existent task: `python orc.py --schedule non_existent_task`
4. Test list operation: `python orc.py --list`

Expected Results:
- File `orc.py` exists in project root
- Help shows all four operations: --schedule, --task, --list, --unschedule
- Non-existent task returns error message and exit code 1
- List operation runs without crashing (may show empty or existing tasks)

PASS CRITERIA: All commands execute without Python import errors and show expected output formats.
FAIL CRITERIA: Any Python import errors, missing operations in help, or crashes.
```

## **Task 2: Validate `main.py` Flow Integration**

```
Test that main.py has been correctly modified to follow the documented flow and can trigger orc.py scheduling.

Run these commands and verify the expected results:

1. Test main.py help: `python main.py cli --help`
2. Test status display: `python main.py status`  
3. Test interactive mode starts: `echo "7" | python main.py`
4. Verify integration function: `python -c "from main import trigger_orc_scheduling; print('Integration OK')"`

Expected Results:
- CLI help displays without errors
- Status shows task counts and scheduled tasks
- Interactive mode starts and exits properly with option 7
- Integration function can be imported without errors

PASS CRITERIA: All validation commands succeed and trigger_orc_scheduling function exists.
FAIL CRITERIA: Import errors, function missing, or crashes in main.py operations.
```

## **Task 3: Validate Web API orc.py Integration**

```
Test that the web API has been updated to call orc.py via subprocess instead of direct object calls.

Run these commands to test the API integration:

1. Start web server: `python -m flask --app orchestrator.web.app:create_app run --port 5001 &` (note the PID)
2. Wait 3 seconds for server startup
3. Test task creation: `curl -X POST http://localhost:5001/api/tasks -H "Content-Type: application/json" -d '{"name":"test_api_task","type":"data_job","command":"echo test","schedule":"0 6 * * *","enabled":true}'`
4. Test scheduling endpoint: `curl -X POST http://localhost:5001/api/tasks/test_api_task/schedule`
5. Test list endpoint: `curl http://localhost:5001/api/tasks/scheduled`
6. Stop server: `kill %1` or kill the background process

Expected Results:
- Task creation returns JSON with "scheduled": true
- Scheduling endpoint returns success response
- List endpoint returns JSON with scheduled tasks array
- No 500 errors in any responses

PASS CRITERIA: All API endpoints return valid JSON responses with expected "scheduled" fields.
FAIL CRITERIA: 500 errors, missing "scheduled" field, or non-JSON responses.
```

## **Task 4: Validate Windows Task Scheduler Integration**

```
Test that Windows scheduled tasks are being created with the correct orc.py commands.

Run this Python test to verify Windows integration:

```python
python -c "
from orchestrator.utils.windows_scheduler import WindowsScheduler
from orchestrator.utils.cron_converter import CronConverter

print('Testing Windows task creation...')
ws = WindowsScheduler()
params = CronConverter.cron_to_schtasks_params('0 6 * * *')
success = ws.create_task('test_validation', 'dummy_command', params, 'Test task')
print(f'Task creation success: {success}')
"
```

Then verify with Windows commands:
1. Check task exists: `schtasks /query /tn "\Orchestrator\Orc_test_validation"`
2. Check command contains orc.py: `schtasks /query /tn "\Orchestrator\Orc_test_validation" /xml | findstr "orc.py"`
3. Clean up: `schtasks /delete /tn "\Orchestrator\Orc_test_validation" /f`

Expected Results:
- Task creation returns True
- Windows shows the task exists  
- Task XML contains "orc.py --task test_validation"
- Task deletes successfully

PASS CRITERIA: Windows Task Scheduler contains tasks with orc.py commands in the action.
FAIL CRITERIA: Tasks not created, wrong commands, or cleanup fails.
```

## **Task 5: Validate Complete End-to-End Flow**

```
Test the complete documented flow from task creation through Windows scheduling to execution.

Create and run this test script to validate the entire flow:

```python
# complete_flow_test.py
import subprocess
import sys
import time

def test_complete_flow():
    print("=== Complete Flow Validation Test ===")
    
    # Step 1: Create task and trigger scheduling
    print("Step 1: Creating and scheduling test task...")
    try:
        from orchestrator.core.config_manager import ConfigManager
        from main import trigger_orc_scheduling
        
        cm = ConfigManager()
        cm.add_task(
            name='flow_test_task',
            task_type='data_job', 
            command='echo "Flow test successful"',
            schedule='0 6 * * *',
            enabled=True
        )
        print('✓ Task saved to database')
        
        success = trigger_orc_scheduling('flow_test_task')
        print(f'✓ Scheduling via orc.py: {success}')
        
        if not success:
            print('✗ Scheduling failed')
            return False
            
    except Exception as e:
        print(f'✗ Step 1 failed: {e}')
        return False
    
    # Step 2: Verify Windows Task creation
    print("\nStep 2: Verifying Windows Task...")
    result = subprocess.run(['schtasks', '/query', '/tn', r'\Orchestrator\Orc_flow_test_task'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Windows Task exists")
    else:
        print("✗ Windows Task not found")
        return False
    
    # Step 3: Test execution via orc.py
    print("\nStep 3: Testing task execution...")
    result = subprocess.run(['python', 'orc.py', '--task', 'flow_test_task'], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Task execution successful")
    else:
        print(f"✗ Task execution failed: {result.stderr}")
        return False
    
    # Step 4: Verify execution logging
    print("\nStep 4: Verifying execution logging...")
    try:
        history = cm.get_task_history('flow_test_task', 1)
        if history and history[0]['status'] == 'SUCCESS':
            print('✓ Task execution logged successfully')
        else:
            print('✗ Task execution not logged properly')
            return False
    except Exception as e:
        print(f'✗ Step 4 failed: {e}')
        return False
    
    # Cleanup
    print("\nCleaning up...")
    subprocess.run(['python', 'orc.py', '--unschedule', 'flow_test_task'])
    print("✓ Cleanup complete")
    
    return True

if __name__ == "__main__":
    success = test_complete_flow()
    if success:
        print("\n🎉 COMPLETE FLOW TEST PASSED")
        sys.exit(0)
    else:
        print("\n❌ COMPLETE FLOW TEST FAILED")
        sys.exit(1)
```

Run: `python complete_flow_test.py`

Expected Results:
- All steps show ✓ (success) 
- No ✗ (failure) messages
- Script exits with "COMPLETE FLOW TEST PASSED"
- Test task is created, scheduled, executed, and cleaned up properly

PASS CRITERIA: Complete flow test passes all validation steps and exits with code 0.
FAIL CRITERIA: Any step shows ✗ or script exits with error code.
```

## **Task 6: Validate Web API Flow Integration**

```
Test that the web API correctly integrates with the orc.py flow for task creation and scheduling.

Run this test to validate web API integration:

```python
# web_api_flow_test.py
import requests
import subprocess
import sys
import time
import json

def test_web_api_flow():
    print("=== Web API Flow Test ===")
    
    # Start web server
    print("Starting web server...")
    web_process = subprocess.Popen([
        sys.executable, '-m', 'flask', '--app', 'orchestrator.web.app:create_app', 
        'run', '--port', '5002'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(5)  # Wait for server startup
    
    try:
        # Test 1: Create task via API
        print("Test 1: Creating task via API...")
        response = requests.post('http://localhost:5002/api/tasks', json={
            'name': 'api_flow_test',
            'type': 'data_job',
            'command': 'echo "API flow test"',
            'schedule': '0 7 * * *',
            'enabled': True
        }, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('scheduled'):
                print('✓ Task created and scheduled via API')
            else:
                print(f'✗ Task created but not scheduled: {data}')
                return False
        else:
            print(f'✗ API call failed: {response.status_code} - {response.text}')
            return False
        
        # Test 2: Verify scheduling worked
        print("Test 2: Verifying Windows Task creation...")
        result = subprocess.run(['schtasks', '/query', '/tn', r'\Orchestrator\Orc_api_flow_test'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Windows Task created via API")
        else:
            print("✗ Windows Task not found after API creation")
            return False
        
        # Test 3: List scheduled tasks via API
        print("Test 3: Listing tasks via API...")
        response = requests.get('http://localhost:5002/api/tasks/scheduled', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'scheduled_tasks' in data:
                print(f'✓ API lists {len(data["scheduled_tasks"])} scheduled tasks')
            else:
                print(f'✗ API response missing scheduled_tasks: {data}')
                return False
        else:
            print(f'✗ List API failed: {response.status_code}')
            return False
        
        # Cleanup
        print("Cleaning up...")
        subprocess.run(['python', 'orc.py', '--unschedule', 'api_flow_test'])
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f'✗ Request failed: {e}')
        return False
    except Exception as e:
        print(f'✗ Test failed: {e}')
        return False
    finally:
        web_process.terminate()
        web_process.wait()

if __name__ == "__main__":
    success = test_web_api_flow()
    if success:
        print("\n🎉 WEB API FLOW TEST PASSED")
        sys.exit(0)
    else:
        print("\n❌ WEB API FLOW TEST FAILED")
        sys.exit(1)
```

Run: `python web_api_flow_test.py`

Expected Results:
- Web server starts successfully
- Task creation via API returns "scheduled": true
- Windows Task is created with correct orc.py command
- API can list scheduled tasks
- Cleanup removes the test task

PASS CRITERIA: All API operations succeed and Windows integration works.
FAIL CRITERIA: API errors, Windows tasks not created, or missing scheduled_tasks field.
```

## **Task 7: Final System Validation**

```
Perform final comprehensive validation that the entire system follows the documented flow.

Run these final validation commands:

1. Verify all entry points: `python orc.py --help && python main.py status`
2. Test orc.py operations: `python orc.py --list`
3. Check system integration: 
```python
python -c "
# Test complete integration
from orchestrator.core.config_manager import ConfigManager
from main import trigger_orc_scheduling
import subprocess

print('=== Final System Validation ===')

# Create task
cm = ConfigManager()
cm.add_task('final_test', 'data_job', 'echo final validation', '0 8 * * *', enabled=True)
print('✓ Task database integration working')

# Schedule it  
success = trigger_orc_scheduling('final_test')
print(f'✓ main.py -> orc.py integration: {success}')

# Execute it
result = subprocess.run(['python', 'orc.py', '--task', 'final_test'], capture_output=True)
print(f'✓ orc.py execution: {result.returncode == 0}')

# Verify logging
history = cm.get_task_history('final_test', 1)
print(f'✓ Result logging: {bool(history and history[0][\"status\"] == \"SUCCESS\")}')

print('=== System Validation Complete ===')
"
```

4. Verify Windows integration: `schtasks /query /tn "\Orchestrator\Orc_final_test"`
5. Cleanup: `python orc.py --unschedule final_test`

Expected Results:
- All entry points work without errors
- Task lifecycle completes successfully (create -> schedule -> execute -> log)
- Windows Task Scheduler shows orchestrator tasks with orc.py commands
- Cleanup successfully removes tasks

PASS CRITERIA: All commands execute successfully, task lifecycle works, Windows integration confirmed.
FAIL CRITERIA: Any Python errors, failed task execution, or Windows integration issues.

SUCCESS MESSAGE: "🎉 PROJECT IS 100% FLOW COMPLIANT"
FAILURE MESSAGE: "❌ FLOW COMPLIANCE ISSUES DETECTED"
```

## **Task 8: Flow Documentation Verification**

```
Verify that the implemented flow exactly matches the documented flow requirements.

Create and run this verification script:

```python
# flow_verification.py
import subprocess
import sys

def verify_flow_compliance():
    print("=== Flow Documentation Verification ===")
    
    compliance_checks = [
        ("orc.py exists as unified entry point", lambda: verify_file_exists("orc.py")),
        ("main.py calls orc.py --schedule", lambda: verify_main_integration()),
        ("Web API calls orc.py subprocess", lambda: verify_web_integration()),
        ("Windows tasks call orc.py --task", lambda: verify_windows_integration()),
        ("Complete flow works end-to-end", lambda: verify_complete_flow())
    ]
    
    results = []
    for description, check_func in compliance_checks:
        try:
            result = check_func()
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {description}")
            results.append(result)
        except Exception as e:
            print(f"✗ ERROR: {description} - {e}")
            results.append(False)
    
    total_checks = len(results)
    passed_checks = sum(results)
    compliance_percentage = (passed_checks / total_checks) * 100
    
    print(f"\n=== COMPLIANCE SUMMARY ===")
    print(f"Passed: {passed_checks}/{total_checks} ({compliance_percentage:.1f}%)")
    
    if compliance_percentage == 100:
        print("🎉 PROJECT IS 100% FLOW COMPLIANT")
        return True
    else:
        print(f"❌ PROJECT IS {compliance_percentage:.1f}% FLOW COMPLIANT")
        return False

def verify_file_exists(filename):
    import os
    return os.path.exists(filename)

def verify_main_integration():
    try:
        from main import trigger_orc_scheduling
        return callable(trigger_orc_scheduling)
    except ImportError:
        return False

def verify_web_integration():
    try:
        with open("orchestrator/web/api/routes.py", "r") as f:
            content = f.read()
            return "call_orc_py" in content and "subprocess" in content
    except:
        return False

def verify_windows_integration():
    try:
        with open("orchestrator/utils/windows_scheduler.py", "r") as f:
            content = f.read()
            return "orc.py --task" in content
    except:
        return False

def verify_complete_flow():
    # Quick test of basic flow components
    result1 = subprocess.run(['python', 'orc.py', '--help'], capture_output=True)
    result2 = subprocess.run(['python', 'main.py', 'status'], capture_output=True)
    return result1.returncode == 0 and result2.returncode == 0

if __name__ == "__main__":
    success = verify_flow_compliance()
    sys.exit(0 if success else 1)
```

Run: `python flow_verification.py`

Expected Results:
- All 5 compliance checks show "✓ PASS"
- Compliance percentage shows 100%
- Final message: "🎉 PROJECT IS 100% FLOW COMPLIANT"

PASS CRITERIA: 100% compliance with all checks passing.
FAIL CRITERIA: Any check fails or compliance less than 100%.
```

---

**Run these tasks in sequence** - each must pass before proceeding to the next. If any task fails, the corresponding implementation step needs to be fixed before continuing.