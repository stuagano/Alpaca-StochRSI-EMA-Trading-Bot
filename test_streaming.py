#!/usr/bin/env python3
"""
Test script to verify the real-time streaming functionality.
This simulates a frontend client connecting and starting streaming.
"""

import socketio
import time
import json

def test_streaming():
    print("🔄 Testing real-time streaming functionality...")
    
    # Connect to the Flask-SocketIO server
    sio = socketio.Client(logger=True, engineio_logger=True)
    updates_received = 0
    
    @sio.event
    def connect():
        print("✅ Connected to Flask-SocketIO server")
        
    @sio.event  
    def connected(data):
        print(f"🔗 Server connection established: {data}")
        
    @sio.event
    def real_time_update(data):
        nonlocal updates_received
        updates_received += 1
        
        print(f"📊 Received real-time update #{updates_received}:")
        print(f"   Account info: {'✅' if data.get('account_info') else '❌'}")
        print(f"   Positions: {len(data.get('positions', []))} positions")
        print(f"   Ticker prices: {len(data.get('ticker_prices', {}))} prices")
        print(f"   Ticker signals: {len(data.get('ticker_signals', {}))} signals")
        
        if data.get('ticker_prices'):
            print("   📈 Prices received:")
            for ticker, price in data['ticker_prices'].items():
                print(f"      {ticker}: ${price:.4f}")
                
        if data.get('ticker_signals'):
            print("   🎯 Signals received:")
            for ticker, signals in data['ticker_signals'].items():
                if 'stochRSI' in signals:
                    stochrsi = signals['stochRSI']
                    signal_status = "🟢 BUY" if stochrsi['signal'] == 1 else "🔴 WAIT"
                    print(f"      {ticker} StochRSI: {signal_status} (K:{stochrsi['k']:.2f}, D:{stochrsi['d']:.2f})")
        print("-" * 50)
        
    @sio.event
    def streaming_status(data):
        status = "🟢 ACTIVE" if data['active'] else "🔴 INACTIVE"
        print(f"📡 Streaming status: {status} (interval: {data.get('interval', 'unknown')}s)")
        
    @sio.event
    def disconnect():
        print("❌ Disconnected from server")
    
    try:
        # Connect to the server
        sio.connect('http://localhost:9765')
        
        # Wait for connection
        time.sleep(2)
        
        # Start streaming
        print("🚀 Starting streaming...")
        sio.emit('start_streaming', {'interval': 5})
        
        # Listen for updates for 15 seconds
        print("⏳ Listening for real-time updates for 15 seconds...")
        start_time = time.time()
        updates_received = 0
        
        while time.time() - start_time < 15:
            sio.sleep(1)  # Use socket.io sleep to process events
            if updates_received == 0:
                print("  ⏳ Waiting for first update...")
        
        if updates_received == 0:
            print("⚠️  No real-time updates received during test period")
        
        # Stop streaming
        print("🛑 Stopping streaming...")
        sio.emit('stop_streaming')
        time.sleep(2)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        sio.disconnect()
        print("🔚 Test completed")

if __name__ == "__main__":
    test_streaming()