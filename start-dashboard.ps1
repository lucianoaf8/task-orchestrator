# PowerShell helper to start the Orchestrator Web Dashboard
# Usage: .\scripts\start-dashboard.ps1

# Ensure we are in project root
param()

$ErrorActionPreference = 'Stop'

# Activate local virtual environment if present
if (Test-Path .\.venv\Scripts\Activate.ps1) {
    Write-Host 'Activating virtual environment…'
    . .\.venv\Scripts\Activate.ps1
}

# Install package in editable mode if not already
pip show task-python-orchestrator -q
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing orchestrator package in editable mode…'
    pip install -e .
}

# Set Flask app entry point and run server
$env:FLASK_APP = "orchestrator.web.app:create_app"
$env:FLASK_ENV = "development"
python -m flask run --host 0.0.0.0 --port 5000
