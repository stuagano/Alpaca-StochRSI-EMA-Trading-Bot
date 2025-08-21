#!/usr/bin/env python3
"""
Quick test runner for Epic 1 Trading Dashboard
Runs comprehensive tests and generates reports
"""

import subprocess
import sys
import os
import time
import json
from datetime import datetime

def run_backend_tests():
    """Run backend test suite"""
    print("🔄 Starting Backend Test Suite...")
    print("=" * 50)
    
    # Run the comprehensive test suite
    result = subprocess.run([
        sys.executable, 'tests/test_suite.py', 
        '--url', 'http://localhost:8765',
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
        response = requests.get('http://localhost:8765/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def print_test_instructions():
    """Print testing instructions"""
    print("\n" + "=" * 60)
    print("🧪 EPIC 1 DASHBOARD TESTING SUITE")
    print("=" * 60)
    print()
    print("📋 Available Test Options:")
    print()
    print("1. 🖥️  Backend API Tests:")
    print("   python run_tests_epic1.py --backend")
    print("   Tests all API endpoints, data validation, performance")
    print()
    print("2. 🎨 Frontend Tests (Interactive):")
    print("   http://localhost:8765/tests/frontend")
    print("   Visual test suite in your browser")
    print()
    print("3. 🔍 Debug Tools:")
    print("   http://localhost:8765/debug/positions")
    print("   Real-time API debugging interface")
    print()
    print("4. 📊 Main Dashboard:")
    print("   http://localhost:8765/")
    print("   Full Epic 1 trading dashboard")
    print()
    print("🚀 Quick Start:")
    if not check_server_status():
        print("❌ Flask server not running!")
        print("   Start server: python flask_app_complete.py")
    else:
        print("✅ Flask server is running")
        print("   Run all tests: python run_tests_epic1.py --all")
    print()

def create_test_summary():
    """Create a comprehensive test summary"""
    summary = {
        "test_suite": "Epic 1 Trading Dashboard",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "server_status": "online" if check_server_status() else "offline",
        "test_urls": {
            "main_dashboard": "http://localhost:8765/",
            "frontend_tests": "http://localhost:8765/tests/frontend",
            "debug_positions": "http://localhost:8765/debug/positions",
            "health_check": "http://localhost:8765/health"
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

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Epic 1 Dashboard Test Runner")
    parser.add_argument("--backend", action="store_true", help="Run backend test suite")
    parser.add_argument("--all", action="store_true", help="Run all available tests")
    parser.add_argument("--summary", action="store_true", help="Create test summary")
    
    args = parser.parse_args()
    
    # Create test summary
    summary = create_test_summary()
    
    if args.backend or args.all:
        if not check_server_status():
            print("❌ Error: Flask server not running on localhost:8765")
            print("Please start the server first: python flask_app_complete.py")
            return 1
        
        success = run_backend_tests()
        
        if success:
            print("\n🎉 Backend tests completed successfully!")
        else:
            print("\n⚠️ Some backend tests failed. Check test_report.md for details.")
        
        if args.all:
            print("\n📱 Frontend Tests:")
            print(f"   Visit: {summary['test_urls']['frontend_tests']}")
            print("\n🔍 Debug Tools:")  
            print(f"   Visit: {summary['test_urls']['debug_positions']}")
    
    elif args.summary:
        print("📋 Test summary created: test_summary.json")
        print(json.dumps(summary, indent=2))
    
    else:
        print_test_instructions()
    
    return 0

if __name__ == "__main__":
    exit(main())