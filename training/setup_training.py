#!/usr/bin/env python3
"""
Setup script for the trading training system
Initializes database, downloads sample data, and tests functionality
"""

import os
import subprocess
import sys
from datetime import datetime, timedelta
import sqlite3

def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False

def initialize_database():
    """Initialize the training database"""
    print("🗄️ Initializing training database...")
    try:
        from training_engine import TrainingDatabase
        db = TrainingDatabase()
        print(f"✅ Database initialized at: {db.db_path}")
        return db
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return None

def download_sample_data(db):
    """Download sample historical data for training"""
    print("📈 Downloading sample market data...")
    
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'SPY']
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')  # 2 years
    
    try:
        import yfinance as yf
        
        for symbol in symbols:
            print(f"  Downloading {symbol}...")
            data = yf.download(symbol, start=start_date, end=end_date, progress=False)
            if not data.empty:
                db.store_historical_data(symbol, data, '1d')
                print(f"  ✅ {symbol}: {len(data)} days stored")
            else:
                print(f"  ⚠️ {symbol}: No data available")
        
        print("✅ Sample data download completed")
        return True
        
    except Exception as e:
        print(f"❌ Sample data download failed: {e}")
        return False

def run_test_backtest(db):
    """Run a test backtest to verify functionality"""
    print("🧪 Running test backtest...")
    
    try:
        from training_engine import BacktestEngine
        
        backtest_engine = BacktestEngine(db)
        
        performance = backtest_engine.run_backtest(
            strategy_name='stoch_rsi_ema',
            symbol='AAPL',
            start_date='2023-01-01',
            end_date='2023-12-31',
            strategy_params={'rsi_oversold': 20, 'rsi_overbought': 80},
            initial_capital=10000
        )
        
        print("✅ Test backtest completed successfully!")
        print(f"   Total Return: {performance['total_return']:+.1f}%")
        print(f"   Win Rate: {performance['win_rate']:.1f}%")
        print(f"   Total Trades: {performance['total_trades']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test backtest failed: {e}")
        return False

def create_startup_scripts():
    """Create convenient startup scripts"""
    print("📝 Creating startup scripts...")
    
    # Create bash script for CLI
    cli_script = """#!/bin/bash
# Trading Training CLI Launcher

echo "🎯 Trading Training System"
echo "=========================="
echo ""
echo "Available commands:"
echo "  backtest   - Run strategy backtests"
echo "  collaborate - Start collaborative decision session"
echo "  compare    - Compare multiple strategies" 
echo "  learn      - Full learning session (backtest + decision)"
echo ""
echo "Examples:"
echo "  python cli_trainer.py backtest --symbol AAPL --days 180"
echo "  python cli_trainer.py collaborate --symbol TSLA"
echo "  python cli_trainer.py compare --symbol SPY"
echo "  python cli_trainer.py learn --symbol MSFT"
echo ""

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 [command] [options]"
    echo "For help: python cli_trainer.py --help"
else
    python cli_trainer.py "$@"
fi
"""
    
    with open('start_cli.sh', 'w') as f:
        f.write(cli_script)
    os.chmod('start_cli.sh', 0o755)
    
    # Create bash script for web dashboard
    dashboard_script = """#!/bin/bash
# Trading Training Dashboard Launcher

echo "🌐 Starting Trading Training Dashboard..."
echo "========================================"
echo ""
echo "Dashboard will be available at: http://localhost:5005"
echo "Press Ctrl+C to stop"
echo ""

python training_dashboard.py
"""
    
    with open('start_dashboard.sh', 'w') as f:
        f.write(dashboard_script)
    os.chmod('start_dashboard.sh', 0o755)
    
    print("✅ Startup scripts created:")
    print("   ./start_cli.sh - Command-line interface")
    print("   ./start_dashboard.sh - Web dashboard")

def main():
    """Main setup process"""
    print("🎯 Trading Training System Setup")
    print("=" * 40)
    print()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install requirements
    if not install_requirements():
        print("❌ Setup failed at requirements installation")
        sys.exit(1)
    
    # Initialize database
    db = initialize_database()
    if not db:
        print("❌ Setup failed at database initialization")
        sys.exit(1)
    
    # Download sample data
    if not download_sample_data(db):
        print("⚠️ Setup continued with sample data download issues")
    
    # Run test backtest
    if not run_test_backtest(db):
        print("⚠️ Setup continued with test backtest issues")
    
    # Create startup scripts
    create_startup_scripts()
    
    print("\n" + "=" * 50)
    print("🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print()
    print("🚀 Quick Start Options:")
    print()
    print("1. Command Line Interface:")
    print("   ./start_cli.sh learn --symbol AAPL")
    print()
    print("2. Web Dashboard:")
    print("   ./start_dashboard.sh")
    print("   Then open: http://localhost:5005")
    print()
    print("3. Direct Python:")
    print("   python cli_trainer.py collaborate --symbol TSLA")
    print("   python training_dashboard.py")
    print()
    print("📚 Features Available:")
    print("   ✅ Historical backtesting (4 strategies)")
    print("   ✅ Real-time collaborative decisions")
    print("   ✅ Strategy comparison and analytics")
    print("   ✅ Learning scenarios and training")
    print("   ✅ Performance tracking and insights")
    print()
    print(f"💾 Database: {db.db_path}")
    print("📖 Documentation: Check the README for detailed usage")
    print()
    print("Happy Trading and Learning! 🎯📈")

if __name__ == "__main__":
    main()