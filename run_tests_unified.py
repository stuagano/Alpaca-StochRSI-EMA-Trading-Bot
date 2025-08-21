#!/usr/bin/env python3
"""
Epic 1 Trading System - Unified Test Runner
Consolidated test runner for all Epic 1 testing needs
"""

import subprocess
import sys
import os
import time
import json
import argparse
from datetime import datetime
from pathlib import Path

def run_epic1_dashboard_tests():
    """Run Epic 1 dashboard comprehensive test suite"""
    print("🔄 Starting Epic 1 Dashboard Test Suite...")
    print("=" * 50)
    
    # Check if server is running
    try:
        import requests
        response = requests.get('http://localhost:9765/health', timeout=5)
        if response.status_code != 200:
            print("❌ Error: Flask server not responding on localhost:9765")
            print("Please start the server first: python flask_app_complete.py")
            return False
    except:
        print("❌ Error: Flask server not running on localhost:9765")
        print("Please start the server first: python flask_app_complete.py")
        return False
    
    # Run the comprehensive test suite
    result = subprocess.run([
        sys.executable, 'tests/test_suite.py', 
        '--url', 'http://localhost:9765',
        '--report', 
        '--output', 'test_report.md'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def check_server_status():
    """Check if Flask server is running"""
    try:
        import requests
        response = requests.get('http://localhost:9765/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def print_epic1_test_instructions():
    """Print Epic 1 testing instructions"""
    print("\n" + "=" * 60)
    print("🧪 EPIC 1 DASHBOARD TESTING SUITE")
    print("=" * 60)
    print()
    print("📋 Available Test Options:")
    print()
    print("1. 🖥️  Backend API Tests:")
    print("   python run_tests_unified.py --epic1")
    print("   Tests all API endpoints, data validation, performance")
    print()
    print("2. 🎨 Frontend Tests (Interactive):")
    print("   http://localhost:9765/tests/frontend")
    print("   Visual test suite in your browser")
    print()
    print("3. 🔍 Debug Tools:")
    print("   http://localhost:9765/debug/positions")
    print("   Real-time API debugging interface")
    print()
    print("4. 📊 Main Dashboard:")
    print("   http://localhost:9765/")
    print("   Full Epic 1 trading dashboard")
    print()
    print("🚀 Quick Start:")
    if not check_server_status():
        print("❌ Flask server not running!")
        print("   Start server: python flask_app_complete.py")
    else:
        print("✅ Flask server is running")
        print("   Run all tests: python run_tests_unified.py --epic1")
    print()

def create_test_summary():
    """Create a comprehensive test summary"""
    summary = {
        "test_suite": "Epic 1 Trading Dashboard",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "server_status": "online" if check_server_status() else "offline",
        "test_urls": {
            "main_dashboard": "http://localhost:9765/",
            "frontend_tests": "http://localhost:9765/tests/frontend",
            "debug_positions": "http://localhost:9765/debug/positions",
            "health_check": "http://localhost:9765/health"
        },
        "documentation": {
            "main_docs": "docs/UNIFIED_DASHBOARD_DOCUMENTATION.md",
            "test_report": "test_report.md",
            "pine_script_ref": "docs/PINE_SCRIPT_TIME_REFERENCE.md",
            "tradingview_patterns": "docs/TRADINGVIEW_PATTERNS_REFERENCE.md"
        },
        "test_files": {
            "backend_suite": "tests/test_suite.py",
            "frontend_suite": "tests/frontend_test_suite.html",
            "debug_page": "debug_positions.html"
        }
    }
    
    with open('test_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary

def run_pytest_suite():
    """Run pytest-based test suite"""
    print("🔄 Running pytest test suite...")
    
    # Run pytest with coverage
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 'tests/', 
        '--cov=.', 
        '--cov-report=html',
        '--cov-report=term-missing',
        '-v'
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    return result.returncode == 0

def main():
    """Main test runner entry point"""
    parser = argparse.ArgumentParser(description="Epic 1 Trading System Test Runner")
    
    parser.add_argument("--epic1", action="store_true", help="Run Epic 1 dashboard tests")
    parser.add_argument("--pytest", action="store_true", help="Run pytest test suite")
    parser.add_argument("--all", action="store_true", help="Run all available tests")
    parser.add_argument("--summary", action="store_true", help="Create test summary")
    parser.add_argument("--check", action="store_true", help="Check server status")
    
    args = parser.parse_args()
    
    # Create test summary
    summary = create_test_summary()
    
    success = True
    
    if args.epic1 or args.all:
        if not check_server_status():
            print("❌ Error: Flask server not running on localhost:9765")
            print("Please start the server first: python flask_app_complete.py")
            return 1
        
        success = run_epic1_dashboard_tests()
        
        if success:
            print("\n🎉 Epic 1 dashboard tests completed successfully!")
        else:
            print("\n⚠️ Some Epic 1 tests failed. Check test_report.md for details.")
    
    if args.pytest or args.all:
        pytest_success = run_pytest_suite()
        success = success and pytest_success
        
        if pytest_success:
            print("\n🎉 Pytest suite completed successfully!")
        else:
            print("\n⚠️ Some pytest tests failed.")
    
    if args.check:
        if check_server_status():
            print("✅ Flask server is running on localhost:9765")
        else:
            print("❌ Flask server is not running on localhost:9765")
    
    if args.summary:
        print("📋 Test summary created: test_summary.json")
        print(json.dumps(summary, indent=2))
    
    if not any(vars(args).values()):
        print_epic1_test_instructions()
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())