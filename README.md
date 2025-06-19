# Task Python Orchestrator

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Enterprise-grade task scheduling and monitoring for Windows environments**

A secure, local-first orchestration platform that bridges Python automation with Windows Task Scheduler. Perfect for SMBs needing robust data pipelines without complex infrastructure.

## ✨ Features

- 🔒 **Encrypted Credentials** - Fernet encryption, no plaintext secrets
- 🎛️ **Multiple Interfaces** - Web UI, CLI, and interactive modes
- 📊 **Real-time Monitoring** - Live dashboard with execution history
- 📧 **Smart Notifications** - Email alerts and daily HTML reports
- 🔄 **Retry Logic** - Configurable retry policies with exponential backoff
- 🌐 **Cross-platform** - VPN detection and dependency checking
- 🧪 **Production Ready** - Comprehensive testing and error handling

## 🚀 Quick Start

### 1. Install & Setup
```bash
# Clone repository
git clone https://github.com/your-org/task-python-orchestrator.git
cd task-python-orchestrator

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python setup.py
```

### 2. Create Your First Task
```bash
# Interactive mode (recommended for beginners)
python main.py

# Or use the web interface
python -m orchestrator.web.dashboard
# Open: http://localhost:5000
```

### 3. Schedule & Monitor
```bash
# Schedule task in Windows Task Scheduler
python orc.py --schedule my_task

# Monitor via dashboard or CLI
python orc.py --list
```

## 🎯 Common Use Cases

### Data Pipeline Automation
```python
# Daily data extraction from APIs
{
    "name": "daily_customer_sync",
    "type": "data_job",
    "command": "python scripts/sync_customers.py",
    "schedule": "0 6 * * *",  # Daily at 6 AM
    "timeout": 3600,
    "retry_count": 3,
    "dependencies": ["vpn_check"]
}
```

### Report Generation
```python
# Weekly sales reports with email distribution
{
    "name": "weekly_sales_report",
    "type": "report", 
    "command": "python scripts/generate_sales_report.py",
    "schedule": "0 8 * * 1",  # Monday at 8 AM
    "dependencies": ["daily_customer_sync"]
}
```

### System Maintenance
```python
# Database cleanup and optimization
{
    "name": "db_maintenance",
    "type": "maintenance",
    "command": "python scripts/cleanup_database.py", 
    "schedule": "0 2 1 * *",  # Monthly at 2 AM
    "timeout": 7200
}
```

## 🎛️ Interfaces

| Interface | Best For | Command |
|-----------|----------|---------|
| **Interactive** | Beginners, one-off tasks | `python main.py` |
| **Web Dashboard** | Visual management | `python -m orchestrator.web.dashboard` |
| **Core CLI** | Production automation | `python orc.py --schedule my_task` |
| **Advanced CLI** | Power users | `python -m orchestrator.cli schedule --task my_task` |
| **REST API** | Integration | `curl -X POST http://localhost:5000/api/tasks` |

## 📊 Web Dashboard

The built-in dashboard provides:

- **Real-time Status Grid** - Live task execution status
- **Visual Task Manager** - Drag-and-drop task creation  
- **Execution History** - Detailed logs and trends
- **Email Configuration** - Notification setup
- **System Health** - Database and scheduler status

![Dashboard Preview](docs/dashboard-preview.png)

## 🔧 Configuration

### Email Notifications
```bash
# Setup via interactive wizard
python setup.py

# Or programmatically
from orchestrator.core.config_manager import ConfigManager
cm = ConfigManager(master_password="your_secure_password")

cm.store_credential('email_username', 'alerts@company.com')
cm.store_credential('email_password', 'app_password')
cm.store_config('email', 'recipients', '["admin@company.com"]')
```

### Schedule Formats
```bash
# Cron expressions (traditional)
"0 6 * * *"        # Daily at 6 AM
"*/30 * * * *"     # Every 30 minutes
"0 8 * * 1"        # Weekly Monday at 8 AM

# Windows-style (simplified)
"06:00"            # Daily at 6:00 AM  
"MON 08:00"        # Weekly Monday at 8:00 AM
"15 09:30"         # Monthly 15th at 9:30 AM
```

### Dependencies
```python
"dependencies": [
    "vpn_check",                    # Task name dependency
    "file:/path/to/data.csv",      # File existence  
    "url:https://api.com/health",   # URL health check
    "command:ping -c 1 server"     # Command success
]
```

## 🧪 Testing & Validation

### Full System Test
```bash
# Automated task lifecycle simulation
python tools/task_simulator.py

# With custom schedule
python tools/task_simulator.py --update-schedule "*/2 * * * *"

# Keep task for debugging  
python tools/task_simulator.py --keep-task
```

### Component Tests
```bash
# Run test suite
python -m pytest tests/

# Test setup validation
python test_setup.py

# Debug task creation
python tools/task_creation_debugger.py
```

## 📁 Project Structure

```
task-python-orchestrator/
├── orchestrator/           # Core package
│   ├── core/              # Business logic (ConfigManager, TaskScheduler)
│   ├── utils/             # Windows integration, cron conversion
│   ├── web/               # Flask app, dashboard, API
│   └── legacy/            # Backward compatibility
├── scripts/               # User automation scripts
├── templates/             # Web UI templates
├── tests/                 # Comprehensive test suite
├── tools/                 # Development utilities
├── main.py               # Interactive entry point
└── orc.py                # Core orchestrator CLI
```

## 🔒 Security Features

- **Encrypted Storage** - All credentials encrypted with Fernet (AES-128)
- **No Hardcoded Secrets** - Secure credential management
- **Audit Trail** - Complete execution history
- **Local-Only** - No cloud dependencies or data transmission
- **Windows Integration** - Leverages OS-level task scheduling

## 🚨 Troubleshooting

### Common Issues

**"Database locked" errors:**
```bash
# Check for zombie processes and restart
ps aux | grep orchestrator
```

**Windows Task Scheduler fails:**
```bash
# Verify task exists
schtasks /query /tn "\Orchestrator\Orc_my_task"

# Run diagnostics
python tools/task_creation_debugger.py
```

**Permission denied:**
- Run initial setup as Administrator
- Check Python executable permissions
- Verify Windows Task Scheduler access

### Get Help

- 📖 **Full Documentation**: See [DOCUMENTATION.md](DOCUMENTATION.md)
- 🐛 **Bug Reports**: Open an issue on GitHub
- 💬 **Questions**: Start a discussion
- 📧 **Email**: support@your-org.com

## 📈 Performance Tips

- **Task Design**: Keep tasks atomic and idempotent
- **Scheduling**: Avoid overlapping executions with proper timeouts
- **Dependencies**: Use condition tasks for prerequisite checking
- **Monitoring**: Regular cleanup of old logs and execution history
- **Resources**: Monitor system resources during peak times

## 🔮 What's Next?

- 📱 **Mobile Dashboard** - PWA for mobile monitoring
- 🌐 **Multi-node Support** - Distributed task execution
- 📊 **Advanced Metrics** - Prometheus/Grafana integration
- 🔌 **Plugin System** - Custom task types and integrations
- ☁️ **Cloud Connectors** - Azure, AWS integration options

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⭐ Support

If this project helps you, please consider giving it a star! ⭐

---

**Made with ❤️ for the Python automation community**