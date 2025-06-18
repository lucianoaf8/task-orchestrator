from flask import Flask, render_template, jsonify, request
import json
import subprocess
import sys
from datetime import datetime
from orchestrator.core.config_manager import ConfigManager

app = Flask(__name__, template_folder="../../templates")

# Register new API blueprint (Phase 4)
try:
    from orchestrator.web.api.routes import api_bp

    app.register_blueprint(api_bp)
except Exception as exc:  # pragma: no cover – ensure dashboard still works even if API fails
    import logging

    logging.getLogger(__name__).warning("API blueprint failed to register: %s", exc)

config_manager = ConfigManager()

# Existing endpoints...
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

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

# @app.route('/api/tasks')
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

# @app.route('/api/tasks/<task_name>/history')
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

# NEW ENDPOINTS FOR TASK MANAGEMENT

# @app.route('/api/tasks', methods=['POST'])
def add_or_update_task():
    """Add new task or update existing task"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'type', 'command']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate task name format
        task_name = data['name'].strip()
        if not task_name or ' ' in task_name:
            return jsonify({
                'status': 'error',
                'error': 'Task name cannot be empty or contain spaces'
            }), 400
        
        # Validate cron schedule if provided
        schedule = data.get('schedule', '').strip()
        if schedule:
            try:
                from croniter import croniter
                croniter(schedule)  # This will raise an exception if invalid
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'error': f'Invalid cron schedule: {str(e)}'
                }), 400
        
        # Add/update task in database
        config_manager.add_task(
            name=task_name,
            task_type=data['type'],
            command=data['command'],
            schedule=schedule if schedule else None,
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

# @app.route('/api/tasks/<task_name>', methods=['DELETE'])
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
            schedule=task['schedule'],
            timeout=task['timeout'],
            retry_count=task['retry_count'],
            retry_delay=task['retry_delay'],
            dependencies=task['dependencies'],
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

# @app.route('/api/test-command', methods=['POST'])
def test_command():
    """Test a command without adding it as a task"""
    try:
        data = request.get_json()
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

# @app.route('/api/tasks/<task_name>/run', methods=['POST'])
def run_task_manually(task_name):
    """Manually trigger a task execution"""
    try:
        # TODO: This will need to be updated when we implement the new orchestrator
        # For now, return a placeholder response
        return jsonify({
            'status': 'success',
            'message': f'Task {task_name} execution requested (feature pending orchestrator redesign)'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/task-manager')
def task_manager_ui():
    """Serve the task management UI"""
    return render_template('task-manager-ui.html')

@app.route('/compact-scheduler')
def compact_scheduler_ui():
    """Serve the compact task scheduler UI"""
    return render_template('compact-task-scheduler.html')

def create_app():
    """Application factory function"""
    return app

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)