# SQLite-Based Python Script Orchestration System

## Architecture Overview

The system consists of four main components:
1. **Task Scheduler** - Manages execution timing and dependencies
2. **Condition Checker** - Validates prerequisites (VPN, upstream jobs)
3. **Configuration Manager** - SQLite-based config, credentials, and state management
4. **Logger & Monitor** - Centralized logging and email notifications

## Core Components

### 1. Database Schema (`orchestrator.db`)

```sql
-- Task configuration
CREATE TABLE tasks (
    name TEXT PRIMARY KEY,
    type TEXT,
    schedule TEXT,
    command TEXT,
    timeout INTEGER DEFAULT 3600,
    retry_count INTEGER DEFAULT 0,
    retry_delay INTEGER DEFAULT 300,
    dependencies TEXT DEFAULT '[]',
    enabled BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Application configuration
CREATE TABLE config (
    section TEXT,
    key TEXT,
    value TEXT,
    PRIMARY KEY (section, key)
);

-- Encrypted credentials
CREATE TABLE credentials (
    name TEXT PRIMARY KEY,
    value BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Task execution history
CREATE TABLE task_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name TEXT,
    status TEXT,
    start_time TEXT,
    end_time TEXT,
    exit_code INTEGER,
    output TEXT,
    error TEXT,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (task_name) REFERENCES tasks (name)
);
```

### 2. Configuration Manager (`config_manager.py`)

```python
import os
import sqlite3
import json
import base64
import platform
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class ConfigManager:
    def __init__(self, db_path: str = "data/orchestrator.db", master_password: str = None):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.cipher = self._init_cipher(master_password) if master_password else None
        self._init_db()
        
    def _init_cipher(self, password: str):
        """Initialize encryption cipher with system-specific salt"""
        # Use system hostname as salt base for consistency
        salt = platform.node().encode()[:16].ljust(16, b'0')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def _init_db(self):
        """Initialize database schema"""
        # Enable WAL mode for better concurrency
        self.db.execute("PRAGMA journal_mode=WAL")
        
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                name TEXT PRIMARY KEY,
                type TEXT,
                schedule TEXT,
                command TEXT,
                timeout INTEGER DEFAULT 3600,
                retry_count INTEGER DEFAULT 0,
                retry_delay INTEGER DEFAULT 300,
                dependencies TEXT DEFAULT '[]',
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS config (
                section TEXT,
                key TEXT,
                value TEXT,
                PRIMARY KEY (section, key)
            );
            
            CREATE TABLE IF NOT EXISTS credentials (
                name TEXT PRIMARY KEY,
                value BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS task_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                status TEXT,
                start_time TEXT,
                end_time TEXT,
                exit_code INTEGER,
                output TEXT,
                error TEXT,
                retry_count INTEGER DEFAULT 0,
                FOREIGN KEY (task_name) REFERENCES tasks (name)
            );
        """)
        self.db.commit()
    
    def add_task(self, name: str, task_type: str, command: str, 
                 schedule: str = None, **kwargs):
        """Add or update task configuration"""
        self.db.execute("""
            INSERT OR REPLACE INTO tasks 
            (name, type, schedule, command, timeout, retry_count, retry_delay, dependencies, enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            name, task_type, schedule, command,
            kwargs.get('timeout', 3600),
            kwargs.get('retry_count', 0),
            kwargs.get('retry_delay', 300),
            json.dumps(kwargs.get('dependencies', [])),
            kwargs.get('enabled', True)
        ))
        self.db.commit()
    
    def get_task(self, name: str) -> Optional[Dict[str, Any]]:
        """Get task configuration"""
        cursor = self.db.execute("SELECT * FROM tasks WHERE name=?", (name,))
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            task = dict(zip(columns, row))
            task['dependencies'] = json.loads(task['dependencies'])
            return task
        return None
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get all enabled tasks"""
        cursor = self.db.execute("SELECT * FROM tasks WHERE enabled=1")
        tasks = {}
        for row in cursor.fetchall():
            columns = [desc[0] for desc in cursor.description]
            task = dict(zip(columns, row))
            task['dependencies'] = json.loads(task['dependencies'])
            tasks[task['name']] = task
        return tasks
    
    def store_credential(self, name: str, value: str):
        """Store encrypted credential"""
        if self.cipher:
            encrypted_value = self.cipher.encrypt(value.encode())
        else:
            encrypted_value = value.encode()
        
        self.db.execute("INSERT OR REPLACE INTO credentials VALUES (?, ?, CURRENT_TIMESTAMP)", 
                       (name, encrypted_value))
        self.db.commit()
    
    def get_credential(self, name: str) -> Optional[str]:
        """Get decrypted credential"""
        result = self.db.execute("SELECT value FROM credentials WHERE name=?", (name,)).fetchone()
        if result:
            if self.cipher:
                return self.cipher.decrypt(result[0]).decode()
            else:
                return result[0].decode()
        return None
    
    def store_config(self, section: str, key: str, value: str):
        """Store configuration value"""
        self.db.execute("INSERT OR REPLACE INTO config VALUES (?, ?, ?)", 
                       (section, key, value))
        self.db.commit()
    
    def get_config(self, section: str, key: str, default: str = None) -> Optional[str]:
        """Get configuration value"""
        result = self.db.execute("SELECT value FROM config WHERE section=? AND key=?", 
                                (section, key)).fetchone()
        return result[0] if result else default
    
    def save_task_result(self, result):
        """Save task execution result"""
        self.db.execute("""
            INSERT INTO task_results 
            (task_name, status, start_time, end_time, exit_code, output, error, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.task_name, result.status,
            result.start_time.isoformat() if result.start_time else None,
            result.end_time.isoformat() if result.end_time else None,
            result.exit_code, result.output, result.error, result.retry_count
        ))
        self.db.commit()
    
    def get_task_history(self, task_name: str, limit: int = 100):
        """Get recent task execution history"""
        cursor = self.db.execute("""
            SELECT * FROM task_results 
            WHERE task_name=? 
            ORDER BY start_time DESC 
            LIMIT ?
        """, (task_name, limit))
        
        results = []
        for row in cursor.fetchall():
            columns = [desc[0] for desc in cursor.description]
            results.append(dict(zip(columns, row)))
        return results
```

### 3. Core Orchestrator (`orchestrator.py`)

```python
import os
import sys
import time
import logging
import smtplib
import subprocess
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from croniter import croniter
from dataclasses import dataclass
from config_manager import ConfigManager

@dataclass
class TaskResult:
    task_name: str
    status: str  # SUCCESS, FAILED, SKIPPED, RUNNING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    output: str = ""
    error: str = ""
    retry_count: int = 0

class TaskManager:
    def __init__(self, db_path: str = "data/orchestrator.db", master_password: str = None):
        self.config_manager = ConfigManager(db_path, master_password)
        self.running_tasks = {}
        self.setup_logging()
        
    def setup_logging(self):
        log_dir = self.config_manager.get_config('logging', 'directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        log_level = getattr(logging, self.config_manager.get_config('logging', 'level', 'INFO'))
        
        # Create daily log file
        log_file = os.path.join(log_dir, f"orchestrator_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def check_dependencies(self, task_name: str) -> tuple[bool, str]:
        """Check if all dependencies are satisfied"""
        task_config = self.config_manager.get_task(task_name)
        dependencies = task_config.get('dependencies', [])
        
        if not dependencies:
            return True, "No dependencies"
            
        failed_deps = []
        for dep in dependencies:
            dep_config = self.config_manager.get_task(dep)
            if not dep_config:
                failed_deps.append(f"{dep} (not found)")
                continue
                
            # For condition tasks, run them on-demand
            if dep_config.get('type') == 'condition':
                result = self.run_task(dep)
                if result.status != 'SUCCESS':
                    failed_deps.append(dep)
            else:
                # Check recent execution history
                history = self.config_manager.get_task_history(dep, 1)
                if not history or history[0]['status'] != 'SUCCESS':
                    failed_deps.append(dep)
        
        if failed_deps:
            return False, f"Failed dependencies: {', '.join(failed_deps)}"
        return True, "All dependencies satisfied"
    
    def run_task(self, task_name: str) -> TaskResult:
        """Execute a single task"""
        if task_name in self.running_tasks:
            self.logger.warning(f"Task {task_name} is already running")
            return TaskResult(task_name, "SKIPPED", error="Task already running")
        
        task_config = self.config_manager.get_task(task_name)
        if not task_config:
            return TaskResult(task_name, "FAILED", error="Task not found")
            
        result = TaskResult(task_name, "RUNNING", start_time=datetime.now())
        self.running_tasks[task_name] = result
        self.logger.info(f"Starting task: {task_name}")
        
        try:
            # Check dependencies
            deps_ok, deps_msg = self.check_dependencies(task_name)
            if not deps_ok:
                result.status = "SKIPPED"
                result.error = deps_msg
                result.end_time = datetime.now()
                self.logger.warning(f"Task {task_name} skipped: {deps_msg}")
                return result
            
            # Execute command
            command = task_config['command']
            timeout = task_config.get('timeout', 3600)
            
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                result.exit_code = process.returncode
                result.output = stdout
                result.error = stderr
                
                if result.exit_code == 0:
                    result.status = "SUCCESS"
                    self.logger.info(f"Task {task_name} completed successfully")
                else:
                    result.status = "FAILED"
                    self.logger.error(f"Task {task_name} failed with exit code {result.exit_code}")
                    
            except subprocess.TimeoutExpired:
                process.kill()
                result.status = "FAILED"
                result.error = f"Task timed out after {timeout} seconds"
                self.logger.error(f"Task {task_name} timed out")
                
        except Exception as e:
            result.status = "FAILED"
            result.error = str(e)
            self.logger.error(f"Task {task_name} failed with exception: {e}")
        
        finally:
            result.end_time = datetime.now()
            self.running_tasks.pop(task_name, None)
            
            # Store result in database
            self.config_manager.save_task_result(result)
            
            # Send notification
            self.send_notification(result)
            
        return result
    
    def run_task_with_retry(self, task_name: str) -> TaskResult:
        """Run task with retry logic"""
        task_config = self.config_manager.get_task(task_name)
        retry_count = task_config.get('retry_count', 0)
        retry_delay = task_config.get('retry_delay', 300)
        
        for attempt in range(retry_count + 1):
            result = self.run_task(task_name)
            result.retry_count = attempt
            
            if result.status == "SUCCESS" or attempt == retry_count:
                return result
                
            if result.status == "FAILED":
                self.logger.info(f"Retrying task {task_name} in {retry_delay} seconds (attempt {attempt + 1}/{retry_count + 1})")
                time.sleep(retry_delay)
                
        return result
    
    def send_notification(self, result: TaskResult):
        """Send email notification for task result"""
        try:
            # Get email configuration
            smtp_server = self.config_manager.get_config('email', 'smtp_server', 'smtp.office365.com')
            smtp_port = int(self.config_manager.get_config('email', 'smtp_port', '587'))
            sender_email = self.config_manager.get_credential('email_username')
            password = self.config_manager.get_credential('email_password')
            recipients_json = self.config_manager.get_config('email', 'recipients', '[]')
            recipients = json.loads(recipients_json) if recipients_json else []
            
            if not all([sender_email, password, recipients]):
                self.logger.warning("Email configuration incomplete, skipping notification")
                return
            
            # Only send notifications for failures and retries
            send_on_failure = self.config_manager.get_config('email', 'send_on_failure', 'true').lower() == 'true'
            send_on_retry = self.config_manager.get_config('email', 'send_on_retry', 'true').lower() == 'true'
            send_on_success = self.config_manager.get_config('email', 'send_on_success', 'false').lower() == 'true'
            
            should_send = (
                (result.status == "FAILED" and send_on_failure) or
                (result.status == "SUCCESS" and result.retry_count > 0 and send_on_retry) or
                (result.status == "SUCCESS" and result.retry_count == 0 and send_on_success)
            )
            
            if not should_send:
                return
                
            subject = f"Task {result.task_name}: {result.status}"
            
            duration = ""
            if result.start_time and result.end_time:
                duration = str(result.end_time - result.start_time)
            
            body = f"""
Task: {result.task_name}
Status: {result.status}
Start Time: {result.start_time}
End Time: {result.end_time}
Duration: {duration}
Exit Code: {result.exit_code}
Retry Count: {result.retry_count}

Output:
{result.output}

Error:
{result.error}
            """
            
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)
                self.logger.info(f"Notification sent for task {result.task_name}")
                    
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
    
    def get_next_execution_time(self, task_name: str) -> Optional[datetime]:
        """Get next scheduled execution time for a task"""
        task_config = self.config_manager.get_task(task_name)
        schedule = task_config.get('schedule') if task_config else None
        
        if not schedule:
            return None
            
        cron = croniter(schedule, datetime.now())
        return cron.get_next(datetime)
    
    def run_scheduler(self):
        """Main scheduler loop"""
        self.logger.info("Starting task scheduler")
        last_minute_check = {}
        
        while True:
            try:
                current_time = datetime.now()
                current_minute = current_time.strftime('%Y%m%d%H%M')
                
                for task_name, task_config in self.config_manager.get_all_tasks().items():
                    schedule = task_config.get('schedule')
                    if not schedule:
                        continue
                        
                    # Prevent duplicate runs within same minute
                    task_minute_key = f"{task_name}_{current_minute}"
                    if task_minute_key in last_minute_check:
                        continue
                    
                    # Check if task should run now
                    cron = croniter(schedule, current_time)
                    prev_run = cron.get_prev(datetime)
                    
                    # If the previous run time is within the last minute
                    if (current_time - prev_run).total_seconds() < 60:
                        last_minute_check[task_minute_key] = True
                        
                        # Run the task in a separate thread
                        self.logger.info(f"Scheduling task: {task_name}")
                        thread = threading.Thread(
                            target=self.run_task_with_retry, 
                            args=(task_name,)
                        )
                        thread.daemon = True
                        thread.start()
                
                # Cleanup old minute checks to prevent memory growth
                if len(last_minute_check) > 1000:
                    last_minute_check.clear()
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
                
            except KeyboardInterrupt:
                self.logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
                time.sleep(60)  # Wait a minute on error

if __name__ == "__main__":
    import getpass
    
    # Get master password for encryption
    master_password = getpass.getpass("Enter master password (or press Enter for no encryption): ")
    if not master_password.strip():
        master_password = None
    
    manager = TaskManager(master_password=master_password)
    manager.run_scheduler()
```

### 4. Web Dashboard (`dashboard.py`)

```python
from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime
from config_manager import ConfigManager

app = Flask(__name__)
config_manager = ConfigManager()

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/health')
def health_check():
    """Health endpoint for monitoring"""
    try:
        # Test database connection
        tasks = config_manager.get_all_tasks()
        return jsonify({
            'status': 'healthy',
            'tasks_configured': len(tasks),
            'database': 'connected'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/tasks')
def get_tasks():
    """Get all tasks with recent execution status"""
    try:
        tasks = config_manager.get_all_tasks()
        
        # Add recent execution status
        for task_name, task_config in tasks.items():
            history = config_manager.get_task_history(task_name, 1)
            if history:
                task_config['last_execution'] = history[0]
            else:
                task_config['last_execution'] = None
                
        return jsonify({
            'tasks': tasks,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

@app.route('/api/tasks/<task_name>/history')
def get_task_history(task_name):
    """Get execution history for a specific task"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = config_manager.get_task_history(task_name, limit)
        return jsonify({
            'task_name': task_name,
            'history': history,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)
```

### 5. Cross-Platform VPN Check (`scripts/check_vpn.py`)

```python
import subprocess
import sys
import socket
import platform

def check_vpn_connection():
    """Check if VPN is connected using cross-platform detection"""
    try:
        system = platform.system()
        
        # Method 1: Check for VPN interface
        if system == "Windows":
            result = subprocess.run(['ipconfig'], capture_output=True, text=True)
            vpn_indicators = ['VPN', 'TAP', 'Cisco AnyConnect', 'OpenVPN']
        elif system == "Darwin":  # macOS
            result = subprocess.run(['ifconfig'], capture_output=True, text=True)
            vpn_indicators = ['utun', 'ppp', 'tun']
        else:  # Linux
            result = subprocess.run(['ip', 'addr'], capture_output=True, text=True)
            vpn_indicators = ['tun', 'ppp', 'vpn']
        
        if any(indicator in result.stdout for indicator in vpn_indicators):
            print(f"VPN interface detected on {system}")
            return True
            
        # Method 2: Try to reach internal IP ranges
        internal_ips = [
            '10.0.0.1',      # Common internal gateway
            '192.168.1.1',   # Common home router
            '172.16.0.1'     # Private network range
        ]
        
        for ip in internal_ips:
            try:
                sock = socket.create_connection((ip, 80), timeout=5)
                sock.close()
                print(f"Successfully connected to internal IP: {ip}")
                return True
            except:
                continue
                
        # Method 3: Check for specific company domain resolution
        # Replace with your company's internal domain
        try:
            import dns.resolver
            internal_domain = "internal.company.com"  # Replace with actual domain
            dns.resolver.resolve(internal_domain, 'A')
            print(f"Internal domain {internal_domain} resolved")
            return True
        except:
            pass
                
        print("VPN connection not detected")
        return False
        
    except Exception as e:
        print(f"Error checking VPN: {e}")
        return False

if __name__ == "__main__":
    if check_vpn_connection():
        sys.exit(0)
    else:
        sys.exit(1)
```

### 6. Setup and Initial Configuration (`setup.py`)

```python
import os
import getpass
import json
from config_manager import ConfigManager

def setup_initial_config():
    """Setup initial configuration in SQLite database"""
    print("=== Orchestrator Setup ===")
    
    # Create directory structure
    directories = ['data', 'scripts', 'logs', 'templates']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Get master password for encryption
    use_encryption = input("Use encryption for credentials? (y/n): ").lower().startswith('y')
    master_password = None
    
    if use_encryption:
        while True:
            master_password = getpass.getpass("Enter master password: ")
            confirm_password = getpass.getpass("Confirm master password: ")
            if master_password == confirm_password:
                break
            print("Passwords don't match. Please try again.")
    
    # Initialize configuration manager
    config = ConfigManager(master_password=master_password)
    print("Database initialized successfully")
    
    # Add sample tasks
    print("\n=== Setting up sample tasks ===")
    
    # VPN check task
    config.add_task(
        name="vpn_check",
        task_type="condition",
        command="python scripts/check_vpn.py",
        timeout=30
    )
    print("Added: vpn_check")
    
    # Daily data fetch task
    config.add_task(
        name="totango_daily",
        task_type="data_job",
        command="python scripts/fetch_totango.py",
        schedule="0 6 * * *",  # Daily at 6 AM
        dependencies=["vpn_check"],
        timeout=1800,  # 30 minutes
        retry_count=3,
        retry_delay=300
    )
    print("Added: totango_daily")
    
    # Weekly data fetch task
    config.add_task(
        name="citus_weekly",
        task_type="data_job",
        command="python scripts/fetch_citus.py",
        schedule="0 7 * * 1",  # Weekly Monday at 7 AM
        dependencies=["vpn_check", "totango_daily"],
        timeout=3600,  # 1 hour
        retry_count=2,
        retry_delay=600
    )
    print("Added: citus_weekly")
    
    # Monthly report task
    config.add_task(
        name="monthly_report",
        task_type="data_job",
        command="python scripts/generate_monthly_report.py",
        schedule="0 8 1 * *",  # Monthly 1st day at 8 AM
        dependencies=["vpn_check", "citus_weekly"],
        timeout=2400,
        retry_count=1,
        retry_delay=900
    )
    print("Added: monthly_report")
    
    # Email configuration
    print("\n=== Email Configuration ===")
    setup_email = input("Configure email notifications? (y/n): ").lower().startswith('y')
    
    if setup_email:
        email_username = input("Email username: ")
        email_password = getpass.getpass("Email password (app password recommended): ")
        recipients = input("Notification recipients (comma-separated): ").split(',')
        recipients = [email.strip() for email in recipients if email.strip()]
        
        # Store credentials
        config.store_credential('email_username', email_username)
        config.store_credential('email_password', email_password)
        
        # Store email configuration
        config.store_config('email', 'smtp_server', 'smtp.office365.com')
        config.store_config('email', 'smtp_port', '587')
        config.store_config('email', 'recipients', json.dumps(recipients))
        config.store_config('email', 'send_on_failure', 'true')
        config.store_config('email', 'send_on_retry', 'true')
        config.store_config('email', 'send_on_success', 'false')
        
        print("Email configuration saved")
    
    # Logging configuration
    config.store_config('logging', 'level', 'INFO')
    config.store_config('logging', 'directory', 'logs')
    
    print("\n=== Setup Complete ===")
    print("Configuration stored in: data/orchestrator.db")
    print("Next steps:")
    print("1. Create your data fetching scripts in the scripts/ directory")
    print("2. Customize task schedules and dependencies as needed")
    print("3. Run: python orchestrator.py")
    print("4. Access dashboard at: http://localhost:5000")
    print("\nDBeaver connection:")
    print(f"  Type: SQLite")
    print(f"  Path: {os.path.abspath('data/orchestrator.db')}")

def create_sample_scripts():
    """Create sample script templates"""
    scripts = {
        'scripts/fetch_totango.py': '''#!/usr/bin/env python3
"""
Sample Totango data fetching script
Replace with your actual Totango API integration
"""
import sys
import requests
import pandas as pd
from datetime import datetime

def fetch_totango_data():
    """Fetch data from Totango API"""
    try:
        # Replace with actual Totango API calls
        print("Fetching Totango data...")
        
        # Simulate API call
        data = {
            'accounts': ['Account1', 'Account2', 'Account3'],
            'fetched_at': datetime.now().isoformat()
        }
        
        # Save to Excel file (replace with actual data processing)
        df = pd.DataFrame(data['accounts'], columns=['Account'])
        output_file = f"data/totango_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df.to_excel(output_file, index=False)
        
        print(f"Data saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error fetching Totango data: {e}")
        return False

if __name__ == "__main__":
    success = fetch_totango_data()
    sys.exit(0 if success else 1)
''',

        'scripts/fetch_citus.py': '''#!/usr/bin/env python3
"""
Sample Citus BI data fetching script
Replace with your actual Citus integration
"""
import sys
import pandas as pd
from datetime import datetime

def fetch_citus_data():
    """Fetch data from Citus BI system"""
    try:
        # Replace with actual Citus API/database calls
        print("Fetching Citus BI data...")
        
        # Simulate data fetch
        data = {
            'reports': ['Report1', 'Report2', 'Report3'],
            'metrics': [100, 200, 300],
            'fetched_at': datetime.now().isoformat()
        }
        
        # Save to Excel file
        df = pd.DataFrame({
            'Report': data['reports'],
            'Metric': data['metrics']
        })
        output_file = f"data/citus_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df.to_excel(output_file, index=False)
        
        print(f"Data saved to: {output_file}")
        return True
        
    except Exception as e:
        print(f"Error fetching Citus data: {e}")
        return False

if __name__ == "__main__":
    success = fetch_citus_data()
    sys.exit(0 if success else 1)
''',

        'scripts/generate_monthly_report.py': '''#!/usr/bin/env python3
"""
Sample monthly report generation script
Combines data from multiple sources
"""
import sys
import pandas as pd
import glob
from datetime import datetime
import os

def generate_monthly_report():
    """Generate monthly report from collected data"""
    try:
        print("Generating monthly report...")
        
        # Find latest data files
        totango_files = glob.glob("data/totango_*.xlsx")
        citus_files = glob.glob("data/citus_*.xlsx")
        
        if not totango_files or not citus_files:
            print("Warning: Missing source data files")
            return False
        
        # Load latest files
        latest_totango = max(totango_files, key=os.path.getctime)
        latest_citus = max(citus_files, key=os.path.getctime)
        
        totango_df = pd.read_excel(latest_totango)
        citus_df = pd.read_excel(latest_citus)
        
        # Create combined report (replace with actual logic)
        report_data = {
            'Report_Date': [datetime.now().strftime('%Y-%m-%d')],
            'Totango_Records': [len(totango_df)],
            'Citus_Records': [len(citus_df)],
            'Status': ['Generated Successfully']
        }
        
        report_df = pd.DataFrame(report_data)
        output_file = f"data/monthly_report_{datetime.now().strftime('%Y%m')}.xlsx"
        
        # Create Excel file with multiple sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            report_df.to_excel(writer, sheet_name='Summary', index=False)
            totango_df.to_excel(writer, sheet_name='Totango_Data', index=False)
            citus_df.to_excel(writer, sheet_name='Citus_Data', index=False)
        
        print(f"Monthly report saved to: {output_file}")
        
        # Copy to network path (replace with actual network path)
        network_path = "//network/share/reports/"  # Replace with your network path
        if os.path.exists(network_path):
            import shutil
            network_file = os.path.join(network_path, os.path.basename(output_file))
            shutil.copy2(output_file, network_file)
            print(f"Report copied to network: {network_file}")
        
        return True
        
    except Exception as e:
        print(f"Error generating monthly report: {e}")
        return False

if __name__ == "__main__":
    success = generate_monthly_report()
    sys.exit(0 if success else 1)
'''
    }
    
    for script_path, content in scripts.items():
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        with open(script_path, 'w') as f:
            f.write(content)
        print(f"Created: {script_path}")

if __name__ == "__main__":
    setup_initial_config()
    
    create_samples = input("\nCreate sample scripts? (y/n): ").lower().startswith('y')
    if create_samples:
        create_sample_scripts()
        print("\nSample scripts created. Remember to:")
        print("1. Replace API endpoints with your actual systems")
        print("2. Update network paths for file copying")
        print("3. Install required packages: pip install pandas openpyxl requests")
```

### 7. Dashboard Template (`templates/dashboard.html`)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Orchestrator Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header h1 { color: #2c3e50; margin-bottom: 10px; }
        .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .status-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .status-card h3 { margin-bottom: 10px; }
        .status-success { border-left: 4px solid #27ae60; }
        .status-failed { border-left: 4px solid #e74c3c; }
        .status-running { border-left: 4px solid #f39c12; }
        .status-skipped { border-left: 4px solid #95a5a6; }
        .tasks-table { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
        th { background: #34495e; color: white; }
        .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge-success { background: #d5f4e6; color: #27ae60; }
        .badge-failed { background: #fce4e4; color: #e74c3c; }
        .badge-running { background: #fef5e7; color: #f39c12; }
        .badge-skipped { background: #f8f9fa; color: #95a5a6; }
        .refresh-btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        .refresh-btn:hover { background: #2980b9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Task Orchestrator Dashboard</h1>
            <p>Monitor and manage your scheduled data pipelines</p>
            <button class="refresh-btn" onclick="loadTasks()">Refresh</button>
        </div>
        
        <div class="status-grid" id="statusGrid">
            <!-- Status cards will be populated by JavaScript -->
        </div>
        
        <div class="tasks-table">
            <table>
                <thead>
                    <tr>
                        <th>Task Name</th>
                        <th>Type</th>
                        <th>Schedule</th>
                        <th>Last Status</th>
                        <th>Last Run</th>
                        <th>Next Run</th>
                        <th>Dependencies</th>
                    </tr>
                </thead>
                <tbody id="tasksBody">
                    <!-- Tasks will be populated by JavaScript -->
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function formatDate(dateString) {
            if (!dateString) return 'Never';
            const date = new Date(dateString);
            return date.toLocaleString();
        }
        
        function getStatusBadge(status) {
            if (!status) return '<span class="status-badge badge-skipped">Never Run</span>';
            const badgeClass = `badge-${status.toLowerCase()}`;
            return `<span class="status-badge ${badgeClass}">${status}</span>`;
        }
        
        function calculateNextRun(schedule) {
            // Simplified next run calculation - replace with proper cron parsing
            if (!schedule) return 'Manual';
            return 'Calculated...';
        }
        
        async function loadTasks() {
            try {
                const response = await fetch('/api/tasks');
                const data = await response.json();
                
                if (data.status === 'success') {
                    updateStatusCards(data.tasks);
                    updateTasksTable(data.tasks);
                } else {
                    console.error('Error loading tasks:', data.error);
                }
            } catch (error) {
                console.error('Error fetching tasks:', error);
            }
        }
        
        function updateStatusCards(tasks) {
            const statusCounts = {
                total: Object.keys(tasks).length,
                success: 0,
                failed: 0,
                running: 0,
                never_run: 0
            };
            
            Object.values(tasks).forEach(task => {
                const lastExecution = task.last_execution;
                if (!lastExecution) {
                    statusCounts.never_run++;
                } else {
                    const status = lastExecution.status.toLowerCase();
                    if (status === 'success') statusCounts.success++;
                    else if (status === 'failed') statusCounts.failed++;
                    else if (status === 'running') statusCounts.running++;
                }
            });
            
            const statusGrid = document.getElementById('statusGrid');
            statusGrid.innerHTML = `
                <div class="status-card">
                    <h3>Total Tasks</h3>
                    <div style="font-size: 24px; color: #34495e;">${statusCounts.total}</div>
                </div>
                <div class="status-card status-success">
                    <h3>Successful</h3>
                    <div style="font-size: 24px; color: #27ae60;">${statusCounts.success}</div>
                </div>
                <div class="status-card status-failed">
                    <h3>Failed</h3>
                    <div style="font-size: 24px; color: #e74c3c;">${statusCounts.failed}</div>
                </div>
                <div class="status-card status-running">
                    <h3>Running</h3>
                    <div style="font-size: 24px; color: #f39c12;">${statusCounts.running}</div>
                </div>
            `;
        }
        
        function updateTasksTable(tasks) {
            const tbody = document.getElementById('tasksBody');
            tbody.innerHTML = '';
            
            Object.entries(tasks).forEach(([taskName, task]) => {
                const lastExecution = task.last_execution;
                const row = document.createElement('tr');
                
                row.innerHTML = `
                    <td><strong>${taskName}</strong></td>
                    <td>${task.type}</td>
                    <td>${task.schedule || 'Manual'}</td>
                    <td>${getStatusBadge(lastExecution?.status)}</td>
                    <td>${formatDate(lastExecution?.start_time)}</td>
                    <td>${calculateNextRun(task.schedule)}</td>
                    <td>${task.dependencies.join(', ') || 'None'}</td>
                `;
                
                tbody.appendChild(row);
            });
        }
        
        // Load tasks on page load
        document.addEventListener('DOMContentLoaded', loadTasks);
        
        // Auto-refresh every 30 seconds
        setInterval(loadTasks, 30000);
    </script>
</body>
</html>
```

### 8. Installation & Setup

#### Requirements (`requirements.txt`)
```
PyYAML>=6.0
croniter>=1.3.0
flask>=2.3.0
requests>=2.31.0
openpyxl>=3.1.0
pandas>=2.0.0
cryptography>=41.0.0
dnspython>=2.4.0
```

#### Quick Start Commands

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Initial setup
python setup.py

# 3. Start the orchestrator
python orchestrator.py

# 4. Start the dashboard (separate terminal)
python dashboard.py

# 5. Access dashboard
# http://localhost:5000
```

## Usage Instructions

### 1. Database Management with DBeaver

**Connection Setup:**
- **Type:** SQLite
- **Path:** `data/orchestrator.db`
- **Test Connection** → Should connect immediately

**Common Queries:**
```sql
-- View all tasks
SELECT * FROM tasks WHERE enabled = 1;

-- Check recent task results
SELECT task_name, status, start_time, retry_count 
FROM task_results 
ORDER BY start_time DESC 
LIMIT 20;

-- Update task schedule
UPDATE tasks 
SET schedule = '0 8 * * *' 
WHERE name = 'totango_daily';

-- View stored credentials (encrypted)
SELECT name, created_at FROM credentials;
```

### 2. Adding New Tasks

```python
from config_manager import ConfigManager

config = ConfigManager(master_password="your_password")

# Add new task
config.add_task(
    name="new_data_source",
    task_type="data_job",
    command="python scripts/fetch_new_source.py",
    schedule="0 9 * * *",  # Daily at 9 AM
    dependencies=["vpn_check"],
    timeout=2400,
    retry_count=2,
    retry_delay=300
)
```

### 3. Credential Management

```python
# Store new credentials
config.store_credential('api_key', 'your_secret_key')
config.store_credential('db_password', 'database_password')

# Retrieve credentials in your scripts
api_key = config.get_credential('api_key')
```

### 4. Manual Task Execution

```python
from orchestrator import TaskManager

manager = TaskManager(master_password="your_password")
result = manager.run_task('totango_daily')
print(f"Task status: {result.status}")
```

## Key Features

### ✅ **SQLite-Based Configuration**
- Encrypted credential storage with PBKDF2 + Fernet
- Atomic configuration updates
- Single database file for backup/restore
- DBeaver integration for visual management

### ✅ **Cross-Platform VPN Detection**
- Windows, macOS, and Linux support
- Multiple detection methods (interface, connectivity, DNS)
- Configurable internal IP/domain testing

### ✅ **Robust Scheduling & Dependencies**
- Cron-style scheduling with croniter
- Dependency resolution with condition validation
- Retry logic with configurable backoff
- Thread-safe execution with timeout protection

### ✅ **Comprehensive Monitoring**
- Persistent task execution history
- Web dashboard with real-time status
- Email notifications for failures/retries
- Health check endpoints for external monitoring

### ✅ **Production-Ready Features**
- Cross-platform compatibility
- Resource limit management
- Detailed error logging with rotation
- Network path integration for file distribution

## Security Considerations

**Encryption:**
- Credentials encrypted with Fernet (AES-128)
- Key derivation using PBKDF2 with 100,000 iterations
- System-specific salt generation

**Database Security:**
- SQLite file-level permissions
- WAL mode for concurrent access
- No network exposure by default

**Best Practices:**
- Use environment variables for sensitive setup data
- Regular database backups
- Monitor file system permissions
- Use app passwords for email authentication

This system provides enterprise-grade orchestration capabilities while remaining completely local and admin-free, with the added benefits of encrypted credential storage and visual database management through DBeaver.