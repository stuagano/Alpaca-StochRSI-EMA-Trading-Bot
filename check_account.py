#!/usr/bin/env python3
import alpaca_trade_api as alpaca
import json

# Load credentials
with open('AUTH/authAlpaca.txt', 'r') as f:
    auth_data = json.loads(f.read().strip())

api = alpaca.REST(
    auth_data['APCA-API-KEY-ID'], 
    auth_data['APCA-API-SECRET-KEY'], 
    auth_data['BASE-URL'], 
    api_version='v2'
)

# Get account info
try:
    account = api.get_account()
    print(f"Account Status: {account.status}")
    print(f"Buying Power: ${account.buying_power}")
    print(f"Portfolio Value: ${account.portfolio_value}")
    print(f"Cash: ${account.cash}")
except Exception as e:
    print(f"Error fetching account: {e}")

# Get available crypto assets
try:
    assets = api.list_assets(status='active', asset_class='crypto')
    print(f"\nAvailable Crypto Assets ({len(assets)} total):")
    for asset in assets[:15]:  # Show first 15
        print(f"  {asset.symbol}")
except Exception as e:
    print(f"Error fetching assets: {e}")

# Check current positions
try:
    positions = api.list_positions()
    print(f"\nCurrent Positions ({len(positions)}):")
    for pos in positions:
        print(f"  {pos.symbol}: {pos.qty} @ ${pos.avg_entry_price}")
except Exception as e:
    print(f"Error fetching positions: {e}")