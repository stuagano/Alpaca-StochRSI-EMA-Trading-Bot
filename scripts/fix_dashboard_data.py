#!/usr/bin/env python3
"""
Fix Dashboard Data Rendering Issue
Clears stale cache and ensures fresh market data is displayed
"""

import sys
import os
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_dashboard_data():
    """Clear stale cache and force fresh data fetch"""
    print("🔧 Fixing Dashboard Data Rendering")
    print("=" * 50)
    
    try:
        # Import necessary modules
        from services.unified_data_manager import UnifiedDataManager
        from core.service_registry import get_service_registry, setup_core_services
        import alpaca_trade_api as tradeapi
        from dotenv import load_dotenv
        
        # Load environment
        load_dotenv()
        
        print("📊 Step 1: Initializing services...")
        
        # Setup core services first
        setup_core_services()
        
        # Get the data manager from registry
        registry = get_service_registry()
        data_manager = registry.get('data_manager')
        
        print("📊 Step 2: Clearing stale cache...")
        
        # Clear any in-memory cache
        if hasattr(data_manager, '_cache'):
            data_manager._cache.clear()
            print("✅ In-memory cache cleared")
        
        # Clear database cache for old data
        if hasattr(data_manager, 'db'):
            try:
                # Clear historical data older than 1 day
                from datetime import datetime, timedelta
                cutoff = datetime.now() - timedelta(days=1)
                
                # Execute cleanup
                conn = data_manager.db.conn
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM historical_data 
                    WHERE timestamp < ?
                """, (cutoff.isoformat(),))
                conn.commit()
                print(f"✅ Cleared {cursor.rowcount} stale database records")
            except Exception as e:
                print(f"⚠️ Could not clear database cache: {e}")
        
        print("\n📊 Step 3: Fetching fresh market data...")
        
        # Initialize fresh Alpaca connection
        api = tradeapi.REST(
            key_id=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            base_url='https://paper-api.alpaca.markets'
        )
        
        # Update data manager's API connection
        data_manager.api = api
        
        # Test with common symbols
        symbols = ['SPY', 'AAPL', 'TSLA', 'NVDA']
        
        for symbol in symbols:
            try:
                # Force fresh fetch from Alpaca
                bars = api.get_bars(
                    symbol,
                    '1Min',
                    start=datetime.now() - timedelta(hours=4),
                    end=datetime.now(),
                    limit=100
                ).df
                
                if not bars.empty:
                    latest = bars.iloc[-1]
                    print(f"  {symbol}: ${latest['close']:.2f} (Last update: {bars.index[-1]})")
                    
                    # Store in data manager cache
                    if hasattr(data_manager, '_cache'):
                        data_manager._cache[f"{symbol}_bars"] = bars
                        data_manager._cache[f"{symbol}_last_update"] = datetime.now()
            except Exception as e:
                print(f"  {symbol}: Error - {e}")
        
        print("\n📊 Step 4: Verifying data flow...")
        
        # Test the get_historical_data method
        test_data = data_manager.get_historical_data('SPY', '1Min', limit=5)
        if not test_data.empty:
            print(f"✅ Data manager returning {len(test_data)} rows")
            latest_timestamp = test_data.index[-1]
            print(f"✅ Latest data timestamp: {latest_timestamp}")
            
            # Check if it's today's data
            if latest_timestamp.date() == datetime.now().date():
                print("✅ Data is from today - FRESH!")
            else:
                print(f"⚠️ Data is from {latest_timestamp.date()} - may be stale")
        
        print("\n✨ Dashboard data fix complete!")
        print("📈 Dashboards should now show live market data")
        print("\nRefresh your browser to see updated data:")
        print("  http://localhost:9765")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix dashboard data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_dashboard_data()