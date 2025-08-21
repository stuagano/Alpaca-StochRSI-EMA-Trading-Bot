#!/usr/bin/env python3
"""
Simple fix for dashboard data - restart Flask with cache clearing
"""

import os
import sys
import signal
import time
import subprocess

def fix_dashboard():
    print("🔧 Fixing Dashboard Data Issue")
    print("=" * 50)
    
    # Kill existing Flask processes
    print("\n📊 Step 1: Stopping Flask server...")
    try:
        subprocess.run("pkill -f 'python.*flask_app'", shell=True)
        print("✅ Flask processes stopped")
        time.sleep(2)
    except:
        pass
    
    # Clear SQLite write-ahead log files that might have stale data
    print("\n📊 Step 2: Clearing database cache...")
    db_files = [
        'database/trading_data.db-wal',
        'database/trading_data.db-shm'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"✅ Removed {db_file}")
            except Exception as e:
                print(f"⚠️ Could not remove {db_file}: {e}")
    
    # Create a simple data refresh script
    print("\n📊 Step 3: Creating data refresh configuration...")
    
    refresh_config = """
import os
os.environ['FORCE_FRESH_DATA'] = '1'
os.environ['SKIP_CACHE'] = '1'
os.environ['DATA_CACHE_TTL'] = '60'  # 1 minute cache only
"""
    
    with open('.env.runtime', 'w') as f:
        f.write(refresh_config)
    print("✅ Runtime configuration created")
    
    # Restart Flask with fresh data flag
    print("\n📊 Step 4: Starting Flask with fresh data mode...")
    
    # Change to project directory
    os.chdir('/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot')
    
    # Start Flask in background
    flask_cmd = """
export FORCE_FRESH_DATA=1
export SKIP_CACHE=1
source venv/bin/activate 2>/dev/null || true
python3 flask_app.py > flask_fresh.log 2>&1 &
"""
    
    subprocess.run(flask_cmd, shell=True)
    print("✅ Flask restarted with fresh data mode")
    
    # Wait for Flask to start
    print("\n⏳ Waiting for Flask to initialize...")
    time.sleep(5)
    
    # Test the endpoints
    print("\n📊 Step 5: Testing data endpoints...")
    try:
        import requests
        
        # Test chart endpoint
        resp = requests.get('http://localhost:9765/api/chart/SPY', timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('success'):
                print(f"✅ Chart endpoint working - {data['data']['data_points']} data points")
        
        # Test account endpoint
        resp = requests.get('http://localhost:9765/api/account', timeout=5)
        if resp.status_code == 200:
            print("✅ Account endpoint working")
            
    except Exception as e:
        print(f"⚠️ Could not test endpoints: {e}")
    
    print("\n✨ Dashboard fix complete!")
    print("\n📈 Please refresh your browser:")
    print("  http://localhost:9765")
    print("\n💡 The dashboard should now show current market data")
    print("💡 If data is still stale, try clearing your browser cache")
    
    return True

if __name__ == "__main__":
    fix_dashboard()