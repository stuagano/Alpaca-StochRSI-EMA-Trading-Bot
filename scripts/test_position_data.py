#!/usr/bin/env python3
"""
Test script to verify position data structure and API endpoint
"""

import requests
import json
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.unified_data_manager import UnifiedDataManager
from config.unified_config import get_config

def test_position_data_structure():
    """Test the position data structure from data manager"""
    print("🧪 Testing Position Data Structure")
    print("=" * 50)
    
    try:
        # Initialize data manager
        config = get_config()
        data_manager = UnifiedDataManager(config)
        
        # Get positions
        positions = data_manager.get_positions()
        
        print(f"Found {len(positions)} positions")
        
        if positions:
            print(f"\nFirst position structure:")
            first_pos = positions[0]
            for key, value in first_pos.items():
                print(f"  {key}: {value} ({type(value).__name__})")
            
            print(f"\nRequired fields check:")
            required_fields = ['symbol', 'qty', 'avg_entry_price', 'current_price', 'unrealized_pl']
            for field in required_fields:
                exists = field in first_pos
                print(f"  ✅ {field}: {exists}")
                if not exists:
                    print(f"     Available keys: {list(first_pos.keys())}")
        else:
            print("No positions found - this is normal if no trades are open")
            
    except Exception as e:
        print(f"❌ Error testing position data: {e}")
        import traceback
        traceback.print_exc()

def test_api_endpoint():
    """Test the positions API endpoint"""
    print("\n🌐 Testing Positions API Endpoint")
    print("=" * 50)
    
    try:
        response = requests.get('http://localhost:9765/api/positions', timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response structure:")
            print(f"  success: {data.get('success')}")
            print(f"  positions count: {len(data.get('positions', []))}")
            
            if data.get('positions'):
                first_pos = data['positions'][0]
                print(f"\nFirst position from API:")
                for key, value in first_pos.items():
                    print(f"  {key}: {value}")
        else:
            print(f"❌ Failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask app. Is it running on port 9765?")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_position_data_structure()
    test_api_endpoint()