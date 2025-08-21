#!/usr/bin/env python3
"""
Quick test to verify signals API functionality
"""

import requests
import json

def test_signals_api():
    try:
        # Test the signals endpoint
        print("Testing /api/signals/AAPL...")
        response = requests.get("http://localhost:9765/api/signals/AAPL")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API Response successful!")
            print(json.dumps(data, indent=2))
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        print("Make sure Flask server is running on port 9765")

if __name__ == "__main__":
    test_signals_api()