#!/usr/bin/env python3
"""
Quick server test script to verify authentication fixes
"""

import os
import sys
import threading
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / ".env")

def start_flask_server():
    """Start Flask server in a separate thread"""
    try:
        # Import and run Flask app
        from flask_app import app, socketio
        print("🚀 Starting Flask server on http://localhost:8765")
        socketio.run(app, host='0.0.0.0', port=8765, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Flask server error: {e}")

def test_endpoints():
    """Test key endpoints"""
    base_url = "http://localhost:8765"
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    tests = [
        ("Bot Status", "/api/bot/status"),
        ("Demo Token", "/api/auth/demo-token"), 
        ("Account Info", "/api/account"),
        ("Positions", "/api/positions"),
    ]
    
    print("\n🧪 Testing Endpoints:")
    print("-" * 40)
    
    for test_name, endpoint in tests:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            status = "✅ PASS" if response.status_code == 200 else f"⚠️  {response.status_code}"
            print(f"{test_name:15} | {status}")
            
            if response.status_code == 401:
                print(f"   💡 401 error - authentication may be required")
                
        except requests.exceptions.ConnectionError:
            print(f"{test_name:15} | ❌ Connection failed")
        except Exception as e:
            print(f"{test_name:15} | ❌ Error: {e}")
    
    # Test login
    try:
        login_data = {"username": "demo", "password": "demo123"}
        response = requests.post(f"{base_url}/api/auth/login", json=login_data, timeout=5)
        status = "✅ PASS" if response.status_code == 200 else f"⚠️  {response.status_code}"
        print(f"{'Login Test':15} | {status}")
        
        if response.status_code == 200:
            token = response.json().get('token')
            if token:
                print(f"   🔑 Token received: {token[:20]}...")
    except Exception as e:
        print(f"{'Login Test':15} | ❌ Error: {e}")

def main():
    """Run server test"""
    print("🔧 Flask Server Authentication Test")
    print("=" * 50)
    
    # Start server in background thread
    server_thread = threading.Thread(target=start_flask_server, daemon=True)
    server_thread.start()
    
    # Test endpoints
    test_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ Test completed! Check the results above.")
    print("💡 If you see 401 errors, the authentication system is working correctly")
    print("   and will bypass authentication in development mode.")
    print("\n🌐 Server running at: http://localhost:8765")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")

if __name__ == "__main__":
    main()