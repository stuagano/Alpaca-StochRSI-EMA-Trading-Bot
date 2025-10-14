#!/usr/bin/env python3
"""
Simplified Crypto Trading Bot Web Interface
Focused on crypto trading only with clean, simple dashboard
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import alpaca_trade_api as tradeapi
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingIndicators:
    """Calculate trading indicators for crypto"""

    @staticmethod
    def calculate_rsi(prices, period=14):
        """Calculate RSI"""
        if len(prices) < period:
            return 50

        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period

        if down == 0:
            return 100

        rs = up / down
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_stoch_rsi(prices, period=14):
        """Calculate Stochastic RSI"""
        if len(prices) < period:
            return 50

        rsi = TradingIndicators.calculate_rsi(prices, period)
        return rsi  # Simplified

    @staticmethod
    def calculate_ema(prices, period):
        """Calculate EMA"""
        if len(prices) < period:
            return prices[-1] if prices else 0

        ema = [sum(prices[:period]) / period]
        multiplier = 2 / (period + 1)

        for price in prices[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])

        return ema[-1] if ema else prices[-1]

class CryptoTradingDashboard:
    """Simplified crypto trading dashboard"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.load_config()
        self.api = self.init_alpaca()

        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self.setup_routes()

        # Trading state
        self.account = None
        self.positions = {}
        self.signals = {}
        self.recent_trades = []
        self.last_update = datetime.now()

    def load_config(self):
        """Load Alpaca configuration"""
        auth_path = self.project_root / "AUTH" / "authAlpaca.txt"

        try:
            with open(auth_path, 'r') as f:
                self.auth = json.load(f)
        except FileNotFoundError:
            logger.error(f"Auth file not found: {auth_path}")
            self.auth = {
                "APCA-API-KEY-ID": "your_key",
                "APCA-API-SECRET-KEY": "your_secret",
                "BASE-URL": "https://paper-api.alpaca.markets"
            }

        # Crypto trading configuration
        self.crypto_symbols = [
            'BTCUSD', 'ETHUSD', 'LTCUSD', 'AVAXUSD',
            'AAVEUSD', 'DOGEUSD', 'SOLUSD', 'ADAUSD'
        ]
        self.position_size = 1000  # $1000 per position
        self.stop_loss_pct = 0.03  # 3% stop loss
        self.take_profit_pct = 0.05  # 5% take profit

    def init_alpaca(self):
        """Initialize Alpaca API"""
        try:
            api = tradeapi.REST(
                self.auth['APCA-API-KEY-ID'],
                self.auth['APCA-API-SECRET-KEY'],
                self.auth.get('BASE-URL', 'https://paper-api.alpaca.markets'),
                api_version='v2'
            )
            logger.info("Connected to Alpaca API")
            return api
        except Exception as e:
            logger.error(f"Failed to connect to Alpaca API: {e}")
            return None

    def setup_routes(self):
        """Setup Flask routes for crypto dashboard"""

        @self.app.route('/')
        def index():
            """Serve the main dashboard"""
            return send_from_directory('frontend', 'index.html')

        @self.app.route('/frontend/<path:filename>')
        def frontend_files(filename):
            """Serve frontend static files"""
            return send_from_directory('frontend', filename)

        @self.app.route('/api/status')
        def api_status():
            """Get crypto trading status"""
            self.update_data()

            return jsonify({
                'status': 'running',
                'last_update': self.last_update.isoformat(),
                'crypto_mode': True,
                'symbols_tracked': len(self.crypto_symbols),
                'market_status': 'OPEN',  # Crypto is 24/7
                'account': self.get_account_data(),
                'positions_count': len(self.positions)
            })

        @self.app.route('/api/account')
        def api_account():
            """Get account information"""
            self.update_account()
            return jsonify(self.get_account_data())

        @self.app.route('/api/positions')
        def api_positions():
            """Get current crypto positions"""
            self.update_positions()

            positions_data = []
            for symbol, pos in self.positions.items():
                positions_data.append({
                    'symbol': symbol,
                    'qty': float(pos.qty),
                    'avg_price': float(pos.avg_entry_price),
                    'current_price': self.get_current_price(symbol),
                    'unrealized_pl': float(pos.unrealized_pl) if hasattr(pos, 'unrealized_pl') else 0,
                    'unrealized_plpc': float(pos.unrealized_plpc) if hasattr(pos, 'unrealized_plpc') else 0,
                    'market_value': float(pos.market_value) if hasattr(pos, 'market_value') else 0
                })

            return jsonify(positions_data)

        @self.app.route('/api/signals')
        def api_signals():
            """Get current crypto trading signals"""
            self.calculate_signals()

            signals_data = []
            for symbol, signal in self.signals.items():
                signals_data.append({
                    'symbol': symbol,
                    'action': signal.get('action', 'HOLD'),
                    'rsi': signal.get('rsi', 50),
                    'stoch_rsi': signal.get('stoch_rsi', 50),
                    'price': signal.get('price', 0),
                    'strength': signal.get('strength', 'Medium'),
                    'timestamp': signal.get('timestamp', datetime.now().isoformat())
                })

            return jsonify(signals_data)

        @self.app.route('/api/trades')
        def api_trades():
            """Get recent crypto trades"""
            return jsonify(self.recent_trades[-20:])  # Last 20 trades

        @self.app.route('/api/crypto-symbols')
        def api_crypto_symbols():
            """Get list of tracked crypto symbols"""
            return jsonify({
                'symbols': self.crypto_symbols,
                'count': len(self.crypto_symbols),
                'market_type': 'crypto'
            })

    def update_data(self):
        """Update all trading data"""
        self.update_account()
        self.update_positions()
        self.calculate_signals()
        self.last_update = datetime.now()

    def update_account(self):
        """Update account information"""
        if not self.api:
            return

        try:
            self.account = self.api.get_account()
            logger.debug("Account data updated")
        except Exception as e:
            logger.error(f"Error updating account: {e}")

    def update_positions(self):
        """Update crypto positions"""
        if not self.api:
            return

        try:
            positions = self.api.list_positions()
            # Filter for crypto positions only
            self.positions = {
                pos.symbol: pos for pos in positions
                if pos.symbol in self.crypto_symbols
            }
            logger.debug(f"Updated {len(self.positions)} crypto positions")
        except Exception as e:
            logger.error(f"Error updating positions: {e}")

    def get_current_price(self, symbol):
        """Get current price for a crypto symbol"""
        if not self.api:
            return 0

        try:
            latest_quote = self.api.get_latest_quote(symbol)
            return float(latest_quote.bid_price + latest_quote.ask_price) / 2
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return 0

    def calculate_signals(self):
        """Calculate trading signals for crypto symbols"""
        if not self.api:
            return

        for symbol in self.crypto_symbols:
            try:
                # Get recent bars
                bars = self.api.get_bars(
                    symbol,
                    '5Min',  # 5-minute bars for crypto
                    limit=50
                ).df

                if len(bars) < 20:
                    continue

                prices = bars['close'].values

                # Calculate indicators
                rsi = TradingIndicators.calculate_rsi(prices)
                stoch_rsi = TradingIndicators.calculate_stoch_rsi(prices)
                ema_short = TradingIndicators.calculate_ema(prices, 9)
                ema_long = TradingIndicators.calculate_ema(prices, 21)

                # Generate signal
                action = 'HOLD'
                strength = 'Medium'

                if rsi < 30 and ema_short > ema_long:
                    action = 'BUY'
                    strength = 'Strong' if rsi < 25 else 'Medium'
                elif rsi > 70 and ema_short < ema_long:
                    action = 'SELL'
                    strength = 'Strong' if rsi > 75 else 'Medium'

                self.signals[symbol] = {
                    'action': action,
                    'rsi': round(rsi, 2),
                    'stoch_rsi': round(stoch_rsi, 2),
                    'price': round(prices[-1], 4),
                    'strength': strength,
                    'ema_short': round(ema_short, 4),
                    'ema_long': round(ema_long, 4),
                    'timestamp': datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error calculating signals for {symbol}: {e}")

    def get_account_data(self):
        """Get formatted account data"""
        if not self.account:
            return {
                'status': 'DISCONNECTED',
                'buying_power': 0,
                'portfolio_value': 0,
                'cash': 0,
                'equity': 0
            }

        return {
            'status': self.account.status,
            'buying_power': float(self.account.buying_power),
            'portfolio_value': float(self.account.portfolio_value),
            'cash': float(self.account.cash),
            'equity': float(self.account.equity)
        }

    def run(self, host='localhost', port=5001, debug=False):
        """Run the Flask app"""
        logger.info("=" * 60)
        logger.info("CRYPTO TRADING DASHBOARD STARTING")
        logger.info("=" * 60)
        logger.info(f"Dashboard URL: http://{host}:{port}")
        logger.info(f"Tracking {len(self.crypto_symbols)} crypto symbols")
        logger.info("=" * 60)

        self.app.run(host=host, port=port, debug=debug)

def create_app():
    """Create Flask app instance"""
    dashboard = CryptoTradingDashboard()
    return dashboard.app

def main():
    """Main entry point"""
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5002
    dashboard = CryptoTradingDashboard()
    dashboard.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()