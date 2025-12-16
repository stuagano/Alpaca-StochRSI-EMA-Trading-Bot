#!/usr/bin/env python3
"""
Quick start script for the Crypto Trading Dashboard
"""

import os
import sys
from pathlib import Path

def main():
    print("🚀 Starting Crypto Trading Dashboard...")
    print("=" * 60)

    # Add current directory to Python path
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))

    try:
        # Import and start the dashboard
        from app import CryptoTradingDashboard

        print("✅ Starting simplified crypto-only dashboard")
        print("🎯 Focused on scalping and short-term trading")
        print("📊 Real-time crypto position monitoring")
        print("")

        # Create and run the dashboard
        dashboard = CryptoTradingDashboard()
        dashboard.run(host='0.0.0.0', port=5001, debug=False)

    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you have installed the requirements:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()