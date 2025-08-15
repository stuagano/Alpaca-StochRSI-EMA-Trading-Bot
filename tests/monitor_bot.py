#!/usr/bin/env python3
"""Monitor the trading bot's activity."""

import sys
import os
import json
from datetime import datetime
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def monitor_bot():
    """Monitor bot activity through logs and database."""
    
    print("=" * 60)
    print("🔍 ALPACA TRADING BOT MONITOR")
    print("=" * 60)
    
    # Check if bot is configured
    config_file = "config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"\n📋 Configuration:")
        print(f"  - Strategy: {config.get('strategy', 'Unknown')}")
        print(f"  - Timeframe: {config.get('timeframe', 'Unknown')}")
        print(f"  - Symbol: {config.get('symbol', 'Unknown')}")
        print(f"  - Trade Quantity: {config.get('trade_quantity', 'Unknown')}")
    
    # Check latest log entries
    log_file = "logs/trading_bot.log"
    if os.path.exists(log_file):
        print(f"\n📊 Latest Log Entries:")
        with open(log_file, 'r') as f:
            lines = f.readlines()
            # Get last 20 lines
            for line in lines[-20:]:
                try:
                    log_entry = json.loads(line.strip())
                    timestamp = log_entry.get('asctime', '')
                    level = log_entry.get('levelname', '')
                    message = log_entry.get('message', '')
                    
                    # Color code by level
                    if level == 'ERROR':
                        print(f"  🔴 [{timestamp}] {message[:100]}")
                    elif level == 'WARNING':
                        print(f"  ⚠️  [{timestamp}] {message[:100]}")
                    elif level == 'INFO':
                        if 'trade' in message.lower() or 'order' in message.lower():
                            print(f"  💹 [{timestamp}] {message[:100]}")
                        elif 'signal' in message.lower():
                            print(f"  📡 [{timestamp}] {message[:100]}")
                        else:
                            print(f"  ℹ️  [{timestamp}] {message[:100]}")
                except:
                    # If not JSON, print as is
                    print(f"  📝 {line.strip()[:100]}")
    
    # Check database for recent trades
    db_file = "trading_bot.db"
    if os.path.exists(db_file):
        import sqlite3
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        try:
            # Get trade count
            cursor.execute("SELECT COUNT(*) FROM trades")
            trade_count = cursor.fetchone()[0]
            print(f"\n💼 Database Statistics:")
            print(f"  - Total Trades: {trade_count}")
            
            # Get recent trades
            cursor.execute("""
                SELECT timestamp, symbol, side, quantity, price, status 
                FROM trades 
                ORDER BY timestamp DESC 
                LIMIT 5
            """)
            recent_trades = cursor.fetchall()
            
            if recent_trades:
                print(f"\n📈 Recent Trades:")
                for trade in recent_trades:
                    timestamp, symbol, side, quantity, price, status = trade
                    print(f"  - {timestamp}: {side} {quantity} {symbol} @ ${price} [{status}]")
        except Exception as e:
            print(f"  ⚠️  Database query error: {e}")
        finally:
            conn.close()
    
    # Check Alpaca connection
    try:
        from alpaca_trade_api import REST
        
        api = REST(
            key_id=os.getenv('APCA_API_KEY_ID'),
            secret_key=os.getenv('APCA_API_SECRET_KEY'),
            base_url=os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
        )
        
        account = api.get_account()
        print(f"\n💰 Alpaca Account Status:")
        print(f"  - Status: {account.status}")
        print(f"  - Buying Power: ${float(account.buying_power):,.2f}")
        print(f"  - Portfolio Value: ${float(account.portfolio_value):,.2f}")
        print(f"  - Cash: ${float(account.cash):,.2f}")
        
        # Get open positions
        positions = api.list_positions()
        if positions:
            print(f"\n📊 Open Positions:")
            for pos in positions[:5]:
                print(f"  - {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f} (P/L: ${float(pos.unrealized_pl):.2f})")
        
        # Get recent orders
        orders = api.list_orders(status='all', limit=5)
        if orders:
            print(f"\n📝 Recent Orders:")
            for order in orders:
                print(f"  - {order.created_at}: {order.side} {order.qty} {order.symbol} [{order.status}]")
                
    except Exception as e:
        print(f"\n⚠️  Could not connect to Alpaca: {e}")
    
    print("\n" + "=" * 60)
    print(f"🕐 Monitored at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    monitor_bot()