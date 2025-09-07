#!/usr/bin/env python3
"""Check what positions are actually in the account"""

import json
import alpaca_trade_api as tradeapi

# Load credentials
with open('AUTH/authAlpaca.txt', 'r') as f:
    auth_data = json.load(f)
    api_key = auth_data.get('APCA-API-KEY-ID')
    api_secret = auth_data.get('APCA-API-SECRET-KEY')
    base_url = auth_data.get('BASE-URL')

api = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')

print("="*60)
print("CHECKING ALPACA POSITIONS")
print("="*60)

# Get account info
account = api.get_account()
print(f"\nAccount Status: {account.status}")
print(f"Crypto Trading: {account.crypto_status}")
print(f"Buying Power: ${float(account.buying_power):,.2f}")

# Get all positions
print("\n📊 ALL POSITIONS:")
positions = api.list_positions()

if not positions:
    print("No open positions")
else:
    stock_positions = []
    crypto_positions = []
    
    for p in positions:
        # Crypto symbols typically don't have exchange suffixes and are pairs like BTCUSD
        is_crypto = any(crypto in p.symbol for crypto in ['BTC', 'ETH', 'LTC', 'BCH', 'DOGE', 'SHIB', 'AVAX', 'SOL', 'ADA', 'MATIC', 'LINK', 'UNI'])
        
        position_info = {
            'symbol': p.symbol,
            'qty': float(p.qty),
            'side': p.side,
            'avg_entry_price': float(p.avg_entry_price),
            'market_value': float(p.market_value),
            'cost_basis': float(p.cost_basis),
            'unrealized_pl': float(p.unrealized_pl),
            'unrealized_plpc': float(p.unrealized_plpc) * 100,
            'current_price': float(p.current_price) if hasattr(p, 'current_price') else 0,
            'asset_class': p.asset_class if hasattr(p, 'asset_class') else 'unknown'
        }
        
        if is_crypto or p.symbol.endswith('USD') or p.symbol.endswith('USDT') or p.symbol.endswith('USDC'):
            crypto_positions.append(position_info)
        else:
            stock_positions.append(position_info)
    
    if stock_positions:
        print("\n📈 STOCK POSITIONS:")
        for p in stock_positions:
            print(f"  {p['symbol']:10s} | Qty: {p['qty']:10.4f} | Entry: ${p['avg_entry_price']:8.2f} | P&L: ${p['unrealized_pl']:+8.2f} ({p['unrealized_plpc']:+.2f}%)")
    
    if crypto_positions:
        print("\n🪙 CRYPTO POSITIONS:")
        for p in crypto_positions:
            print(f"  {p['symbol']:10s} | Qty: {p['qty']:10.8f} | Entry: ${p['avg_entry_price']:8.2f} | P&L: ${p['unrealized_pl']:+8.2f} ({p['unrealized_plpc']:+.2f}%)")
    
    # Show what the frontend is likely seeing
    print("\n🌐 WHAT THE FRONTEND SEES:")
    print(f"Total positions: {len(positions)}")
    print(f"Stock positions: {len(stock_positions)}")
    print(f"Crypto positions: {len(crypto_positions)}")

# Check if we can place crypto orders
print("\n🔧 CRYPTO TRADING CAPABILITY:")
try:
    # Check BTC asset
    btc = api.get_asset('BTCUSD')
    print(f"BTC/USD: Tradable={btc.tradable}, Status={btc.status}")
    
    # Get latest crypto quote
    quote = api.get_latest_crypto_quote('BTCUSD')
    print(f"BTC/USD Current Price: ${float(quote.ap):,.2f}")
    
    print("✅ Crypto trading is available")
except Exception as e:
    print(f"❌ Crypto trading error: {e}")

print("\n" + "="*60)