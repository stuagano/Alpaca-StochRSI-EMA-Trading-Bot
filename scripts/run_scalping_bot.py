#!/usr/bin/env python3
"""
Run the crypto scalping bot with comprehensive error handling and trade logging
"""

import sys
import os
import argparse
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.crypto_scalping_bot import AlpacaScalpingBot

def main():
    """Main function to run the scalping bot"""
    print("""
╔═══════════════════════════════════════════════╗
║     ALPACA CRYPTO SCALPING BOT v2.0          ║
║     High-Frequency Trading with Logging      ║
╚═══════════════════════════════════════════════╝
    """)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Alpaca Crypto Scalping Bot')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Run in dry mode (no real trades)')
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable verbose logging')
    parser.add_argument('--symbols', nargs='+', default=['BTCUSD', 'ETHUSD'],
                       help='Symbols to trade (e.g., BTCUSD ETHUSD)')
    parser.add_argument('--config', type=str, 
                       help='Path to config file')
    
    args = parser.parse_args()
    
    # Set environment variables for API credentials
    # The bot will load from AUTH/authAlpaca.txt automatically
    
    try:
        # Create and configure bot
        bot = AlpacaScalpingBot(config_path=args.config)
        
        # Override settings from command line
        if args.dry_run:
            bot.dry_run = True
            print("🏃 Running in DRY RUN mode - no real trades will be executed")
        
        if args.verbose:
            bot.verbose = True
            import logging
            logging.getLogger().setLevel(logging.DEBUG)
        
        if args.symbols:
            bot.config['symbols'] = args.symbols
            print(f"📊 Trading symbols: {args.symbols}")
        
        # Run the bot
        print("\n🚀 Starting scalping bot...")
        print("Press Ctrl+C to stop\n")
        
        bot.run()
        
    except KeyboardInterrupt:
        print("\n⛔ Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()