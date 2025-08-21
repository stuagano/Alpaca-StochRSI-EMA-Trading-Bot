#!/usr/bin/env python3
"""
Start Real-Time Data Streaming for Dashboard
"""

import sys
import os
import time
import threading
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def start_real_time_data():
    """Start the real-time data thread that feeds the dashboard"""
    print("🚀 Starting Real-Time Data Service")
    print("=" * 50)
    
    try:
        # Import necessary modules
        from data_manager import DataManager
        from config.unified_config import UnifiedConfig
        import alpaca_trade_api as tradeapi
        from dotenv import load_dotenv
        
        # Load environment
        load_dotenv()
        
        # Initialize config
        config = UnifiedConfig()
        config.load_config()
        
        # Initialize data manager
        print("📊 Initializing Data Manager...")
        data_manager = DataManager()
        
        # Initialize Alpaca API
        print("🔌 Connecting to Alpaca...")
        api = tradeapi.REST(
            key_id=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        )
        
        # Test connection
        account = api.get_account()
        print(f"✅ Connected - Balance: ${float(account.equity):,.2f}")
        
        # Get market status
        clock = api.get_clock()
        if clock.is_open:
            print("🟢 Market is OPEN - Live data available")
        else:
            print("🟡 Market is CLOSED - Using latest cached data")
        
        # Start fetching data for common symbols
        symbols = ['SPY', 'AAPL', 'TSLA', 'NVDA', 'AMD', 'GOOG']
        
        print(f"\n📈 Fetching data for: {', '.join(symbols)}")
        
        def update_data():
            """Continuously update data"""
            while True:
                try:
                    for symbol in symbols:
                        # Get latest price
                        try:
                            latest_trade = api.get_latest_trade(symbol)
                            if latest_trade:
                                print(f"  {symbol}: ${latest_trade.price:.2f}")
                        except Exception as e:
                            print(f"  {symbol}: Error - {e}")
                        
                        # Get bars for charting
                        try:
                            bars = api.get_bars(
                                symbol,
                                '1Min',
                                limit=100
                            ).df
                            
                            if not bars.empty:
                                # Store in data manager's cache
                                data_manager._cache[f"{symbol}_bars"] = bars
                                data_manager._cache[f"{symbol}_last_update"] = datetime.now()
                        except Exception as e:
                            print(f"  Error fetching bars for {symbol}: {e}")
                    
                    # Sleep based on market status
                    if clock.is_open:
                        time.sleep(5)  # Update every 5 seconds during market hours
                    else:
                        time.sleep(60)  # Update every minute after hours
                        
                except KeyboardInterrupt:
                    print("\n⚠️ Stopping data service...")
                    break
                except Exception as e:
                    print(f"❌ Error in update loop: {e}")
                    time.sleep(10)
        
        # Start update thread
        update_thread = threading.Thread(target=update_data, daemon=True)
        update_thread.start()
        
        print("\n✅ Real-time data service started!")
        print("📊 Data is being updated in the background")
        print("🌐 Dashboard should now show live data")
        print("\nPress Ctrl+C to stop...")
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down data service...")
            
    except Exception as e:
        print(f"❌ Failed to start data service: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    start_real_time_data()