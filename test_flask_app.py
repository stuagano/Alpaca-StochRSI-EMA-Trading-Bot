#!/usr/bin/env python3
"""
Test script for Flask trading application
Tests API endpoints and real-time functionality
"""

import requests
import json
import time
import socketio
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api"

def test_api_endpoints():
    """Test all API endpoints"""
    print("\n🧪 Testing API Endpoints...")
    
    # Test account endpoint
    print("\n1. Testing /api/account")
    try:
        response = requests.get(f"{API_BASE}/account")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success', False)}")
            if data.get('success'):
                account = data.get('account', {})
                print(f"   Portfolio Value: ${account.get('portfolio_value', 'N/A')}")
                print(f"   Cash: ${account.get('cash', 'N/A')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test positions endpoint
    print("\n2. Testing /api/positions")
    try:
        response = requests.get(f"{API_BASE}/positions")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success', False)}")
            positions = data.get('positions', [])
            print(f"   Number of positions: {len(positions)}")
            for pos in positions[:2]:  # Show first 2 positions
                print(f"   - {pos.get('symbol')}: {pos.get('qty')} shares @ ${pos.get('avg_entry_price')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test tickers endpoint
    print("\n3. Testing /api/tickers")
    try:
        response = requests.get(f"{API_BASE}/tickers")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success', False)}")
            tickers = data.get('tickers', [])
            print(f"   Tickers: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test chart data endpoint
    print("\n4. Testing /api/chart/<symbol>")
    try:
        test_symbol = "AAPL"
        response = requests.get(f"{API_BASE}/chart/{test_symbol}?timeframe=1Min&limit=10")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success', False)}")
            if data.get('success'):
                chart_data = data.get('data', {})
                print(f"   Data points: {len(chart_data.get('timestamps', []))}")
                if chart_data.get('close'):
                    print(f"   Latest close: ${chart_data['close'][-1]}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test latest bar endpoint
    print("\n5. Testing /api/latest_bar/<symbol>")
    try:
        test_symbol = "AAPL"
        response = requests.get(f"{API_BASE}/latest_bar/{test_symbol}")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success', False)}")
            if data.get('success'):
                bar = data.get('bar', {})
                print(f"   Time: {datetime.fromtimestamp(bar.get('time', 0))}")
                print(f"   OHLC: O=${bar.get('open')}, H=${bar.get('high')}, L=${bar.get('low')}, C=${bar.get('close')}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_socketio_connection():
    """Test Socket.IO real-time connection"""
    print("\n\n🔌 Testing Socket.IO Connection...")
    
    sio = socketio.Client()
    connected = False
    received_updates = []
    
    @sio.event
    def connect():
        nonlocal connected
        connected = True
        print("   ✅ Connected to Socket.IO server")
    
    @sio.event
    def disconnect():
        print("   Disconnected from Socket.IO server")
    
    @sio.on('real_time_update')
    def on_real_time_update(data):
        received_updates.append(data)
        print(f"\n   📊 Received real-time update at {datetime.now().strftime('%H:%M:%S')}")
        if 'account' in data:
            print(f"      Account - Portfolio Value: ${data['account'].get('portfolio_value', 'N/A')}")
        if 'positions' in data:
            print(f"      Positions: {len(data['positions'])} active")
        if 'ticker_prices' in data:
            print(f"      Ticker Prices: {len(data['ticker_prices'])} tickers")
            for ticker, price in list(data['ticker_prices'].items())[:3]:
                print(f"        - {ticker}: ${price}")
    
    try:
        # Connect to Socket.IO server
        print("   Attempting to connect...")
        sio.connect(BASE_URL)
        
        if connected:
            # Start streaming
            print("\n   Starting real-time streaming...")
            response = requests.post(f"{API_BASE}/stream/start")
            if response.status_code == 200:
                print("   ✅ Streaming started successfully")
                
                # Wait for updates
                print("   Waiting for real-time updates (30 seconds)...")
                start_time = time.time()
                while time.time() - start_time < 30:
                    time.sleep(1)
                    if len(received_updates) > 0 and (time.time() - start_time) > 10:
                        break
                
                print(f"\n   📈 Received {len(received_updates)} updates")
                
                # Stop streaming
                print("\n   Stopping streaming...")
                response = requests.post(f"{API_BASE}/stream/stop")
                if response.status_code == 200:
                    print("   ✅ Streaming stopped successfully")
            else:
                print(f"   ❌ Failed to start streaming: {response.text}")
        
        # Disconnect
        sio.disconnect()
        
    except Exception as e:
        print(f"   ❌ Socket.IO Error: {e}")

def main():
    """Main test function"""
    print("=" * 50)
    print("Flask Trading Application Test Suite")
    print("=" * 50)
    
    # Check if server is running
    print("\n🔍 Checking server status...")
    try:
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            print("   ✅ Server is running")
        else:
            print(f"   ⚠️  Server returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ❌ Server is not running!")
        print("   Please start the Flask app with: python flask_app.py")
        return
    
    # Run tests
    test_api_endpoints()
    test_socketio_connection()
    
    print("\n" + "=" * 50)
    print("✨ Test suite completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()