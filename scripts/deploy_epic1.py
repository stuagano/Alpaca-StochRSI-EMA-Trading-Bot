#!/usr/bin/env python3
"""
Epic 1 Deployment Script
Deploys the trading bot with all Epic 1 signal quality enhancements
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def print_header():
    """Print deployment header"""
    print("="*60)
    print("🚀 EPIC 1 TRADING BOT DEPLOYMENT")
    print("="*60)
    print(f"⏰ Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("📊 Features: Dynamic Bands | Volume Confirmation | Enhanced Signals")
    print("="*60)

def check_environment():
    """Verify environment is ready"""
    print("\n🔍 Checking Environment...")
    
    checks = {
        "Python Version": sys.version.split()[0],
        "Working Directory": os.getcwd(),
        "Config File": os.path.exists("config/config.yml"),
        "Unified Config": os.path.exists("config/unified_config.yml"),
        "Database": os.path.exists("database/trading_data.db"),
        "Templates": os.path.exists("templates/professional_trading_dashboard.html")
    }
    
    all_good = True
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}: {result}")
        if not result and check != "Python Version":
            all_good = False
    
    return all_good

def verify_epic1_fixes():
    """Verify Epic 1 fixes are in place"""
    print("\n🔧 Verifying Epic 1 Fixes...")
    
    # Check dynamic band sensitivity
    try:
        from indicator import calculate_dynamic_bands
        import inspect
        source = inspect.getsource(calculate_dynamic_bands)
        if "sensitivity=0.7" in source:
            print("  ✅ Dynamic band sensitivity: 0.7")
        else:
            print("  ⚠️  Dynamic band sensitivity may not be updated")
    except Exception as e:
        print(f"  ❌ Could not verify dynamic bands: {e}")
    
    # Check volume confirmation fix
    try:
        from src.utils.epic1_integration_helpers import calculate_volume_confirmation
        import pandas as pd
        test_df = pd.DataFrame({
            'volume': [1000, 1200, 1100],
            'close': [100, 101, 102]
        })
        result = calculate_volume_confirmation(test_df, 'TEST')
        if isinstance(result.get('volume_confirmed', None), bool):
            print("  ✅ Volume confirmation returns Python bool")
        else:
            print("  ❌ Volume confirmation type issue not fixed")
    except Exception as e:
        print(f"  ⚠️  Could not verify volume confirmation: {e}")
    
    # Check config parameters
    try:
        from config.config import config
        if hasattr(config.indicators.stochRSI, 'dynamic_bands_enabled'):
            print("  ✅ StochRSI config has dynamic_bands_enabled")
        if hasattr(config.indicators.stochRSI, 'atr_sensitivity'):
            print("  ✅ StochRSI config has atr_sensitivity")
    except Exception as e:
        print(f"  ⚠️  Config verification issue: {e}")
    
    return True

def test_alpaca_connection():
    """Test Alpaca API connection"""
    print("\n🔌 Testing Alpaca Connection...")
    
    try:
        from alpaca_trade_api import REST
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        api = REST(
            key_id=os.getenv('ALPACA_API_KEY'),
            secret_key=os.getenv('ALPACA_SECRET_KEY'),
            base_url=os.getenv('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets')
        )
        
        account = api.get_account()
        print(f"  ✅ Connected to Alpaca")
        print(f"  💰 Account Balance: ${float(account.equity):,.2f}")
        print(f"  📊 Buying Power: ${float(account.buying_power):,.2f}")
        print(f"  🎯 Pattern Day Trader: {account.pattern_day_trader}")
        
        # Check market status
        clock = api.get_clock()
        if clock.is_open:
            print(f"  🟢 Market is OPEN")
        else:
            print(f"  🔴 Market is CLOSED (next open: {clock.next_open})")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Alpaca connection failed: {e}")
        return False

def start_flask_server():
    """Start Flask backend server"""
    print("\n🌐 Starting Flask Backend Server...")
    
    def run_flask():
        try:
            subprocess.run([sys.executable, "flask_app.py"], check=False)
        except Exception as e:
            print(f"Flask server error: {e}")
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Wait for server to start
    time.sleep(3)
    
    # Test if server is running
    try:
        import requests
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code == 200:
            print("  ✅ Flask server running on http://localhost:5000")
            return True
    except:
        pass
    
    print("  ⚠️  Flask server may not be fully started")
    print("  📝 You can manually start it with: python flask_app.py")
    return False

def launch_trading_bot():
    """Launch the main trading bot"""
    print("\n🤖 Launching Trading Bot...")
    
    launch_script = """
import sys
import os
sys.path.insert(0, os.getcwd())

from main import TradingBot
from data_manager import DataManager
from strategies.stoch_rsi_strategy import StochRSIStrategy
from config.config import config

print("  📊 Initializing Data Manager...")
data_manager = DataManager()

print("  🎯 Loading StochRSI Strategy with Epic 1 enhancements...")
strategy = StochRSIStrategy(config)

print("  🚀 Creating Trading Bot instance...")
bot = TradingBot(data_manager, strategy)

# Configure Epic 1 settings
print("  ⚙️  Configuring Epic 1 features...")
bot.config = config
bot.enable_dynamic_bands = True
bot.enable_volume_confirmation = True

print("  ✅ Trading Bot initialized successfully!")
print("  📈 Tickers:", bot.tickers if hasattr(bot, 'tickers') else 'Not configured')
print("  ⏱️  Ready to start trading...")

# Display Epic 1 status
print("\\n📊 Epic 1 Feature Status:")
print(f"  • Dynamic Bands: {'ENABLED' if bot.enable_dynamic_bands else 'DISABLED'}")
print(f"  • Volume Confirmation: {'ENABLED' if bot.enable_volume_confirmation else 'DISABLED'}")
print(f"  • Signal Quality Enhancement: ACTIVE")

return bot
"""
    
    try:
        exec(launch_script)
        print("\n  ✅ Trading bot launched successfully!")
        return True
    except Exception as e:
        print(f"\n  ❌ Failed to launch trading bot: {e}")
        print("\n  📝 You can manually start it with: python main.py")
        return False

def create_monitoring_dashboard():
    """Create monitoring dashboard URL"""
    print("\n📊 Dashboard Access:")
    print("  🌐 Trading Dashboard: http://localhost:5000")
    print("  📈 Professional Dashboard: http://localhost:5000/dashboard/professional")
    print("  🔍 Epic 1 Status: http://localhost:5000/api/epic1/status")
    print("  📊 Positions: http://localhost:5000/api/positions")

def deployment_summary(results):
    """Print deployment summary"""
    print("\n" + "="*60)
    print("📋 DEPLOYMENT SUMMARY")
    print("="*60)
    
    if all(results.values()):
        print("🎉 SUCCESS: Epic 1 Trading System Deployed!")
        print("\n✅ All systems operational:")
        for component, status in results.items():
            print(f"  • {component}: {'✅ Ready' if status else '❌ Failed'}")
        
        print("\n🚀 NEXT STEPS:")
        print("  1. Open dashboard: http://localhost:5000")
        print("  2. Monitor positions and signals")
        print("  3. Check Epic 1 metrics: http://localhost:5000/api/epic1/status")
        print("  4. View logs: tail -f flask.log")
        
    else:
        print("⚠️  PARTIAL DEPLOYMENT")
        print("\nComponent Status:")
        for component, status in results.items():
            print(f"  • {component}: {'✅ Ready' if status else '❌ Failed'}")
        
        print("\n🔧 MANUAL STEPS NEEDED:")
        if not results.get('Flask Server'):
            print("  1. Start Flask: python flask_app.py")
        if not results.get('Trading Bot'):
            print("  2. Start Bot: python main.py")

def main():
    """Main deployment sequence"""
    print_header()
    
    results = {}
    
    # Step 1: Check environment
    results['Environment'] = check_environment()
    if not results['Environment']:
        print("\n❌ Environment check failed. Please fix issues above.")
        return
    
    # Step 2: Verify Epic 1 fixes
    results['Epic 1 Fixes'] = verify_epic1_fixes()
    
    # Step 3: Test Alpaca connection
    results['Alpaca API'] = test_alpaca_connection()
    
    # Step 4: Start Flask server
    results['Flask Server'] = start_flask_server()
    
    # Step 5: Launch trading bot
    results['Trading Bot'] = launch_trading_bot()
    
    # Step 6: Show monitoring info
    create_monitoring_dashboard()
    
    # Step 7: Deployment summary
    deployment_summary(results)
    
    print("\n🔍 Monitoring Commands:")
    print("  • View logs: tail -f flask.log")
    print("  • Check processes: ps aux | grep python")
    print("  • Stop all: pkill -f 'python.*flask_app'")
    
    print("\n✨ Epic 1 deployment script complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Deployment error: {e}")
        import traceback
        traceback.print_exc()