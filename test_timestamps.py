#!/usr/bin/env python3
"""
Quick test script to verify timestamp formats in the trading bot
"""
import requests
import json
from datetime import datetime

def test_endpoint(endpoint, description):
    """Test an API endpoint and check timestamp formats"""
    try:
        print(f"\n🧪 Testing {description}")
        print(f"📡 Endpoint: {endpoint}")
        
        response = requests.get(endpoint, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                # Check chart endpoint format
                if 'data' in data and 'data' in data['data']:
                    candles = data['data']['data'][:2]  # First 2 candles
                    print(f"✅ Success: {len(data['data']['data'])} candles")
                    for i, candle in enumerate(candles):
                        timestamp = candle['time']
                        dt = datetime.fromtimestamp(timestamp)
                        print(f"   Candle {i+1}: time={timestamp} ({type(timestamp).__name__}) -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"   OHLC: [{candle['open']}, {candle['high']}, {candle['low']}, {candle['close']}]")
                
                # Check latest_bar format
                elif 'bar' in data:
                    bar = data['bar']
                    timestamp = bar['time']
                    dt = datetime.fromtimestamp(timestamp)
                    print(f"✅ Success: Latest bar")
                    print(f"   time={timestamp} ({type(timestamp).__name__}) -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   OHLC: [{bar['open']}, {bar['high']}, {bar['low']}, {bar['close']}]")
                    print(f"   Flags: new_candle={data.get('is_new_candle')}, current_minute={data.get('is_current_minute')}")
                
                else:
                    print(f"✅ Success but unknown format: {list(data.keys())}")
            else:
                print(f"❌ API returned error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text[:200]}")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Timeout - server might be starting up")
    except requests.exceptions.ConnectionError:
        print(f"🚫 Connection error - server might not be running")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")

def main():
    base_url = "http://localhost:9765"
    
    print("🎯 Timestamp Format Verification Test")
    print("=" * 50)
    
    # Test chart endpoint
    test_endpoint(f"{base_url}/api/chart/AAPL?limit=5", "Chart endpoint for AAPL")
    
    # Test latest bar endpoint  
    test_endpoint(f"{base_url}/api/latest_bar/AAPL", "Latest bar endpoint for AAPL")
    
    print("\n🏁 Test completed!")

if __name__ == "__main__":
    main()