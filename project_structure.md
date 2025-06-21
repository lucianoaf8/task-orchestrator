# Project Structure: task-python-orchestrator

```
[ROOT] task-python-orchestrator
|-- [DIR] config
|   |-- [PY]  __init__.py
|   |-- [PY]  settings.py
|-- [DIR] orchestrator
|   |-- [DIR] core
|   |   |-- [PY]  __init__.py
|   |   |-- [PY]  config_manager.py
|   |   |-- [PY]  scheduler.py
|   |   |-- [PY]  task_result.py
|   |-- [DIR] legacy
|   |   |-- [PY]  __init__.py
|   |   |-- [PY]  task_manager.py
|   |-- [DIR] utils
|   |   |-- [PY]  __init__.py
|   |   |-- [PY]  configure.py
|   |   |-- [PY]  cron_converter.py
|   |   |-- [PY]  windows_scheduler.py
|   |-- [DIR] web
|   |   |-- [DIR] api
|   |   |   |-- [PY]  __init__.py
|   |   |   |-- [PY]  routes.py
|   |   |-- [PY]  __init__.py
|   |   |-- [PY]  app.py
|   |   |-- [PY]  dashboard.py
|   |-- [PY]  __init__.py
|   |-- [PY]  cli.py
|-- [DIR] scripts
|   |-- [DIR] checks
|   |   |-- [PY]  __init__.py
|   |   |-- [PY]  check_db_connection.py
|   |   |-- [PY]  check_dependencies.py
|   |   |-- [PY]  check_vpn.py
|   |-- [DIR] notifications
|   |   |-- [PY]  __init__.py
|   |   |-- [PY]  daily_email_main.py
|   |   |-- [PY]  daily_report.py
|   |-- [PY]  __init__.py
|   |-- [SCRIPT] start-dashboard.ps1
|   |-- [PY]  test_task.py
|   |-- [PY]  write_marker.py
|-- [DIR] templates
|   |-- [HTML] compact-task-scheduler.html
|   |-- [HTML] dashboard.html
|   |-- [FILE] scheduled_task_template.xml
|   |-- [HTML] task-manager-ui.html
|-- [DIR] tests
|   |-- [DIR] test_outputs
|   |-- [PY]  __init__.py
|   |-- [PY]  test_cron_and_scripts.py
|   |-- [PY]  test_email_notifications.py
|   |-- [PY]  test_end_to_end.py
|   |-- [PY]  test_imports.py
|   |-- [PY]  test_migration.py
|   |-- [PY]  test_scheduler.py
|   |-- [PY]  test_web_integration.py
|   |-- [PY]  test_windows_integration.py
|   |-- [PY]  web_api_flow_test.py
|-- [DIR] tools
|   |-- [PY]  __init__.py
|   |-- [PY]  cleanup.py
|   |-- [PY]  migration.py
|   |-- [PY]  task_creation_debugger.py
|-- [FILE] .gitignore
|-- [SCRIPT] Get-TreeProject.ps1
|-- [PY]  main.py
|-- [PY]  orc.py
|-- [MD]  project_documentation.md
|-- [MD]  project_structure.md
|-- [MD]  project-analysis.md
|-- [TOML] pyproject.toml
|-- [MD]  README.md
```

## Summary

- **Total Items Displayed**: 71
- **Project Root**: `C:\Projects\task-python-orchestrator`

