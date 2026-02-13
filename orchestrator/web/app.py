from flask import Flask, render_template, jsonify, request
import os
import json
import subprocess
import sys
from datetime import datetime
from orchestrator.core.config_manager import ConfigManager
from orchestrator.utils.cron_converter import CronConverter

def create_app():
    """Application factory function"""
    app = Flask(__name__, template_folder="../../templates")

    # Initialize config manager
    config_manager = ConfigManager()

    # Register new API blueprint (Phase 4)
    try:
        from orchestrator.web.api.routes import api_bp
        app.register_blueprint(api_bp)
        print("✓ API blueprint registered successfully")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("API blueprint failed to register: %s", exc)
        print(f"⚠️  API blueprint registration failed: {exc}")

    # Main dashboard routes
    @app.route('/')
    def dashboard():
        return render_template('dashboard.html')

    @app.route('/task-manager')
    def task_manager_ui():
        """Serve the task management UI"""
        return render_template('task-manager-ui.html')

    @app.route('/compact-scheduler')
    def compact_scheduler_ui():
        """Serve the compact task scheduler UI"""
        return render_template('compact-task-scheduler.html')

    # Legacy health endpoint (non-API)
    @app.route('/health')
    def health_check():
        """Health endpoint for monitoring"""
        try:
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

    # API endpoints that might be missing from blueprint
    @app.route('/api/tasks')
    def get_tasks():
        """Get all tasks with recent execution status"""
        try:
            tasks = config_manager.get_all_tasks()
            
            # Add recent execution status
            for task_name, task_config in tasks.items():
                try:
                    history = config_manager.get_task_history(task_name, 1)
                    if history:
                        task_config['last_execution'] = history[0]
                    else:
                        task_config['last_execution'] = None
                except Exception:
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
        """Get task execution history"""
        try:
            limit = request.args.get('limit', 10, type=int)
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

    @app.route('/api/tasks/<task_name>', methods=['POST'])
    def create_or_update_task(task_name):
        """Create or update a task"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'error': 'No JSON data provided'
                }), 400
            
            # Validate required fields
            required_fields = ['type', 'command']
            for field in required_fields:
                if field not in data:
                    return jsonify({
                        'status': 'error',
                        'error': f'Missing required field: {field}'
                    }), 400
            
            # Validate cron expression if provided
            if 'schedule' in data and data['schedule']:
                try:
                    converter = CronConverter()
                    is_valid, error_msg = converter.validate_cron_expression(data['schedule'])
                    if not is_valid:
                        return jsonify({
                            'status': 'error',
                            'error': f'Invalid cron expression: {error_msg}'
                        }), 400
                except Exception:
                    # If CronConverter fails, do basic validation
                    parts = data['schedule'].strip().split()
                    if len(parts) != 5:
                        return jsonify({
                            'status': 'error',
                            'error': 'Invalid cron expression: must have 5 parts'
                        }), 400
            
            # Save task to database
            config_manager.add_task(
                name=task_name,
                task_type=data['type'],
                command=data['command'],
                schedule=data.get('schedule'),
                timeout=data.get('timeout', 3600),
                retry_count=data.get('retry_count', 0),
                retry_delay=data.get('retry_delay', 300),
                dependencies=data.get('dependencies', []),
                enabled=data.get('enabled', True)
            )
            
            return jsonify({
                'status': 'success',
                'message': f'Task {task_name} saved successfully'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/api/tasks/<task_name>', methods=['DELETE'])
    def delete_task(task_name):
        """Delete a task"""
        try:
            # Check if task exists
            task = config_manager.get_task(task_name)
            if not task:
                return jsonify({
                    'status': 'error',
                    'error': 'Task not found'
                }), 404
            
            # Disable task instead of deleting (safer)
            config_manager.add_task(
                name=task_name,
                task_type=task['type'],
                command=task['command'],
                schedule=task.get('schedule'),
                timeout=task.get('timeout', 3600),
                retry_count=task.get('retry_count', 0),
                retry_delay=task.get('retry_delay', 300),
                dependencies=task.get('dependencies', []),
                enabled=False
            )
            
            return jsonify({
                'status': 'success',
                'message': f'Task {task_name} disabled successfully'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/api/tasks/<task_name>/run', methods=['POST'])
    def run_task_manually(task_name):
        """Manually trigger a task execution"""
        try:
            # Check if task exists
            task = config_manager.get_task(task_name)
            if not task:
                return jsonify({
                    'status': 'error',
                    'error': 'Task not found'
                }), 404
            
            # For now, just return success - actual execution would be implemented later
            return jsonify({
                'status': 'success',
                'message': f'Task {task_name} execution requested'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/api/test-command', methods=['POST'])
    def test_command():
        """Test a command without adding it as a task"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'error': 'No JSON data provided'
                }), 400
                
            command = data.get('command', '').strip()
            
            if not command:
                return jsonify({
                    'status': 'error',
                    'error': 'No command provided'
                }), 400
            
            # Run command with timeout
            try:
                result = subprocess.run(
                    command.split(),
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout for testing
                )
                
                return jsonify({
                    'status': 'success',
                    'exit_code': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                })
                
            except subprocess.TimeoutExpired:
                return jsonify({
                    'status': 'error',
                    'error': 'Command timed out (30 seconds)'
                }), 400
                
            except FileNotFoundError:
                return jsonify({
                    'status': 'error',
                    'error': 'Command not found - check if the script/executable exists'
                }), 400
                
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Backup endpoints in case blueprint doesn't register
    @app.route('/api/system/scheduler-status')
    def scheduler_status_backup():
        """Backup scheduler status endpoint"""
        try:
            tasks = config_manager.get_all_tasks()
            configured = len(tasks)
            
            # Try to get scheduled count from Windows Task Scheduler
            scheduled = 0
            try:
                from orchestrator.services import get_scheduling_service
                scheduler = get_scheduling_service()
                scheduled_tasks = scheduler.list_tasks()
                scheduled = len(scheduled_tasks) if scheduled_tasks else 0
            except Exception:
                pass
            
            return jsonify({
                'status': 'success',
                'configured': configured,
                'scheduled': scheduled
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        # Log the 404 for debugging
        print(f"404 Error: {request.method} {request.path}")
        return jsonify({
            'status': 'error',
            'error': 'Not found',
            'path': request.path
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'status': 'error',
            'error': 'Internal server error'
        }), 500

    # Add debug route to list all routes
    @app.route('/debug/routes')
    def list_routes():
        """Debug endpoint to list all registered routes"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
        return jsonify({'routes': routes})

    return app

# For backward compatibility
app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Task Orchestrator Dashboard")
    print("📍 Available at: http://localhost:5000")
    print("🔧 Debug routes at: http://localhost:5000/debug/routes")
    app.run(host='localhost', port=5000, debug=True)