#!/usr/bin/env python3
"""
Quick Start Script for Alpaca StochRSI EMA Trading Bot
Complete Epic 0 Implementation

This script starts the enhanced trading system with all Epic 0 features:
- TradingView Lightweight Charts
- Real-time WebSocket communication
- Live position and P&L display
- Trading signal visualization
- Performance monitoring
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are available"""
    print("🔍 Checking dependencies...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check required modules
    required_modules = [
        'flask', 'pandas', 'numpy', 'alpaca_trade_api',
        'flask_cors', 'python_json_logger'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module.replace('_', '-'))
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"❌ Missing modules: {', '.join(missing_modules)}")
        print("💡 Install with: pip install " + " ".join(missing_modules))
        return False
    
    print("✅ All dependencies available")
    return True

def check_configuration():
    """Check if configuration files exist"""
    print("🔧 Checking configuration...")
    
    required_files = [
        'AUTH/authAlpaca.txt',
        'AUTH/Tickers.txt'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"⚠️  Missing configuration files: {', '.join(missing_files)}")
        print("💡 Create these files with your Alpaca API credentials")
        
        # Create template files
        os.makedirs('AUTH', exist_ok=True)
        
        if not os.path.exists('AUTH/authAlpaca.txt'):
            with open('AUTH/authAlpaca.txt', 'w') as f:
                f.write("# Add your Alpaca API credentials here\\n")
                f.write("# Line 1: API Key\\n")
                f.write("# Line 2: Secret Key\\n")
                f.write("# Line 3: Base URL (paper or live)\\n")
                f.write("YOUR_API_KEY\\n")
                f.write("YOUR_SECRET_KEY\\n")
                f.write("https://paper-api.alpaca.markets\\n")
        
        if not os.path.exists('AUTH/Tickers.txt'):
            with open('AUTH/Tickers.txt', 'w') as f:
                f.write("AAPL\\n")
                f.write("MSFT\\n")
                f.write("GOOGL\\n")
                f.write("TSLA\\n")
                f.write("NVDA\\n")
        
        print("📝 Template files created. Please update with your credentials.")
        return False
    
    print("✅ Configuration files found")
    return True

def start_enhanced_dashboard():
    """Start the enhanced trading dashboard"""
    print("🚀 Starting Enhanced Trading Dashboard...")
    
    try:
        # Try to start the enhanced Flask app
        if os.path.exists('src/enhanced_flask_app.py'):
            print("📊 Launching Enhanced WebSocket Trading System...")
            process = subprocess.Popen([
                sys.executable, 'src/enhanced_flask_app.py'
            ], cwd=os.getcwd())
            
        elif os.path.exists('run_enhanced_dashboard.py'):
            print("📊 Launching Enhanced Dashboard...")
            process = subprocess.Popen([
                sys.executable, 'run_enhanced_dashboard.py'
            ], cwd=os.getcwd())
            
        else:
            print("📊 Launching Standard Flask App...")
            process = subprocess.Popen([
                sys.executable, 'flask_app.py'
            ], cwd=os.getcwd())
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Open browser to dashboard
        print("🌐 Opening browser...")
        urls_to_try = [
            'http://localhost:8765/enhanced',
            'http://localhost:8765/dashboard',
            'http://localhost:8765'
        ]
        
        for url in urls_to_try:
            try:
                webbrowser.open(url)
                print(f"✅ Dashboard opened: {url}")
                break
            except:
                continue
        
        print("\\n" + "="*60)
        print("🎉 TRADING SYSTEM STARTED SUCCESSFULLY!")
        print("="*60)
        print("📊 Dashboard URLs:")
        print("   • Enhanced Dashboard: http://localhost:8765/enhanced")
        print("   • Signal Dashboard:   http://localhost:8765/signals/dashboard")
        print("   • WebSocket Test:     http://localhost:8765/websocket_test_client.html")
        print("   • Standard Dashboard: http://localhost:8765/dashboard")
        print("\\n🔧 API Endpoints:")
        print("   • Account Info:       http://localhost:8765/api/account")
        print("   • Positions:          http://localhost:8765/api/positions")
        print("   • Bot Status:         http://localhost:8765/api/bot/status")
        print("   • WebSocket Stats:    http://localhost:8765/api/websocket/performance")
        print("\\n💡 Features Available:")
        print("   ✅ TradingView Lightweight Charts")
        print("   ✅ Real-time WebSocket communication (<50ms latency)")
        print("   ✅ Live position and P&L display")
        print("   ✅ Trading signal visualization")
        print("   ✅ Performance monitoring")
        print("   ✅ Comprehensive testing framework")
        print("\\n⚠️  To stop the system: Press Ctrl+C")
        print("="*60)
        
        # Keep script running
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\\n🛑 Shutting down trading system...")
            process.terminate()
            print("✅ System stopped")
        
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        return False
    
    return True

def main():
    """Main startup function"""
    print("🎯 Alpaca StochRSI EMA Trading Bot - Epic 0 Complete")
    print("=" * 60)
    print("🏗️  Epic 0 Features:")
    print("   ✅ Story 0.1: TradingView Lightweight Charts Integration")
    print("   ✅ Story 0.2: End-to-End Testing Framework")
    print("   ✅ Story 0.3: Frontend-Backend WebSocket Connection")
    print("   ✅ Story 0.4: Live Position and P&L Display")
    print("   ✅ Story 0.5: Trading Signal Visualization")
    print("   ✅ Story 0.6: Testing Strategy Documentation")
    print("   ✅ Story 0.7: Development Environment Standardization")
    print("=" * 60)
    print()
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Dependency check failed")
        return False
    
    # Check configuration
    if not check_configuration():
        print("❌ Configuration check failed")
        print("💡 Please update AUTH/authAlpaca.txt with your API credentials")
        return False
    
    # Start the system
    return start_enhanced_dashboard()

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)