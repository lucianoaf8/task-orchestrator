# complete_flow_test.ps1 - Corrected PowerShell syntax
# PowerShell script for Windows flow validation

$ErrorActionPreference = "Stop"

Write-Host "=== Complete Flow Validation Test ===" -ForegroundColor Green

function Test-Step {
    param(
        [string]$StepName,
        [scriptblock]$TestBlock
    )
    
    Write-Host "`n$StepName..." -ForegroundColor Yellow
    try {
        & $TestBlock
        Write-Host "✓ $StepName completed successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ $StepName failed: $_" -ForegroundColor Red
        return $false
    }
}

# Step 1: Create test task via CLI
$step1Success = Test-Step "Step 1: Creating test task" {
    $step1Script = @'
from orchestrator.core.config_manager import ConfigManager
from orchestrator.core.scheduler import TaskScheduler

# Create task in database
cm = ConfigManager()
cm.add_task(
    name='flow_test_task',
    task_type='data_job', 
    command='echo "Flow test successful"',
    schedule='0 6 * * *',
    enabled=True
)
print('✓ Task saved to database')

# Trigger scheduling via TaskScheduler
scheduler = TaskScheduler()
success = scheduler.schedule_task('flow_test_task')
print(f'✓ Scheduling result: {success}')
'@

    python -c $step1Script
    if ($LASTEXITCODE -ne 0) {
        throw "Task creation failed with exit code $LASTEXITCODE"
    }
}

if (-not $step1Success) { 
    exit 1 
}

# Step 2: Verify Windows Task was created
$step2Success = Test-Step "Step 2: Verifying Windows Task creation" {
    $taskExists = $false
    try {
        $null = schtasks /query /tn "\Orchestrator\Orc_flow_test_task" 2>$null
        $taskExists = ($LASTEXITCODE -eq 0)
    }
    catch {
        $taskExists = $false
    }
    
    if ($taskExists) {
        Write-Host "✓ Windows Task exists" -ForegroundColor Green
        
        # Verify task command
        try {
            $taskXml = schtasks /query /tn "\Orchestrator\Orc_flow_test_task" /xml
            if ($taskXml -match "flow_test_task") {
                Write-Host "✓ Windows Task command contains task name" -ForegroundColor Green
            }
            else {
                Write-Host "⚠ Windows Task command may need verification" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "⚠ Could not verify task command details" -ForegroundColor Yellow
        }
    }
    else {
        throw "Windows Task not found in Task Scheduler"
    }
}

if (-not $step2Success) { 
    exit 1 
}

# Step 3: Test manual execution via CLI
$step3Success = Test-Step "Step 3: Testing task execution via CLI" {
    $step3Script = @'
from orchestrator.core.scheduler import TaskScheduler

scheduler = TaskScheduler()
result = scheduler.execute_task('flow_test_task')
if result.status == 'SUCCESS':
    print('✓ Task execution successful')
    print(f'  Output: {result.output}')
else:
    print(f'✗ Task execution failed: {result.status}')
    print(f'  Error: {result.error}')
    import sys
    sys.exit(1)
'@

    python -c $step3Script
    if ($LASTEXITCODE -ne 0) {
        throw "Task execution failed with exit code $LASTEXITCODE"
    }
}

if (-not $step3Success) { 
    exit 1 
}

# Step 4: Verify execution was logged
$step4Success = Test-Step "Step 4: Verifying execution was logged" {
    $step4Script = @'
from orchestrator.core.config_manager import ConfigManager
import sys

cm = ConfigManager()
history = cm.get_task_history('flow_test_task', 1)
if history and history[0]['status'] == 'SUCCESS':
    print('✓ Task execution logged successfully')
    print(f"  Output: {history[0]['output']}")
else:
    print('✗ Task execution not logged properly')
    if history:
        print(f"  Last status: {history[0].get('status', 'Unknown')}")
        print(f"  Last error: {history[0].get('error', 'None')}")
    else:
        print('  No execution history found')
    sys.exit(1)
'@

    python -c $step4Script
    if ($LASTEXITCODE -ne 0) {
        throw "Execution logging verification failed"
    }
}

if (-not $step4Success) { 
    exit 1 
}

# Step 5: Test web API integration
$step5Success = Test-Step "Step 5: Testing web API integration" {
    $step5Script = @'
import requests
import time
import subprocess
import sys
import os

web_process = None
try:
    # Start web server
    web_process = subprocess.Popen([
        sys.executable, '-m', 'flask', '--app', 'orchestrator.web.app:create_app', 
        'run', '--port', '5002', '--host', '127.0.0.1'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for server to start
    time.sleep(5)

    # Test server is responding
    server_ready = False
    for attempt in range(10):
        try:
            response = requests.get('http://127.0.0.1:5002/health', timeout=2)
            if response.status_code == 200:
                server_ready = True
                break
        except:
            time.sleep(1)
    
    if not server_ready:
        raise Exception('Web server did not start within 10 seconds')
    
    # Test task creation via API
    response = requests.post('http://127.0.0.1:5002/api/tasks', json={
        'name': 'api_flow_test',
        'type': 'data_job',
        'command': 'echo "API flow test"',
        'schedule': '0 7 * * *',
        'enabled': True
    }, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('status') == 'success':
            print('✓ Web API task creation successful')
        else:
            print(f'✗ Web API failed: {data}')
            sys.exit(1)
    else:
        print(f'✗ Web API failed: Status {response.status_code}')
        print(f'Response: {response.text}')
        sys.exit(1)
        
except Exception as e:
    print(f'✗ Web API test failed: {e}')
    sys.exit(1)
finally:
    if web_process:
        try:
            web_process.terminate()
            web_process.wait(timeout=5)
        except:
            web_process.kill()
'@

    python -c $step5Script
    if ($LASTEXITCODE -ne 0) {
        throw "Web API test failed"
    }
}

# Continue even if web API test fails (non-critical for core functionality)
if (-not $step5Success) {
    Write-Host "⚠ Web API test failed but continuing..." -ForegroundColor Yellow
}

# Step 6: Cleanup
$step6Success = Test-Step "Step 6: Cleaning up test tasks" {
    # Unschedule test tasks
    $cleanupScript = @'
from orchestrator.core.scheduler import TaskScheduler

scheduler = TaskScheduler()
result1 = scheduler.unschedule_task('flow_test_task')
result2 = scheduler.unschedule_task('api_flow_test')
print(f'✓ Cleanup results: flow_test_task={result1}, api_flow_test={result2}')
'@

    python -c $cleanupScript
    
    # Verify cleanup
    $task1Exists = $false
    $task2Exists = $false
    
    try {
        $null = schtasks /query /tn "\Orchestrator\Orc_flow_test_task" 2>$null
        $task1Exists = ($LASTEXITCODE -eq 0)
    }
    catch { 
        # Task doesn't exist - this is what we want
    }
    
    try {
        $null = schtasks /query /tn "\Orchestrator\Orc_api_flow_test" 2>$null
        $task2Exists = ($LASTEXITCODE -eq 0)
    }
    catch { 
        # Task doesn't exist - this is what we want
    }
    
    if (-not $task1Exists -and -not $task2Exists) {
        Write-Host "✓ Test tasks cleaned up successfully" -ForegroundColor Green
    }
    else {
        Write-Host "⚠ Some test tasks may still exist (manual cleanup may be needed)" -ForegroundColor Yellow
    }
}

Write-Host "`n=== Flow Validation Complete ===" -ForegroundColor Green

# Final verification summary
Write-Host "`n=== Validation Summary ===" -ForegroundColor Cyan
Write-Host "✓ Task creation and database storage: $step1Success" -ForegroundColor $(if($step1Success){"Green"}else{"Red"})
Write-Host "✓ Windows Task Scheduler integration: $step2Success" -ForegroundColor $(if($step2Success){"Green"}else{"Red"})
Write-Host "✓ Task execution via TaskScheduler: $step3Success" -ForegroundColor $(if($step3Success){"Green"}else{"Red"})
Write-Host "✓ Execution logging and history: $step4Success" -ForegroundColor $(if($step4Success){"Green"}else{"Red"})
Write-Host "✓ Web API integration: $step5Success" -ForegroundColor $(if($step5Success){"Green"}else{"Yellow"})
Write-Host "✓ Cleanup and unscheduling: $step6Success" -ForegroundColor $(if($step6Success){"Green"}else{"Yellow"})

$overallSuccess = $step1Success -and $step2Success -and $step3Success -and $step4Success
if ($overallSuccess) {
    Write-Host "`nAll critical validation steps passed!" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "`nSome critical validation steps failed!" -ForegroundColor Red
    exit 1
}