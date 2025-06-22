import os
import sqlite3
import json
import base64
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Any as AnyType

from .migrations import apply_pending_migrations
from .config_schema import CONFIG_SCHEMA
from .database_transaction import DatabaseTransaction, TransactionError
from orchestrator.utils.windows_scheduler import WindowsScheduler
from orchestrator.utils.cron_converter import CronConverter
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class ConfigManager:
    def __init__(self, db_path: str = "data/orchestrator.db", master_password: Optional[str] = None):
        """Create a new `ConfigManager`.

        When the orchestrator is executed by Windows Task Scheduler the
        current working directory defaults to *C:\Windows\System32*.
        Any *relative* database path would therefore point to the wrong
        location and a fresh, empty SQLite file would be created there.
        That in turn makes `orc.py --task <name>` fail because it cannot
        find the task definition.

        To avoid this class of bugs we resolve relative `db_path` values
        against the *project root* (the parent of the top-level
        `orchestrator` package) before opening the connection.
        """
        # ----------------------------------------------------------
        # Resolve *relative* database paths against the repo root
        # ----------------------------------------------------------
        if not os.path.isabs(db_path):
            project_root = Path(__file__).resolve().parents[2]
            db_path = str(project_root / db_path)

        self.db_path = db_path

        # Ensure directory exists irrespective of the CWD
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cipher = self._init_cipher(master_password) if master_password else None
        self._init_db()
        self._check_migrations()
        
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
    
    def _init_db(self) -> None:
        """Initialise the SQLite schema.

        If the underlying file is *not* a valid SQLite database (commonly caused
        by previous bad writes or an accidental overwrite), the file is backed
        up with the suffix ``.corrupt-YYYYMMDD-HHMMSS`` and a fresh database is
        created automatically. This prevents the orchestrator from crashing on
        start-up while still preserving the corrupt artefact for manual
        inspection.
        """

        try:
            # Enable WAL mode for better concurrency
            self.db.execute("PRAGMA journal_mode=WAL")

            # Create tables (idempotent)
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
        except sqlite3.DatabaseError as exc:
            # Detect corruption and attempt automatic recovery.
            if "file is not a database" in str(exc).lower():
                # Close the bad connection first
                self.db.close()

                # Backup the corrupted file so we don't lose forensic data
                timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                backup_path = f"{self.db_path}.corrupt-{timestamp}"
                os.replace(self.db_path, backup_path)
                print(
                    f"[WARNING] Detected corrupted database file. A backup has "
                    f"been saved to '{backup_path}'. Creating a fresh DB…"
                )

                # Re-create the connection and retry initialisation once
                self.db = sqlite3.connect(self.db_path, check_same_thread=False)
                self._init_db()  # recursion will execute only once
            else:
                # Propagate unknown errors
                raise
    
    def add_task(self, name: str, task_type: str, command: str,
                 schedule: Optional[str] = None, **kwargs):
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
    
    # ------------------------------------------------------------------
    # Query helpers (Phase C1) -----------------------------------------
    # ------------------------------------------------------------------
    def get_tasks_paginated(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        enabled_only: bool = True,
        fields: list[str] | None = None,
    ) -> list[Dict[str, Any]]:
        """Return up to *limit* tasks starting at *offset*.

        Provides light pagination for dashboards / APIs.
        """
        cols = ", ".join(fields) if fields else "*"
        sql = f"SELECT {cols} FROM tasks"
        if enabled_only:
            sql += " WHERE enabled=1"
        sql += " ORDER BY name LIMIT ? OFFSET ?"
        cursor = self.db.execute(sql, (limit, offset))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result: list[Dict[str, Any]] = []
        for row in rows:
            task = dict(zip(columns, row))
            if "dependencies" in task:
                task["dependencies"] = json.loads(task["dependencies"])
            result.append(task)
        return result

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
    
    # ------------------------------------------------------------------
    # Configuration validation helpers
    # ------------------------------------------------------------------

    def _validate_config(self, section: str, key: str, value):
        """Validate *value* against :pydata:`CONFIG_SCHEMA`."""
        if section not in CONFIG_SCHEMA or key not in CONFIG_SCHEMA[section]:
            # Unknown keys allowed for forward compatibility
            return value

        rules = CONFIG_SCHEMA[section][key]
        expected_type = rules.get("type")
        if expected_type and not isinstance(value, expected_type):
            raise TypeError(f"{section}.{key} must be {expected_type.__name__}")

        if "range" in rules:
            lo, hi = rules["range"]
            if not (lo <= value <= hi):
                raise ValueError(f"{section}.{key} out of range {lo}-{hi}")

        if validator := rules.get("validator"):
            value = validator(value)
        return value

    def store_config(self, section: str, key: str, value: AnyType):
        """Validate and persist configuration value."""
        validated_value = self._validate_config(section, key, value)
        self.db.execute(
            "INSERT OR REPLACE INTO config VALUES (?, ?, ?)",
            (section, key, validated_value),
        )
        self.db.commit()
    
    def get_config(self, section: str, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration value"""
        result = self.db.execute("SELECT value FROM config WHERE section=? AND key=?", 
                                (section, key)).fetchone()
        return result[0] if result else default
    
    def _check_migrations(self) -> None:
        """Apply pending database migrations safely."""
        apply_pending_migrations(self.db)

    # ------------------------------------------------------------------
    # Transactional operations
    # ------------------------------------------------------------------
    def add_task_with_scheduling(self, task_data: Dict[str, Any]):
        """Atomically insert a task and schedule it if enabled.

        Raises TransactionError if scheduling fails so that the DB changes
        are rolled back.
        """
        with DatabaseTransaction(self.db):
            self.add_task(**task_data)
            if task_data.get("enabled") and task_data.get("schedule"):
                if not self._schedule_task(task_data["name"]):
                    raise TransactionError("Scheduling failed")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _schedule_task(self, task_name: str) -> bool:
        """Schedule *task_name* via Windows Task Scheduler."""
        task = self.get_task(task_name)
        if not task or not task.get("schedule"):
            return False
        scheduler = WindowsScheduler()
        params = CronConverter.cron_to_schtasks_params(task["schedule"])
        return scheduler.create_task(task_name, task["command"], params, description=f"Orchestrator – {task_name}")

    # ------------------------------------------------------------------
    # Existing API below
    # ------------------------------------------------------------------
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