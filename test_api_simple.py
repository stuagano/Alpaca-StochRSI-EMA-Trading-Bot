#!/usr/bin/env python3
"""
Simple API test for Flask trading application
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
API_BASE = f"{BASE_URL}/api"

print("=" * 50)
print("Flask Trading API Quick Test")
print("=" * 50)

# Test 1: Account Info
print("\n✅ Testing Account Info...")
try:
    response = requests.get(f"{API_BASE}/account")
    data = response.json()
    if data.get('success'):
        account = data['account']
        print(f"Portfolio Value: ${account.get('portfolio_value', 'N/A'):,.2f}")
        print(f"Cash: ${account.get('cash', 'N/A'):,.2f}")
        print(f"Equity: ${account.get('equity', 'N/A'):,.2f}")
    else:
        print(f"Error: {data.get('error')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Positions
print("\n✅ Testing Positions...")
try:
    response = requests.get(f"{API_BASE}/positions")
    data = response.json()
    if data.get('success'):
        positions = data['positions']
        print(f"Active positions: {len(positions)}")
        for pos in positions[:3]:
            print(f"- {pos['symbol']}: {pos['qty']} shares @ ${pos.get('avg_entry_price', 0):.2f}")
    else:
        print(f"Error: {data.get('error')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Chart Data
print("\n✅ Testing Chart Data (AAPL)...")
try:
    response = requests.get(f"{API_BASE}/chart/AAPL?timeframe=1Min&limit=5")
    data = response.json()
    if data.get('success'):
        chart_data = data['data']
        print(f"Data points: {len(chart_data['timestamps'])}")
        if chart_data['close']:
            print(f"Latest close: ${chart_data['close'][-1]:.2f}")
            print(f"Latest time: {datetime.fromtimestamp(chart_data['timestamps'][-1])}")
    else:
        print(f"Error: {data.get('error')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Latest Bar
print("\n✅ Testing Latest Bar (AAPL)...")
try:
    response = requests.get(f"{API_BASE}/latest_bar/AAPL")
    data = response.json()
    if data.get('success'):
        bar = data['bar']
        print(f"Time: {datetime.fromtimestamp(bar['time'])}")
        print(f"OHLC: ${bar['open']:.2f} / ${bar['high']:.2f} / ${bar['low']:.2f} / ${bar['close']:.2f}")
    else:
        print(f"Error: {data.get('error')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: Start/Stop Streaming
print("\n✅ Testing Streaming Control...")
try:
    # Start streaming
    response = requests.post(f"{API_BASE}/stream/start")
    data = response.json()
    print(f"Start streaming: {'Success' if data.get('success') else 'Failed'}")
    
    # Stop streaming
    response = requests.post(f"{API_BASE}/stream/stop")
    data = response.json()
    print(f"Stop streaming: {'Success' if data.get('success') else 'Failed'}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 50)
print("✨ API tests completed!")
print("=" * 50)