#!/usr/bin/env python3
"""Test crypto trading by manually placing a small order"""

import json
import alpaca_trade_api as tradeapi
import sys

# Load credentials
with open('AUTH/authAlpaca.txt', 'r') as f:
    auth_data = json.load(f)
    api_key = auth_data.get('APCA-API-KEY-ID')
    api_secret = auth_data.get('APCA-API-SECRET-KEY')
    base_url = auth_data.get('BASE-URL')

api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

print("="*60)
print("CRYPTO TRADING TEST")
print("="*60)

# Get account info
account = api.get_account()
print(f"\nAccount Status: {account.status}")
print(f"Crypto Trading: {account.crypto_status}")
print(f"Buying Power: ${float(account.buying_power):,.2f}")

# Check BTC price
try:
    btc_quote = api.get_latest_crypto_quote('BTC/USD')
    btc_price = float(btc_quote.ap)
    print(f"\nBTC/USD Current Price: ${btc_price:,.2f}")
except:
    # Try alternative method
    try:
        btc_bars = api.get_crypto_bars('BTC/USD', '1Min', limit=1).df
        if not btc_bars.empty:
            btc_price = btc_bars['close'].iloc[-1]
            print(f"\nBTC/USD Current Price: ${btc_price:,.2f}")
        else:
            print("\nCould not get BTC price, using estimate")
            btc_price = 110000  # Approximate
    except:
        print("\nCould not get BTC price, using estimate")
        btc_price = 110000  # Approximate

# Place a TINY test order for BTC
try:
    print("\n📊 Placing test crypto order...")
    print("   Symbol: BTC/USD")
    print("   Quantity: 0.0001 BTC")
    print(f"   Value: ~${0.0001 * btc_price:.2f}")
    
    order = api.submit_order(
        symbol='BTC/USD',  # Use slash format
        qty=0.0001,  # Very small amount
        side='buy',
        type='market',
        time_in_force='gtc'
    )
    
    print(f"\n✅ Order placed successfully!")
    print(f"   Order ID: {order.id}")
    print(f"   Status: {order.status}")
    print(f"   Quantity: {order.qty} BTC")
    
except Exception as e:
    print(f"\n❌ Order failed: {e}")
    
# Check positions after order
print("\n📊 CHECKING POSITIONS AFTER ORDER:")
positions = api.list_positions()

crypto_positions = [p for p in positions if any(crypto in p.symbol for crypto in ['BTC', 'ETH', 'LTC'])]

if crypto_positions:
    print("\n🪙 CRYPTO POSITIONS:")
    for p in crypto_positions:
        print(f"  {p.symbol:10s} | Qty: {float(p.qty):10.8f} | Entry: ${float(p.avg_entry_price):8.2f}")
else:
    print("\nNo crypto positions yet")

print("\n" + "="*60)