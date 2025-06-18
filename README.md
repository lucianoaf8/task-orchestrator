# Python Script Orchestrator

Local-only task scheduling and monitoring system for data pipelines.

## Quick Start

1. **Setup**
   ```bash
   pip install -r requirements.txt
   python test_setup.py  # Validate setup
   python setup.py       # Configure database
   ```

2. **Run**
   ```bash
   # Windows
   run_orchestrator.bat
   
   # Linux/Mac  
   chmod +x run_orchestrator.sh
   ./run_orchestrator.sh
   ```

3. **Dashboard**
   ```bash
   python dashboard.py
   # Open: http://localhost:5000
   ```

## Features

- ✅ SQLite-based configuration with encryption
- ✅ Cron-style scheduling with dependencies
- ✅ Cross-platform VPN detection
- ✅ Email notifications
- ✅ Web dashboard
- ✅ DBeaver integration
- ✅ Retry logic and error handling

## File Structure

```
orchestrator/
├── data/
│   └── orchestrator.db          # SQLite database
├── scripts/
│   ├── check_vpn.py            # VPN detection
│   ├── fetch_totango.py        # Your data scripts
│   └── fetch_citus.py          
├── logs/                       # Execution logs
├── templates/
│   └── dashboard.html          # Web interface
├── config_manager.py           # Database operations
├── orchestrator.py             # Main scheduler
├── dashboard.py               # Web dashboard
└── setup.py                   # Initial configuration
```

## Configuration

Use DBeaver to connect to `data/orchestrator.db` for visual configuration management.

**Common SQL operations:**
```sql
-- Add new task
INSERT INTO tasks VALUES ('task_name', 'data_job', '0 6 * * *', 'python script.py', 3600, 3, 300, '[]', 1, datetime('now'), datetime('now'));

-- Update schedule
UPDATE tasks SET schedule = '0 8 * * *' WHERE name = 'task_name';

-- View execution history
SELECT * FROM task_results ORDER BY start_time DESC LIMIT 20;
```

## Customization

1. **Replace sample scripts** in `scripts/` with your actual data fetching logic
2. **Update VPN detection** in `scripts/check_vpn.py` with your network details
3. **Configure email** credentials during setup
4. **Set network paths** for file distribution

## Security

- Credentials encrypted with Fernet (AES-128)
- PBKDF2 key derivation with 100k iterations
- SQLite file-level permissions
- No network exposure

# test_setup.py - Quick System Validation
import os
import sys
import subprocess
from pathlib import Path

def test_dependencies():
    """Test if all required packages are installed"""
    required_packages = [
        'sqlite3', 'croniter', 'flask', 'cryptography', 
        'pandas', 'openpyxl', 'requests'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing.append(package)
            print(f"❌ {package}")
    
    return len(missing) == 0

def test_database():
    """Test database creation and basic operations"""
    try:
        from config_manager import ConfigManager
        config = ConfigManager()  # No encryption for test
        
        # Test basic operations
        config.store_config('test', 'key', 'value')
        value = config.get_config('test', 'key')
        
        if value == 'value':
            print("✅ Database operations working")
            return True
        else:
            print("❌ Database operations failed")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_vpn_detection():
    """Test VPN detection script"""
    try:
        result = subprocess.run([sys.executable, 'scripts/check_vpn.py'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ VPN detected (or VPN check passed)")
        else:
            print("⚠️  VPN not detected (this may be expected)")
            
        return True
        
    except Exception as e:
        print(f"❌ VPN detection test failed: {e}")
        return False

def test_file_structure():
    """Test that all required directories and files exist"""
    required_dirs = ['data', 'scripts', 'logs', 'templates']
    required_files = [
        'config_manager.py', 'orchestrator.py', 'setup.py',
        'scripts/check_vpn.py', 'requirements.txt'
    ]
    
    all_good = True
    
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✅ Directory: {directory}")
        else:
            print(f"❌ Missing directory: {directory}")
            all_good = False
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ File: {file_path}")
        else:
            print(f"❌ Missing file: {file_path}")
            all_good = False
    
    return all_good

def main():
    """Run all tests"""
    print("=== Orchestrator Setup Validation ===\n")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Dependencies", test_dependencies),
        ("Database", test_database),
        ("VPN Detection", test_vpn_detection)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n--- Testing {test_name} ---")
        results[test_name] = test_func()
    
    print("\n=== Summary ===")
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! You're ready to run the orchestrator.")
        print("Next steps:")
        print("1. Run: python setup.py (if not done already)")
        print("2. Run: python orchestrator.py")
        print("3. Run: python dashboard.py (in separate terminal)")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above before proceeding.")
        
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# .env.template - Environment Variables Template
# Copy this to .env and fill in your values

# Database Configuration
DB_PATH=data/orchestrator.db
MASTER_PASSWORD=your_encryption_password_here

# Email Configuration  
EMAIL_USERNAME=your-email@company.com
EMAIL_PASSWORD=your_app_password_here
EMAIL_RECIPIENTS=admin@company.com,team@company.com

# VPN Configuration
VPN_INTERNAL_IPS=10.0.0.1,192.168.1.1,172.16.0.1
VPN_INTERNAL_DOMAIN=internal.company.com

# Network Paths
NETWORK_SHARE_PATH=//server/share/data
BACKUP_PATH=//backup-server/backups

# API Configuration (if needed)
TOTANGO_API_URL=https://api.totango.com
TOTANGO_API_KEY=your_totango_api_key
CITUS_DB_HOST=your.citus.host
CITUS_DB_USER=your_db_user
CITUS_DB_PASSWORD=your_db_password

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30

#!/bin/bash
# run_orchestrator.sh - Linux/Mac Startup Script

set -e  # Exit on any error

echo "Starting Python Orchestrator..."
cd "$(dirname "$0")"
echo "Current directory: $(pwd)"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 not found"
    exit 1
fi

# Check if virtual environment exists (optional)
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if requirements are installed
python3 -c "import sqlite3, croniter, flask" 2>/dev/null || {
    echo "Installing requirements..."
    pip3 install -r requirements.txt
}

# Check if database exists
if [ ! -f "data/orchestrator.db" ]; then
    echo "Database not found. Running setup..."
    python3 setup.py
fi

echo "Starting orchestrator..."
echo "Press Ctrl+C to stop"
python3 orchestrator.py

# run_orchestrator.bat - Windows Service Script
@echo off
echo Starting Python Orchestrator...
cd /d "%~dp0"
echo Current directory: %CD%
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists (optional)
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if requirements are installed
python -c "import sqlite3, croniter, flask" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing requirements...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install requirements
        pause
        exit /b 1
    )
)

REM Check if database exists
if not exist "data\orchestrator.db" (
    echo Database not found. Running setup...
    python setup.py
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Setup failed
        pause
        exit /b 1
    )
)

echo Starting orchestrator...
echo Press Ctrl+C to stop
python orchestrator.py

pause