#!/usr/bin/env python3
"""
Unified Alpaca Trading Bot Launcher
Single entry point for all bot components
"""

import subprocess
import sys
import os
import json
import argparse
from pathlib import Path
import time

class TradingBotLauncher:
    def __init__(self):
        self.required_files = [
            'AUTH/authAlpaca.txt',
            'AUTH/ConfigFile.txt', 
            'AUTH/Tickers.txt'
        ]
        self.required_dirs = ['ORDERS', 'AUTH']

    def kill_existing_processes(self):
        """Kill any existing bot or dashboard processes"""
        import psutil
        import signal
        
        processes_killed = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if any(script in cmdline for script in ['main.py', 'flask_app.py', 'app.py', 'streamlit']):
                    if proc.pid != os.getpid():  # Don't kill ourselves
                        print(f"🔪 Killing existing process: {proc.info['name']} (PID: {proc.info['pid']})")
                        proc.terminate()
                        processes_killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if processes_killed > 0:
            print(f"✅ Killed {processes_killed} existing processes")
            time.sleep(2)  # Wait for processes to clean up
        else:
            print("ℹ️  No existing processes found")
        return processes_killed

    def setup_environment(self):
        """Create necessary directories"""
        for directory in self.required_dirs:
            Path(directory).mkdir(exist_ok=True)
            print(f"✅ Directory '{directory}' ready")

    def check_requirements(self):
        """Check if all required files exist"""
        missing_files = []
        for file_path in self.required_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print("❌ Missing required files:")
            for file_path in missing_files:
                print(f"   - {file_path}")
            print("\n📝 Please create these files before running.")
            return False
        return True

    def install_requirements(self):
        """Install required packages"""
        print("📦 Installing requirements...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print("✅ Requirements installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install requirements: {e}")
            return False

    def run_trading_bot(self):
        """Run the core trading bot"""
        print("🤖 Starting Alpaca Trading Bot...")
        try:
            subprocess.run([sys.executable, 'main.py'])
        except KeyboardInterrupt:
            print("\n🛑 Trading bot stopped by user")
        except Exception as e:
            print(f"❌ Error running trading bot: {e}")

    def run_streamlit_dashboard(self):
        """Run Streamlit dashboard - DEPRECATED: Use Flask instead"""
        print("⚠️  Streamlit dashboard is deprecated. Use Flask dashboard instead.")
        print("💡 Run: python run.py flask")
        return

    def run_flask_dashboard(self):
        """Run Flask dashboard with WebSockets"""
        print("🌐 Starting Flask Dashboard with WebSockets...")
        print("🌐 Will be available at: http://localhost:8765")
        try:
            subprocess.run([sys.executable, 'flask_app.py'])
        except KeyboardInterrupt:
            print("\n🛑 Flask dashboard stopped by user")
        except Exception as e:
            print(f"❌ Error running Flask dashboard: {e}")

    def run_bot_with_dashboard(self, dashboard_type='streamlit'):
        """Run bot and dashboard in parallel"""
        print(f"🚀 Starting trading bot with {dashboard_type} dashboard...")
        
        import threading
        
        # Start bot in background thread
        def run_bot():
            self.run_trading_bot()
        
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        # Wait a moment for bot to start
        time.sleep(2)
        
        # Start dashboard in main thread
        if dashboard_type == 'streamlit':
            self.run_streamlit_dashboard()
        else:
            self.run_flask_dashboard()

    def show_status(self):
        """Show current bot status"""
        print("📊 Trading Bot Status")
        print("=" * 50)
        
        # Check if config files exist
        config_status = "✅" if self.check_requirements() else "❌"
        print(f"{config_status} Configuration files")
        
        # Check if bot is running (simplified check)
        print("ℹ️  Use 'run' command to start components")

def main():
    launcher = TradingBotLauncher()
    
    parser = argparse.ArgumentParser(description='Unified Alpaca Trading Bot Launcher')
    parser.add_argument('command', nargs='?', default='help', choices=[
        'bot', 'flask', 'both-flask', 
        'install', 'status', 'kill', 'restart', 'help'
    ], help='Command to run')
    
    args = parser.parse_args()
    
    print("🤖 Alpaca Trading Bot Launcher")
    print("=" * 50)
    
    # Setup environment
    launcher.setup_environment()
    
    if args.command == 'install':
        launcher.install_requirements()
        return
    
    if args.command == 'status':
        launcher.show_status()
        return
    
    if args.command == 'kill':
        launcher.kill_existing_processes()
        return
    
    if args.command == 'restart':
        launcher.kill_existing_processes()
        args.command = 'flask'  # Default to flask only after restart
    
    if args.command == 'help':
        print("\n📚 Available Commands:")
        print("  bot           - Run trading bot only")
        print("  flask         - Run Flask dashboard only")
        print("  both-flask    - Run bot + Flask dashboard")
        print("  install       - Install requirements")
        print("  status        - Show current status")
        print("  kill          - Kill all existing processes")
        print("  restart       - Kill existing + start Flask dashboard (RECOMMENDED)")
        print("  help          - Show this help")
        print("\n💡 Examples:")
        print("  python run.py restart       # RECOMMENDED: Single command to start everything")
        print("  python run.py flask         # Dashboard only")
        print("  python run.py both-flask    # Bot + Dashboard")
        return
    
    # Check requirements before running (except for kill command)
    if args.command not in ['kill'] and not launcher.check_requirements():
        print("\n💡 Fix configuration issues before continuing")
        return
    
    # Kill existing processes for all commands that will start new ones
    if args.command in ['bot', 'flask', 'both-flask', 'restart']:
        launcher.kill_existing_processes()
    
    # Execute commands
    if args.command == 'bot':
        launcher.run_trading_bot()
    elif args.command == 'flask':
        launcher.run_flask_dashboard()
    elif args.command == 'both-flask':
        launcher.run_bot_with_dashboard('flask')

if __name__ == "__main__":
    main()