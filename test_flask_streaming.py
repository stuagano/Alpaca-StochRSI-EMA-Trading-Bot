#!/usr/bin/env python3
"""
Test script to validate Flask streaming data flow
"""
import socketio
import time
import json

# Create Socket.IO client
sio = socketio.Client()

@sio.event
def connect():
    print("✅ Connected to Flask server")
    print("🚀 Starting streaming...")
    sio.emit('start_streaming', {'interval': 3})

@sio.event
def disconnect():
    print("❌ Disconnected from server")

@sio.event
def real_time_update(data):
    print("📊 Real-time update received:")
    print(f"   Data keys: {list(data.keys())}")
    
    if 'account_info' in data and data['account_info']:
        account = data['account_info']
        print(f"   💰 Account: Portfolio=${account.get('portfolio_value', 0):.2f}, Cash=${account.get('cash', 0):.2f}")
    else:
        print("   ⚠️  No account_info")
    
    if 'positions' in data and data['positions']:
        positions = data['positions']
        print(f"   📈 Positions: {len(positions)} active")
        for pos in positions[:3]:  # Show first 3
            print(f"      {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']:.2f}")
    else:
        print("   ⚠️  No positions")
    
    if 'ticker_prices' in data and data['ticker_prices']:
        prices = data['ticker_prices']
        print(f"   💲 Prices: {len(prices)} tickers")
        for ticker, price in list(prices.items())[:3]:  # Show first 3
            print(f"      {ticker}: ${price:.4f}")
    else:
        print("   ⚠️  No ticker_prices")
    
    if 'ticker_signals' in data and data['ticker_signals']:
        signals = data['ticker_signals']
        print(f"   🎯 Signals: {len(signals)} tickers")
        for ticker, signal_data in list(signals.items())[:3]:  # Show first 3
            if 'stochRSI' in signal_data:
                stoch = signal_data['stochRSI']
                print(f"      {ticker}: StochRSI K={stoch.get('k', 'N/A'):.1f}, D={stoch.get('d', 'N/A'):.1f}, Signal={stoch.get('signal', 0)}")
    else:
        print("   ⚠️  No ticker_signals")
    
    print("-" * 60)

@sio.event
def streaming_status(data):
    status = "Active" if data.get('active', False) else "Inactive"
    interval = data.get('interval', 0)
    print(f"📡 Streaming status: {status} (interval: {interval}s)")

if __name__ == '__main__':
    try:
        print("🔌 Connecting to Flask server at http://localhost:9765...")
        sio.connect('http://localhost:9765')
        
        # Keep running for 30 seconds
        print("⏰ Listening for 30 seconds...")
        time.sleep(30)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🛑 Stopping streaming...")
        sio.emit('stop_streaming')
        time.sleep(1)
        sio.disconnect()
        print("✅ Test completed")