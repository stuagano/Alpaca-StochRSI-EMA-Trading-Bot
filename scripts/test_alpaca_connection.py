#!/usr/bin/env python3
"""
Test Alpaca API Connection
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
env_path = '/Users/stuartgano/Desktop/Penny Personal Assistant/Alpaca-StochRSI-EMA-Trading-Bot/.env'
load_dotenv(env_path)

print("Testing Alpaca API Connection")
print("=" * 50)

# Check environment variables
api_key = os.getenv('APCA_API_KEY_ID')
api_secret = os.getenv('APCA_API_SECRET_KEY')
base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')

if not api_key or not api_secret:
    print("❌ Alpaca API credentials not found in .env file")
    sys.exit(1)

print(f"API Key: {api_key[:8]}...")
print(f"Base URL: {base_url}")

try:
    import alpaca_trade_api as tradeapi
    
    # Initialize Alpaca client
    api = tradeapi.REST(
        key_id=api_key,
        secret_key=api_secret,
        base_url=base_url,
        api_version='v2'
    )
    
    # Test account access
    print("\nFetching account information...")
    account = api.get_account()
    
    print("✅ Successfully connected to Alpaca API!")
    print(f"\nAccount Details:")
    print(f"  Account ID: {account.id}")
    print(f"  Status: {account.status}")
    print(f"  Buying Power: ${float(account.buying_power):,.2f}")
    print(f"  Cash: ${float(account.cash):,.2f}")
    print(f"  Portfolio Value: ${float(account.portfolio_value):,.2f}")
    print(f"  Pattern Day Trader: {account.pattern_day_trader}")
    
    # Test market data
    print("\nFetching latest AAPL price...")
    try:
        bars = api.get_latest_bar('AAPL')
        print(f"✅ AAPL Latest Price: ${bars.c:.2f}")
        print(f"  Volume: {bars.v:,}")
        print(f"  Time: {bars.t}")
    except Exception as e:
        print(f"⚠️  Could not fetch market data: {e}")
        print("   (This is normal outside market hours)")
    
    print("\n✅ Alpaca API is fully configured and working!")
    print("   Real market data will be available in the trading interface.")
    
except Exception as e:
    print(f"\n❌ Error connecting to Alpaca API: {e}")
    print("\nPossible issues:")
    print("  1. Invalid API credentials")
    print("  2. Network connection issues")
    print("  3. Alpaca API service is down")
    print("\nPlease check your .env file and try again.")
    sys.exit(1)