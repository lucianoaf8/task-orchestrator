#!/usr/bin/env python3
"""
404 Error Debugging Script for Task Orchestrator Dashboard
Tests all endpoints the dashboard tries to access and identifies missing routes
"""

import requests
import json
import sys
from urllib.parse import urljoin

def test_endpoint(base_url, endpoint, method='GET', data=None, description=""):
    """Test a single endpoint and return detailed results"""
    url = urljoin(base_url, endpoint)
    
    try:
        if method == 'GET':
            response = requests.get(url, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=5)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=5)
        
        status_icon = "✅" if response.status_code == 200 else "❌" if response.status_code == 404 else "⚠️"
        
        result = {
            'endpoint': endpoint,
            'method': method,
            'status_code': response.status_code,
            'success': response.status_code == 200,
            'description': description,
            'url': url
        }
        
        print(f"{status_icon} {method:6} {endpoint:35} -> {response.status_code} {description}")
        
        if response.status_code == 404:
            print(f"    💀 MISSING: This endpoint doesn't exist!")
        elif response.status_code == 500:
            print(f"    💥 ERROR: Server error - check logs")
        elif response.status_code == 200:
            try:
                json_data = response.json()
                if 'error' in json_data:
                    print(f"    ⚠️  JSON Error: {json_data['error']}")
                elif 'status' in json_data:
                    print(f"    📊 Status: {json_data['status']}")
            except:
                print(f"    📄 Response length: {len(response.text)} chars")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print(f"❌ {method:6} {endpoint:35} -> CONNECTION_FAILED {description}")
        print(f"    🔌 OFFLINE: Dashboard server not running!")
        return {'endpoint': endpoint, 'method': method, 'success': False, 'error': 'CONNECTION_FAILED'}
    except Exception as e:
        print(f"❌ {method:6} {endpoint:35} -> EXCEPTION {description}")
        print(f"    💥 Error: {e}")
        return {'endpoint': endpoint, 'method': method, 'success': False, 'error': str(e)}

def main():
    """Run comprehensive endpoint testing"""
    base_url = "http://localhost:5000"
    
    print("🔍 TASK ORCHESTRATOR - 404 ERROR DEBUGGING")
    print("=" * 60)
    print(f"Testing dashboard at: {base_url}")
    print("=" * 60)
    
    # Test all endpoints the dashboard tries to access
    endpoints_to_test = [
        # Main pages
        ('/', 'GET', None, 'Main dashboard page'),
        ('/task-manager', 'GET', None, 'Task manager page'),
        ('/compact-scheduler', 'GET', None, 'Compact scheduler page'),
        
        # API endpoints that JavaScript calls
        ('/api/tasks', 'GET', None, 'Get all tasks (PRIMARY)'),
        ('/api/health', 'GET', None, 'API health check'),
        ('/health', 'GET', None, 'Legacy health check'),
        ('/api/system/scheduler-status', 'GET', None, 'Scheduler status'),
        ('/api/tasks/scheduled', 'GET', None, 'List scheduled tasks'),
        
        # Task management endpoints
        ('/api/tasks/test_task', 'POST', {'name': 'test_task', 'type': 'shell', 'command': 'echo test'}, 'Create task'),
        ('/api/tasks/test_task/run', 'POST', None, 'Run task'),
        ('/api/tasks/test_task/history', 'GET', None, 'Task history'),
        ('/api/tasks/test_task', 'DELETE', None, 'Delete task'),
        
        # Command testing
        ('/api/test-command', 'POST', {'command': 'echo test'}, 'Test command'),
        
        # Debug endpoints
        ('/debug/routes', 'GET', None, 'List all routes'),
    ]
    
    results = []
    
    for endpoint, method, data, description in endpoints_to_test:
        result = test_endpoint(base_url, endpoint, method, data, description)
        results.append(result)
        print()  # Add space between tests
    
    # Summary
    print("=" * 60)
    print("📊 SUMMARY REPORT")
    print("=" * 60)
    
    total_tests = len(results)
    successful = sum(1 for r in results if r.get('success', False))
    missing_404 = sum(1 for r in results if r.get('status_code') == 404)
    errors_500 = sum(1 for r in results if r.get('status_code') == 500)
    
    print(f"Total endpoints tested: {total_tests}")
    print(f"✅ Working correctly: {successful}")
    print(f"❌ Missing (404): {missing_404}")
    print(f"💥 Server errors (500): {errors_500}")
    print(f"🔌 Connection failures: {sum(1 for r in results if r.get('error') == 'CONNECTION_FAILED')}")
    
    if missing_404 > 0:
        print("\n🚨 MISSING ENDPOINTS (404 Errors):")
        for result in results:
            if result.get('status_code') == 404:
                print(f"   • {result['method']} {result['endpoint']}")
    
    if errors_500 > 0:
        print("\n💥 SERVER ERRORS (500 Errors):")
        for result in results:
            if result.get('status_code') == 500:
                print(f"   • {result['method']} {result['endpoint']}")
    
    print("\n🔧 RECOMMENDED FIXES:")
    
    if missing_404 > 0:
        print("   1. Update orchestrator/web/app.py with the complete Flask app fix")
        print("   2. Ensure API blueprint is properly registered")
        print("   3. Check that all @app.route decorators are uncommented")
    
    if any(r.get('endpoint') == '/api/tasks' and not r.get('success', False) for r in results):
        print("   4. PRIMARY ISSUE: /api/tasks endpoint not working - dashboard will be empty!")
    
    if successful == total_tests:
        print("   🎉 All endpoints working! 404 errors should be resolved.")
    
    print(f"\n📝 Logs: Check terminal where you started the dashboard for detailed error messages")
    print(f"🌐 Dashboard: {base_url}")
    
    return 0 if missing_404 == 0 else 1

if __name__ == "__main__":
    sys.exit(main())