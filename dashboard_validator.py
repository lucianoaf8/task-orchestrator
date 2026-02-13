#!/usr/bin/env python3
"""
Dashboard Validation Script
Tests all API endpoints that the dashboard depends on
"""

import requests
import json
import sys
from datetime import datetime

def test_endpoint(url, method='GET', data=None):
    """Test an API endpoint and return success status"""
    try:
        if method == 'GET':
            response = requests.get(url, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=5)
        
        print(f"  {method} {url} -> {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"    ✓ Response: {type(result)} with {len(str(result))} chars")
            return True, result
        else:
            print(f"    ✗ Error: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"    ✗ Exception: {e}")
        return False, None

def main():
    """Run comprehensive dashboard API validation"""
    base_url = "http://localhost:5000"
    
    print("🔍 Dashboard API Validation")
    print(f"Testing endpoints at {base_url}")
    print(f"Started: {datetime.now()}")
    print("-" * 50)
    
    tests = [
        # Core dashboard endpoints
        ("Health Check", f"{base_url}/health", "GET"),
        ("API Health", f"{base_url}/api/health", "GET"),
        ("Get Tasks", f"{base_url}/api/tasks", "GET"),
        ("Scheduler Status", f"{base_url}/api/system/scheduler-status", "GET"),
        ("Scheduled Tasks", f"{base_url}/api/tasks/scheduled", "GET"),
    ]
    
    results = {}
    
    for test_name, url, method in tests:
        print(f"\n🧪 {test_name}")
        success, data = test_endpoint(url, method)
        results[test_name] = success
        
        # Additional validation for specific endpoints
        if success and data:
            if "Get Tasks" in test_name:
                tasks = data.get('tasks', {})
                print(f"    📊 Found {len(tasks)} tasks")
                for name, task in list(tasks.items())[:3]:  # Show first 3
                    print(f"      - {name}: {task.get('type', 'unknown')}")
                    
            elif "Scheduler Status" in test_name:
                configured = data.get('configured', 0)
                scheduled = data.get('scheduled', 0)
                print(f"    📊 Configured: {configured}, Scheduled: {scheduled}")
                
            elif "Health" in test_name:
                status = data.get('status', 'unknown')
                print(f"    📊 Status: {status}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dashboard should work correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the endpoints above.")
        print("\n🔧 Common fixes:")
        print("   - Ensure Flask app is running: python -m orchestrator.web.dashboard")
        print("   - Check if ConfigManager can connect to database")
        print("   - Verify API blueprint is registered correctly")
        return 1

if __name__ == "__main__":
    sys.exit(main())