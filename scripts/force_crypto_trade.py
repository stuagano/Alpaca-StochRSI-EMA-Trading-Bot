#!/usr/bin/env python3
"""Force the crypto bot to scan and execute a trade"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import alpaca_trade_api as tradeapi
from strategies.crypto_scalping_strategy import CryptoVolatilityScanner
from datetime import datetime, timezone

# Load credentials
with open('AUTH/authAlpaca.txt', 'r') as f:
    auth_data = json.load(f)
    api_key = auth_data.get('APCA-API-KEY-ID')
    api_secret = auth_data.get('APCA-API-SECRET-KEY')
    base_url = auth_data.get('BASE-URL')

api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

print("="*60)
print("FORCING CRYPTO TRADE EXECUTION")
print("="*60)

# Get account info
account = api.get_account()
print(f"\nAccount Status: {account.status}")
print(f"Buying Power: ${float(account.buying_power):,.2f}")

# Initialize scanner
scanner = CryptoVolatilityScanner()

# Update scanner with market data
print("\n📊 Updating scanner with market data...")
symbols = ['BTCUSD', 'ETHUSD', 'LTCUSD', 'DOGEUSD', 'AVAXUSD']

for symbol in symbols:
    try:
        # Get latest quote using the correct format
        bars = api.get_crypto_bars(symbol.replace('USD', '/USD'), '1Min', limit=100).df
        if not bars.empty:
            current_price = bars['close'].iloc[-1]
            volume = bars['volume'].mean()
            volatility = (bars['high'].iloc[-1] - bars['low'].iloc[-1]) / bars['close'].iloc[-1]
            
            scanner.update_data(symbol, current_price, volume, volatility)
            print(f"   {symbol}: ${current_price:.4f} (vol: {volatility:.4f})")
    except Exception as e:
        print(f"   Error getting data for {symbol}: {e}")

# Get signals
print("\n🎯 Scanning for opportunities...")
signals = scanner.scan_for_opportunities()

if not signals:
    print("No signals found - forcing a signal by adjusting thresholds")
    # Force generate signals by lowering thresholds
    scanner.min_volatility = 0.0001  # Super low threshold
    signals = scanner.scan_for_opportunities()

if signals:
    print(f"\n📊 Found {len(signals)} signals:")
    for i, signal in enumerate(signals[:3]):
        print(f"\n  Signal {i+1}:")
        print(f"    Symbol: {signal.symbol}")
        print(f"    Action: {signal.action.upper()}")
        print(f"    Price: ${signal.price:.4f}")
        print(f"    Confidence: {signal.confidence:.2f}")
        print(f"    Volatility: {signal.volatility:.4f}")
        
        if i == 0 and signal.confidence > 0.3:  # Take the first signal
            print(f"\n  🚀 EXECUTING TRADE:")
            
            # Convert symbol format for Alpaca
            if 'USD' in signal.symbol:
                crypto_part = signal.symbol.replace('USD', '').replace('USDT', '').replace('USDC', '')
                alpaca_symbol = f"{crypto_part}/USD"
            else:
                alpaca_symbol = signal.symbol
                
            # Calculate small position size
            position_value = 25  # $25 position
            qty = position_value / signal.price
            
            print(f"    Placing {signal.action} order for {qty:.8f} {alpaca_symbol}")
            
            try:
                order = api.submit_order(
                    symbol=alpaca_symbol,
                    qty=round(qty, 8),
                    side=signal.action,
                    type='market',
                    time_in_force='gtc'  # Changed from 'ioc' to 'gtc' for better fills
                )
                
                print(f"\n  ✅ Order placed successfully!")
                print(f"    Order ID: {order.id}")
                print(f"    Status: {order.status}")
                
            except Exception as e:
                print(f"\n  ❌ Order failed: {e}")
else:
    print("No signals generated even with lowered thresholds")

# Check positions
print("\n📊 CURRENT CRYPTO POSITIONS:")
positions = api.list_positions()
crypto_positions = [p for p in positions if any(crypto in p.symbol for crypto in ['BTC', 'ETH', 'LTC', 'DOGE', 'AVAX'])]

if crypto_positions:
    for p in crypto_positions:
        print(f"  {p.symbol:10s} | Qty: {float(p.qty):10.8f} | P&L: ${float(p.unrealized_pl):+8.2f}")
else:
    print("  No crypto positions")

print("\n" + "="*60)