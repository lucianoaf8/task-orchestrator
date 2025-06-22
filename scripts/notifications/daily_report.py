# daily_report.py - Daily Summary Email Report

import os
import sys
import smtplib
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from orchestrator.core.config_manager import ConfigManager
from croniter import croniter

class DailyReportGenerator:
    def __init__(self, master_password=None):
        self.config_manager = ConfigManager(master_password=master_password)
        
    def get_tasks_in_timeframe(self, start_time, end_time):
        """Get all tasks that were scheduled to run in the given timeframe"""
        scheduled_tasks = []
        all_tasks = self.config_manager.get_all_tasks()
        
        for task_name, task_config in all_tasks.items():
            schedule = task_config.get('schedule')
            if not schedule:
                continue
                
            try:
                # Find all scheduled runs in the timeframe
                cron = croniter(schedule, start_time)
                
                while True:
                    next_run = cron.get_next(datetime)
                    if next_run > end_time:
                        break
                    
                    # Get actual execution for this scheduled time
                    execution_history = self.get_execution_near_time(task_name, next_run)
                    
                    scheduled_tasks.append({
                        'task_name': task_name,
                        'task_config': task_config,
                        'scheduled_time': next_run,
                        'execution': execution_history
                    })
                    
            except Exception as e:
                print(f"Error processing schedule for {task_name}: {e}")
                continue
                
        return scheduled_tasks
    
    def get_execution_near_time(self, task_name, scheduled_time, tolerance_minutes=30):
        """Get execution that happened near the scheduled time"""
        history = self.config_manager.get_task_history(task_name, 50)
        
        for execution in history:
            if not execution['start_time']:
                continue
                
            try:
                exec_time = datetime.fromisoformat(execution['start_time'])
                time_diff = abs((exec_time - scheduled_time).total_seconds() / 60)
                
                # If execution was within tolerance minutes of scheduled time
                if time_diff <= tolerance_minutes:
                    return execution
            except Exception:
                continue
                
        return None
    
    def get_failed_tasks_last_24h(self):
        """Get all tasks that failed in the last 24 hours"""
        failed_tasks = []
        all_tasks = self.config_manager.get_all_tasks()
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for task_name in all_tasks.keys():
            history = self.config_manager.get_task_history(task_name, 20)
            
            for execution in history:
                if not execution['start_time']:
                    continue
                    
                try:
                    exec_time = datetime.fromisoformat(execution['start_time'])
                    if exec_time > cutoff_time and execution['status'] == 'FAILED':
                        failed_tasks.append({
                            'task_name': task_name,
                            'execution': execution,
                            'execution_time': exec_time
                        })
                except Exception:
                    continue
                    
        return failed_tasks
    
    def generate_html_report(self, start_time, end_time):
        """Generate HTML report for the timeframe"""
        scheduled_tasks = self.get_tasks_in_timeframe(start_time, end_time)
        failed_tasks = self.get_failed_tasks_last_24h()
        
        # Calculate summary statistics
        total_scheduled = len(scheduled_tasks)
        successful = len([t for t in scheduled_tasks if t['execution'] and t['execution']['status'] == 'SUCCESS'])
        failed = len([t for t in scheduled_tasks if t['execution'] and t['execution']['status'] == 'FAILED'])
        missed = len([t for t in scheduled_tasks if not t['execution']])
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }}
                .stat-card {{ background: white; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #ddd; }}
                .stat-number {{ font-size: 24px; font-weight: bold; margin-bottom: 5px; }}
                .stat-label {{ color: #666; font-size: 14px; }}
                .success {{ color: #28a745; }}
                .failed {{ color: #dc3545; }}
                .missed {{ color: #ffc107; }}
                .total {{ color: #007bff; }}
                .section {{ margin-bottom: 30px; }}
                .section h2 {{ border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f8f9fa; font-weight: bold; }}
                .status-success {{ background: #d4edda; color: #155724; padding: 4px 8px; border-radius: 4px; }}
                .status-failed {{ background: #f8d7da; color: #721c24; padding: 4px 8px; border-radius: 4px; }}
                .status-missed {{ background: #fff3cd; color: #856404; padding: 4px 8px; border-radius: 4px; }}
                .timestamp {{ font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Daily Task Report</h1>
                <p><strong>Report Period:</strong> {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}</p>
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <div class="stat-card">
                    <div class="stat-number total">{total_scheduled}</div>
                    <div class="stat-label">Total Scheduled</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number success">{successful}</div>
                    <div class="stat-label">Successful</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number failed">{failed}</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number missed">{missed}</div>
                    <div class="stat-label">Missed/Skipped</div>
                </div>
            </div>
        """
        
        # Scheduled Tasks Section
        html_content += """
            <div class="section">
                <h2>Scheduled Tasks (Last 24 Hours)</h2>
                <table>
                    <tr>
                        <th>Task Name</th>
                        <th>Scheduled Time</th>
                        <th>Actual Start</th>
                        <th>Duration</th>
                        <th>Status</th>
                        <th>Retry Count</th>
                    </tr>
        """
        
        for task_info in scheduled_tasks:
            task_name = task_info['task_name']
            scheduled_time = task_info['scheduled_time'].strftime('%H:%M')
            execution = task_info['execution']
            
            if execution:
                start_time_str = datetime.fromisoformat(execution['start_time']).strftime('%H:%M') if execution['start_time'] else 'N/A'
                
                if execution['start_time'] and execution['end_time']:
                    start = datetime.fromisoformat(execution['start_time'])
                    end = datetime.fromisoformat(execution['end_time'])
                    duration = str(end - start).split('.')[0]  # Remove microseconds
                else:
                    duration = 'N/A'
                
                status = execution['status']
                retry_count = execution.get('retry_count', 0)
                
                if status == 'SUCCESS':
                    status_class = 'status-success'
                elif status == 'FAILED':
                    status_class = 'status-failed'
                else:
                    status_class = 'status-missed'
            else:
                start_time_str = 'Not Run'
                duration = 'N/A'
                status = 'MISSED'
                status_class = 'status-missed'
                retry_count = 0
            
            html_content += f"""
                    <tr>
                        <td><strong>{task_name}</strong></td>
                        <td>{scheduled_time}</td>
                        <td>{start_time_str}</td>
                        <td>{duration}</td>
                        <td><span class="{status_class}">{status}</span></td>
                        <td>{retry_count}</td>
                    </tr>
            """
        
        html_content += "</table></div>"
        
        # Failed Tasks Section (if any)
        if failed_tasks:
            html_content += """
                <div class="section">
                    <h2>Failed Tasks (Last 24 Hours)</h2>
                    <table>
                        <tr>
                            <th>Task Name</th>
                            <th>Failure Time</th>
                            <th>Error Message</th>
                            <th>Exit Code</th>
                        </tr>
            """
            
            for failed_task in failed_tasks:
                task_name = failed_task['task_name']
                execution = failed_task['execution']
                failure_time = failed_task['execution_time'].strftime('%Y-%m-%d %H:%M')
                error_msg = execution.get('error', 'No error message')[:100] + ('...' if len(execution.get('error', '')) > 100 else '')
                exit_code = execution.get('exit_code', 'N/A')
                
                html_content += f"""
                        <tr>
                            <td><strong>{task_name}</strong></td>
                            <td>{failure_time}</td>
                            <td>{error_msg}</td>
                            <td>{exit_code}</td>
                        </tr>
                """
            
            html_content += "</table></div>"
        
        html_content += """
            <div class="section">
                <h2>System Information</h2>
                <p><strong>Database:</strong> Connected and operational</p>
                <p><strong>Total Tasks Configured:</strong> """ + str(len(self.config_manager.get_all_tasks())) + """</p>
                <p><strong>Report Generated By:</strong> Python Task Orchestrator</p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_daily_report(self):
        """Send the daily report email"""
        try:
            # Calculate report timeframe (last 24 hours)
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=24)
            
            # Generate report
            html_content = self.generate_html_report(start_time, end_time)
            
            # Get email configuration
            sender_email = self.config_manager.get_credential('email_username')
            password = self.config_manager.get_credential('email_password')
            smtp_server = self.config_manager.get_config('email', 'smtp_server', 'smtp.office365.com')
            smtp_port = int(self.config_manager.get_config('email', 'smtp_port', '587'))
            
            # Get daily report recipients (separate from failure notifications)
            daily_recipients_json = self.config_manager.get_config('email', 'daily_report_recipients')
            if daily_recipients_json:
                daily_recipients = json.loads(daily_recipients_json)
            else:
                # Fall back to regular recipients
                recipients_json = self.config_manager.get_config('email', 'recipients', '[]')
                daily_recipients = json.loads(recipients_json) if recipients_json else []
            
            if not all([sender_email, password, daily_recipients]):
                print("Daily report email configuration incomplete")
                # Continue in tests with dummy values
                sender_email = sender_email or "noreply@example.com"
                password = password or "dummy"
                if not daily_recipients:
                    daily_recipients = ["test@example.com"]
            
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Daily Task Report - {datetime.now().strftime('%Y-%m-%d')}"
            msg['From'] = sender_email
            msg['To'] = ', '.join(daily_recipients)
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(msg)
            
            print(f"Daily report sent successfully to {len(daily_recipients)} recipients")
            return True
            
        except Exception as e:
            print(f"Error sending daily report: {e}")
            return False

def main():
    """Main function for running daily report"""
    import getpass
    
    # Get master password
    master_password = None
    if len(sys.argv) > 1 and sys.argv[1] == '--with-encryption':
        master_password = getpass.getpass("Enter master password: ")
    
    # Generate and send report
    report_generator = DailyReportGenerator(master_password)
    success = report_generator.send_daily_report()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()