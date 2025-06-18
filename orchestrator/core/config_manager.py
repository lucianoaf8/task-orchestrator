import os
import sqlite3
import json
import base64
import platform
from datetime import datetime
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