#!/usr/bin/env python3
"""Check real Alpaca account status"""

import alpaca_trade_api as tradeapi
from utils.alpaca import load_alpaca_credentials

# Load auth
creds = load_alpaca_credentials('AUTH/authAlpaca.txt')

api = tradeapi.REST(
    creds.key_id,
    creds.secret_key,
    creds.base_url,
    api_version='v2'
)

# Check account
account = api.get_account()
print(f'💰 Buying Power: ${float(account.buying_power):,.2f}')
print(f'💵 Cash: ${float(account.cash):,.2f}')
print(f'📊 Portfolio Value: ${float(account.portfolio_value):,.2f}')
print(f'🔒 Pattern Day Trader: {account.pattern_day_trader}')

# Get positions
print('\n=== REAL CRYPTO POSITIONS ===')
positions = api.list_positions()
if positions:
    for pos in positions:
        print(f'{pos.symbol}: {pos.qty} @ ${pos.avg_entry_price} (P&L: ${float(pos.unrealized_pl):.2f})')
else:
    print('❌ No open positions found!')

# Get recent orders
print('\n=== RECENT ORDERS (Last 10) ===')
orders = api.list_orders(status='all', limit=10)
if orders:
    for order in orders[:10]:
        print(f'{order.symbol}: {order.side} {order.qty} @ {order.order_type} - {order.status}')
        if order.status == 'rejected':
            print(f'  ⚠️ Rejection reason: Check Alpaca dashboard')
else:
    print('❌ No recent orders!')

# Check if this is paper or live
if creds.is_paper:
    print('\n⚠️  PAPER TRADING ACCOUNT')
else:
    print('\n🔴 LIVE TRADING ACCOUNT')
