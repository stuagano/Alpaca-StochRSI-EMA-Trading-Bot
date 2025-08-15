#!/usr/bin/env python3
"""
AI Trading Academy - Initial Setup Script
==========================================

Run this script first to set up your AI Trading Academy.
This will install dependencies, create configurations, and prepare the system.

Usage:
    python setup_academy.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def print_header():
    """Print setup header"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    🎓 AI TRADING ACADEMY SETUP 🎓                     ║
║                                                                      ║
║              Setting up your complete trading education platform      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"   Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True


def install_dependencies():
    """Install required packages"""
    print("\n📦 Installing dependencies...")
    
    try:
        # Install requirements
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ All dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def create_directory_structure():
    """Create necessary directories"""
    print("\n📁 Creating directory structure...")
    
    directories = [
        'logs',
        'config',
        'backtest_results', 
        'ORDERS',
        'database',
        'education',
        'risk_management',
        'backtesting',
        'services',
        'utils'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"  ✓ Created {directory}/")
    
    print("✅ Directory structure created")


def create_sample_config():
    """Create sample configuration files"""
    print("\n⚙️ Creating sample configurations...")
    
    # Sample Alpaca config (user will need to add their keys)
    alpaca_config = {
        "base_url": "https://paper-api.alpaca.markets",
        "api_key": "YOUR_API_KEY_HERE", 
        "api_secret": "YOUR_SECRET_KEY_HERE",
        "paper_trading": True,
        "timeout": 30
    }
    
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    with open(config_dir / "alpaca.json", "w") as f:
        json.dump(alpaca_config, f, indent=4)
    
    print("  ✓ Created config/alpaca.json")
    print("    📝 Remember to add your Alpaca API credentials!")
    
    # Create sample orders file
    orders_dir = Path("ORDERS")
    orders_dir.mkdir(exist_ok=True)
    
    sample_orders = """Time,Ticker,Type,Buy Price,Sell Price,Highest Price,Quantity,Total,Acc Balance,Target Price,Stop Loss Price,ActivateTrailingStopAt
2024-01-15 10:30:00,AAPL,buy,150.00,-,150.00,10,1500.00,100000.00,157.50,142.50,153.00"""
    
    with open(orders_dir / "sample_orders.csv", "w") as f:
        f.write(sample_orders)
    
    print("  ✓ Created ORDERS/sample_orders.csv")
    print("✅ Sample configurations created")


def create_launcher_alias():
    """Create convenient launcher alias"""
    print("\n🚀 Creating launcher shortcuts...")
    
    # Create a simple start script
    start_script = """#!/bin/bash
echo "🎓 Starting AI Trading Academy..."
python trading_academy_launcher.py
"""
    
    with open("start_academy.sh", "w") as f:
        f.write(start_script)
    
    # Make executable on Unix systems
    if os.name != 'nt':
        os.chmod("start_academy.sh", 0o755)
        print("  ✓ Created start_academy.sh")
    
    # Create Windows batch file
    windows_script = """@echo off
echo 🎓 Starting AI Trading Academy...
python trading_academy_launcher.py
pause
"""
    
    with open("start_academy.bat", "w") as f:
        f.write(windows_script)
    
    print("  ✓ Created start_academy.bat")
    print("✅ Launcher shortcuts created")


def run_initial_tests():
    """Run initial system tests"""
    print("\n🔧 Running system tests...")
    
    try:
        # Test imports
        print("  Testing imports...")
        import pandas
        import numpy 
        import plotly
        import streamlit
        print("    ✓ Core libraries imported successfully")
        
        # Test database creation
        print("  Testing database...")
        from database.models import DatabaseManager
        db = DatabaseManager("test.db")
        os.remove("test.db")  # Clean up test db
        print("    ✓ Database system working")
        
        # Test configuration
        print("  Testing configuration...")
        from config.config_manager import get_config_manager
        config_manager = get_config_manager()
        print("    ✓ Configuration system working")
        
        print("✅ All system tests passed")
        return True
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        return False


def show_next_steps():
    """Show what to do next"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                        🎉 SETUP COMPLETE! 🎉                         ║
╚══════════════════════════════════════════════════════════════════════╝

🚀 NEXT STEPS:

1️⃣  ADD YOUR ALPACA API CREDENTIALS:
   • Edit config/alpaca.json
   • Add your API key and secret from alpaca.markets
   • Keep paper_trading: true for safe learning!

2️⃣  START YOUR AI TRADING ACADEMY:
   
   Method 1 - Full Educational Dashboard:
   python trading_academy_launcher.py
   
   Method 2 - Quick launcher scripts:
   ./start_academy.sh        (Mac/Linux)
   start_academy.bat         (Windows)

3️⃣  BEGIN YOUR LEARNING JOURNEY:
   • Start with the "Indicator Academy" 
   • Learn about your current StochRSI strategy
   • Chat with your AI Trading Assistant
   • Build and backtest new strategies

📚 HELPFUL COMMANDS:
   python trading_academy_launcher.py --status     # Check system health
   python trading_academy_launcher.py --flask      # Original enhanced dashboard  
   python trading_academy_launcher.py --backtest   # Run sample backtests

📖 READ THE FULL GUIDE:
   Open README_TRADING_ACADEMY.md for complete documentation

🎓 Happy learning and profitable trading!

    """)


def main():
    """Main setup function"""
    print_header()
    
    # Check system requirements
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed during dependency installation")
        sys.exit(1)
    
    # Create directory structure
    create_directory_structure()
    
    # Create sample configurations
    create_sample_config()
    
    # Create launcher shortcuts
    create_launcher_alias()
    
    # Run tests
    if not run_initial_tests():
        print("⚠️  Setup completed but some tests failed")
        print("   The system should still work, but you may need to troubleshoot")
    
    # Show next steps
    show_next_steps()
    
    print("✅ AI Trading Academy setup completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Setup interrupted by user")
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        print("Please check the error message and try again")
        sys.exit(1)