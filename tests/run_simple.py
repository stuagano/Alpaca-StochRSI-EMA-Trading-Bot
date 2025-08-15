#!/usr/bin/env python3
"""Simple bot runner with output capture."""

import sys
import os
import threading
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_bot():
    """Run the bot and capture output."""
    print(f"🚀 Starting Alpaca Trading Bot at {datetime.now()}")
    print("=" * 60)
    
    try:
        # Import and run the main module
        import main
        print("✅ Bot imported successfully")
        
        # If main has a main() function, call it
        if hasattr(main, 'main'):
            print("📊 Running main() function...")
            main.main()
        else:
            print("📊 Main module loaded (running in background)")
            
    except Exception as e:
        print(f"❌ Error running bot: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)
    print(f"🏁 Bot execution completed at {datetime.now()}")

def timeout_handler():
    """Exit after timeout."""
    time.sleep(10)  # Run for 10 seconds
    print("\n⏱️  Timeout reached - stopping bot")
    os._exit(0)

if __name__ == "__main__":
    # Start timeout thread
    timer = threading.Thread(target=timeout_handler, daemon=True)
    timer.start()
    
    # Run the bot
    run_bot()