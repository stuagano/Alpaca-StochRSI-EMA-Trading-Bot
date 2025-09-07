#!/usr/bin/env python3
import alpaca_trade_api as tradeapi
import os
from datetime import datetime

# Initialize API
api = tradeapi.REST(
    os.getenv('APCA_API_KEY_ID'),
    os.getenv('APCA_API_SECRET_KEY'),
    os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
)

# Get all positions
positions = api.list_positions()
crypto_positions = [p for p in positions if 'USD' in p.symbol]

print(f"\n🪙 Crypto Positions Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)
print(f"Total crypto positions: {len(crypto_positions)}")
print(f"Total all positions: {len(positions)}")
print("=" * 60)

total_value = 0
for p in crypto_positions:
    value = float(p.market_value)
    total_value += value
    pl = float(p.unrealized_pl)
    pl_pct = float(p.unrealized_plpc) * 100
    print(f"\n{p.symbol}:")
    print(f"  Quantity: {p.qty}")
    print(f"  Avg Price: ${p.avg_entry_price}")
    print(f"  Current Price: ${p.current_price}")
    print(f"  Market Value: ${value:,.2f}")
    print(f"  P/L: ${pl:,.2f} ({pl_pct:+.2f}%)")

print("\n" + "=" * 60)
print(f"Total Crypto Portfolio Value: ${total_value:,.2f}")

# Check recent orders
print("\n📋 Recent Crypto Orders (Last 10):")
print("=" * 60)
orders = api.list_orders(status='all', limit=50)
crypto_orders = [o for o in orders if 'USD' in o.symbol][:10]

for o in crypto_orders:
    print(f"{o.submitted_at.strftime('%H:%M:%S')} - {o.side.upper()} {o.qty} {o.symbol} @ ${o.limit_price or 'MARKET'} - {o.status}")