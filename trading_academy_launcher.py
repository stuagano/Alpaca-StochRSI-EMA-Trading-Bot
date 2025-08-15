#!/usr/bin/env python3
"""
AI Trading Academy - Unified Launcher
=====================================

Complete educational and algorithmic trading platform that teaches
technical indicators and smart trading algorithm development.

Run this file to launch the interactive educational dashboard.
"""

import sys
import os
import subprocess
import logging
from pathlib import Path
from typing import Optional
import argparse

def setup_logging():
    """Setup basic logging for the launcher"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('launcher')

def check_dependencies():
    """Check if required dependencies are installed"""
    logger = logging.getLogger('launcher')
    
    required_packages = [
        'streamlit', 'pandas', 'numpy', 'plotly', 'ta', 
        'scipy', 'alpaca-py', 'flask', 'flask-socketio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error("Missing required packages:")
        for package in missing_packages:
            logger.error(f"  - {package}")
        
        logger.info("\nTo install missing packages, run:")
        logger.info("pip install -r requirements.txt")
        
        return False
    
    logger.info("All dependencies are installed ✅")
    return True

def setup_directories():
    """Create necessary directories"""
    logger = logging.getLogger('launcher')
    
    directories = [
        'logs',
        'config', 
        'backtest_results',
        'ORDERS',
        'database',
        'education'
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            logger.info(f"Created directory: {directory}")
    
    logger.info("Directory structure verified ✅")

def initialize_configurations():
    """Initialize default configurations if they don't exist"""
    logger = logging.getLogger('launcher')
    
    try:
        # Initialize configuration manager to create default configs
        from config.config_manager import get_config_manager
        config_manager = get_config_manager()
        
        # Initialize logging system
        from utils.logging_config import setup_logging
        setup_logging()
        
        logger.info("Configuration system initialized ✅")
        
    except Exception as e:
        logger.error(f"Configuration initialization failed: {e}")
        return False
    
    return True

def check_database():
    """Initialize database if needed"""
    logger = logging.getLogger('launcher')
    
    try:
        from database.models import DatabaseManager
        from services.data_service import get_data_service
        
        # Initialize database
        db_manager = DatabaseManager()
        data_service = get_data_service()
        
        logger.info("Database system initialized ✅")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False
    
    return True

def launch_educational_dashboard():
    """Launch the main educational dashboard"""
    logger = logging.getLogger('launcher')
    
    try:
        logger.info("🎓 Launching AI Trading Academy...")
        logger.info("Opening educational dashboard in your browser...")
        
        # Launch Streamlit app
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            "education/educational_dashboard.py",
            "--server.port=8501",
            "--server.headless=false",
            "--browser.gatherUsageStats=false",
            "--theme.base=dark"
        ]
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        logger.info("\n👋 Thanks for using AI Trading Academy!")
    except Exception as e:
        logger.error(f"Failed to launch dashboard: {e}")

def launch_flask_dashboard():
    """Launch the Flask-based trading dashboard"""
    logger = logging.getLogger('launcher')
    
    try:
        logger.info("🚀 Launching Flask Trading Dashboard...")
        
        # Import and run Flask app
        from flask_app import create_app
        app = create_app()
        
        logger.info("Flask dashboard running at: http://localhost:5000")
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except Exception as e:
        logger.error(f"Failed to launch Flask dashboard: {e}")

def launch_original_bot():
    """Launch the original trading bot"""
    logger = logging.getLogger('launcher')
    
    try:
        logger.info("🤖 Launching Original Trading Bot...")
        
        # Run the main trading bot
        import main
        
    except Exception as e:
        logger.error(f"Failed to launch trading bot: {e}")

def run_backtests():
    """Run sample backtests"""
    logger = logging.getLogger('launcher')
    
    try:
        logger.info("🔬 Running sample backtests...")
        
        from services.backtesting_service import get_backtesting_service
        backtesting_service = get_backtesting_service()
        
        # Run StochRSI strategy backtest
        result = backtesting_service.run_single_strategy_backtest(
            strategy_name="stochastic_rsi",
            ticker="SPY",
            start_date="2023-01-01",
            end_date="2023-12-31"
        )
        
        logger.info(f"Backtest Results:")
        logger.info(f"  Total Return: {result.total_return_pct:.2f}%")
        logger.info(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
        logger.info(f"  Max Drawdown: {result.max_drawdown_pct:.2f}%")
        logger.info(f"  Win Rate: {result.win_rate:.1f}%")
        
        # Generate report
        report = backtesting_service.backtesting_engine.generate_report(result)
        
        report_path = "backtest_results/sample_backtest_report.md"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Full report saved to: {report_path}")
        
    except Exception as e:
        logger.error(f"Backtesting failed: {e}")

def show_system_status():
    """Show system status and health check"""
    logger = logging.getLogger('launcher')
    
    logger.info("🔍 AI Trading Academy System Status")
    logger.info("=" * 50)
    
    # Check components
    components = {
        "Dependencies": check_dependencies(),
        "Configuration": initialize_configurations(),
        "Database": check_database(),
    }
    
    for component, status in components.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"{component}: {status_icon}")
    
    # Show available features
    logger.info("\n🎯 Available Features:")
    logger.info("  📊 Interactive Indicator Lessons")
    logger.info("  🤖 AI Trading Assistant") 
    logger.info("  🏗️ Strategy Builder")
    logger.info("  🔬 Backtesting Laboratory")
    logger.info("  ⚖️ Risk Management Tools")
    logger.info("  📈 Portfolio Analysis")
    logger.info("  🎮 Interactive Trading Playground")
    
    # Show quick start commands
    logger.info("\n🚀 Quick Start Commands:")
    logger.info("  python trading_academy_launcher.py --dashboard    # Educational Dashboard")
    logger.info("  python trading_academy_launcher.py --flask        # Trading Dashboard") 
    logger.info("  python trading_academy_launcher.py --bot          # Original Bot")
    logger.info("  python trading_academy_launcher.py --backtest     # Sample Backtest")
    
    return all(components.values())

def print_welcome_message():
    """Print welcome message with ASCII art"""
    
    welcome_text = """
    
╔══════════════════════════════════════════════════════════════════════╗
║                        🎓 AI TRADING ACADEMY 🎓                        ║
║                                                                      ║
║            Master Technical Indicators & Build Smart Algorithms      ║
║                                                                      ║
║  🎯 WHAT YOU'LL LEARN:                                               ║
║    📊 Technical Indicators (StochRSI, EMA, RSI, MACD, etc.)         ║
║    🏗️ Strategy Development & Optimization                           ║
║    ⚖️ Professional Risk Management                                   ║
║    🔬 Backtesting & Performance Analysis                             ║
║    🤖 AI-Powered Trading Assistance                                  ║
║                                                                      ║
║  🚀 FEATURES:                                                        ║
║    • Interactive Indicator Playground                               ║
║    • AI Trading Assistant (Chat-based tutor)                        ║
║    • Strategy Builder Wizard                                        ║
║    • Comprehensive Backtesting Lab                                  ║
║    • Risk Management Academy                                        ║
║    • Progress Tracking & Achievements                               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

    """
    
    print(welcome_text)

def main():
    """Main launcher function"""
    
    # Setup logging
    logger = setup_logging()
    
    # Print welcome message
    print_welcome_message()
    
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description="AI Trading Academy - Complete Educational Trading Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trading_academy_launcher.py                    # Launch educational dashboard (default)
  python trading_academy_launcher.py --dashboard        # Launch educational dashboard
  python trading_academy_launcher.py --flask            # Launch Flask trading dashboard
  python trading_academy_launcher.py --bot              # Launch original trading bot
  python trading_academy_launcher.py --backtest         # Run sample backtest
  python trading_academy_launcher.py --status           # Show system status
        """
    )
    
    parser.add_argument(
        '--dashboard', 
        action='store_true', 
        help='Launch the educational dashboard (default)'
    )
    
    parser.add_argument(
        '--flask', 
        action='store_true', 
        help='Launch Flask-based trading dashboard'
    )
    
    parser.add_argument(
        '--bot', 
        action='store_true', 
        help='Launch the original trading bot'
    )
    
    parser.add_argument(
        '--backtest', 
        action='store_true', 
        help='Run sample backtests'
    )
    
    parser.add_argument(
        '--status', 
        action='store_true', 
        help='Show system status and health check'
    )
    
    parser.add_argument(
        '--setup', 
        action='store_true', 
        help='Run initial setup and configuration'
    )
    
    args = parser.parse_args()
    
    # Setup directories
    setup_directories()
    
    # Handle different launch modes
    if args.status:
        show_system_status()
        return
    
    if args.setup:
        logger.info("🛠️ Running initial setup...")
        
        if not check_dependencies():
            logger.error("Please install dependencies first:")
            logger.error("pip install -r requirements.txt")
            return
        
        if not initialize_configurations():
            logger.error("Configuration setup failed")
            return
        
        if not check_database():
            logger.error("Database setup failed")
            return
        
        logger.info("✅ Setup completed successfully!")
        logger.info("Run 'python trading_academy_launcher.py' to start learning!")
        return
    
    # Check system status before launching
    logger.info("Performing system health check...")
    
    if not show_system_status():
        logger.error("\n❌ System health check failed!")
        logger.error("Run 'python trading_academy_launcher.py --setup' to fix issues")
        return
    
    logger.info("\n✅ System health check passed!")
    
    # Launch appropriate interface
    if args.flask:
        launch_flask_dashboard()
    elif args.bot:
        launch_original_bot()
    elif args.backtest:
        run_backtests()
    else:
        # Default: Launch educational dashboard
        launch_educational_dashboard()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Thanks for using AI Trading Academy!")
        print("Happy learning and profitable trading! 🚀")
    except Exception as e:
        print(f"\n❌ Launcher error: {e}")
        print("Try running: python trading_academy_launcher.py --setup")
        sys.exit(1)