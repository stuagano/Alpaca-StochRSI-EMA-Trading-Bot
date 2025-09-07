#!/usr/bin/env python3
"""
Alpaca Crypto Scalping Bot with Comprehensive Error Handling and Trade Logging
Author: Trading Bot System
Version: 2.0.0
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.common.exceptions import APIError
import asyncio
from collections import deque
import signal
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class TradeAction(Enum):
    """Trade action types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderStatusType(Enum):
    """Order status types"""
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class TradeLog:
    """Trade log entry structure"""
    timestamp: str
    action: str
    symbol: str
    quantity: float
    price: float
    status: str
    error_notes: str = ""
    order_id: str = ""
    pnl: float = 0.0
    
    def to_console_string(self) -> str:
        """Format for console output"""
        status_emoji = {
            "filled": "✅",
            "partially_filled": "⚠️",
            "failed": "❌",
            "pending": "⏳",
            "cancelled": "🚫"
        }.get(self.status, "❓")
        
        action_color = "\033[92m" if self.action == "BUY" else "\033[91m"
        reset_color = "\033[0m"
        
        return (
            f"{status_emoji} {self.timestamp} | "
            f"{action_color}{self.action:4s}{reset_color} | "
            f"{self.symbol:10s} | "
            f"Qty: {self.quantity:8.4f} | "
            f"Price: ${self.price:10.2f} | "
            f"Status: {self.status:15s} | "
            f"P&L: ${self.pnl:+8.2f} | "
            f"{self.error_notes}"
        )


class AlpacaScalpingBot:
    """
    High-frequency crypto scalping bot with robust error handling
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the scalping bot"""
        self.config = self._load_config(config_path)
        self.dry_run = self.config.get('dry_run', False)
        self.verbose = self.config.get('verbose', False)
        
        # Initialize API clients
        self.trading_client = None
        self.data_client = None
        self._initialize_alpaca()
        
        # Trading state
        self.trade_log: List[TradeLog] = []
        self.positions: Dict[str, Dict] = {}
        self.pending_orders: Dict[str, Any] = {}
        self.indicators_cache: Dict[str, Dict] = {}
        
        # Performance tracking
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'max_drawdown': 0.0,
            'start_balance': 0.0,
            'current_balance': 0.0
        }
        
        # Error handling
        self.error_count = 0
        self.max_errors = 10
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60
        
        # Rate limiting
        self.rate_limiter = self._create_rate_limiter()
        
        # Graceful shutdown
        self.running = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"🚀 Alpaca Scalping Bot initialized {'(DRY RUN MODE)' if self.dry_run else ''}")

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load configuration from file or use defaults"""
        default_config = {
            'symbols': ['BTCUSD', 'ETHUSD'],
            'timeframe': '1Min',
            'position_size': 0.001,  # Small position for scalping
            'max_positions': 3,
            'stop_loss_pct': 0.002,  # 0.2%
            'take_profit_pct': 0.003,  # 0.3%
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'ma_fast': 9,
            'ma_slow': 21,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'min_volume': 100000,
            'dry_run': False,
            'verbose': False
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    default_config.update(loaded_config)
                    logger.info(f"📋 Configuration loaded from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}, using defaults")
        
        return default_config

    def _initialize_alpaca(self):
        """Initialize Alpaca API clients with error handling"""
        try:
            # Get API credentials from environment
            api_key = os.getenv('ALPACA_API_KEY')
            secret_key = os.getenv('ALPACA_SECRET_KEY')
            
            if not api_key or not secret_key:
                # Try loading from AUTH directory
                auth_file = 'AUTH/authAlpaca.txt'
                if os.path.exists(auth_file):
                    with open(auth_file, 'r') as f:
                        lines = f.readlines()
                        api_key = lines[0].strip() if len(lines) > 0 else None
                        secret_key = lines[1].strip() if len(lines) > 1 else None
            
            if not api_key or not secret_key:
                raise ValueError("API credentials not found in environment or AUTH file")
            
            # Determine if paper trading
            paper = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'
            
            # Initialize clients
            self.trading_client = TradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=paper
            )
            
            self.data_client = CryptoHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key
            )
            
            # Get account info
            account = self.trading_client.get_account()
            self.stats['start_balance'] = float(account.cash)
            self.stats['current_balance'] = float(account.cash)
            
            logger.info(f"✅ Connected to Alpaca {'Paper' if paper else 'Live'} Trading")
            logger.info(f"💰 Account Balance: ${float(account.cash):,.2f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Alpaca: {e}")
            raise

    def _create_rate_limiter(self) -> deque:
        """Create a rate limiter to avoid API limits"""
        return deque(maxlen=200)  # Alpaca allows 200 requests per minute

    def _check_rate_limit(self) -> bool:
        """Check if we can make an API call"""
        now = time.time()
        # Remove timestamps older than 60 seconds
        while self.rate_limiter and self.rate_limiter[0] < now - 60:
            self.rate_limiter.popleft()
        
        if len(self.rate_limiter) >= 195:  # Leave some buffer
            return False
        
        self.rate_limiter.append(now)
        return True

    def _wait_for_rate_limit(self):
        """Wait if rate limited"""
        while not self._check_rate_limit():
            logger.warning("⏳ Rate limit reached, waiting 1 second...")
            time.sleep(1)

    def calculate_indicators(self, symbol: str, bars: pd.DataFrame) -> Dict:
        """Calculate technical indicators for scalping"""
        try:
            if len(bars) < max(self.config['ma_slow'], self.config['macd_slow']):
                return {}
            
            indicators = {}
            
            # Price and volume
            close_prices = bars['close'].values
            volumes = bars['volume'].values
            
            # Moving Averages
            indicators['ma_fast'] = np.mean(close_prices[-self.config['ma_fast']:])
            indicators['ma_slow'] = np.mean(close_prices[-self.config['ma_slow']:])
            
            # RSI
            indicators['rsi'] = self._calculate_rsi(close_prices, self.config['rsi_period'])
            
            # MACD
            macd, signal, histogram = self._calculate_macd(
                close_prices,
                self.config['macd_fast'],
                self.config['macd_slow'],
                self.config['macd_signal']
            )
            indicators['macd'] = macd
            indicators['macd_signal'] = signal
            indicators['macd_histogram'] = histogram
            
            # Volume
            indicators['volume'] = volumes[-1]
            indicators['volume_avg'] = np.mean(volumes[-20:])
            
            # Price action
            indicators['current_price'] = close_prices[-1]
            indicators['price_change'] = (close_prices[-1] - close_prices[-2]) / close_prices[-2]
            
            # Volatility
            indicators['volatility'] = np.std(close_prices[-20:]) / np.mean(close_prices[-20:])
            
            self.indicators_cache[symbol] = indicators
            
            if self.verbose:
                logger.debug(f"📊 {symbol} Indicators: RSI={indicators['rsi']:.2f}, "
                           f"MACD={indicators['macd']:.4f}, Price=${indicators['current_price']:.2f}")
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            return {}

    def _calculate_rsi(self, prices: np.ndarray, period: int) -> float:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        deltas = np.diff(prices[-period-1:])
        gains = deltas[deltas > 0]
        losses = -deltas[deltas < 0]
        
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    def _calculate_macd(self, prices: np.ndarray, fast: int, slow: int, signal: int) -> Tuple[float, float, float]:
        """Calculate MACD indicator"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
        
        # Simple moving averages for demonstration (use EMA in production)
        ema_fast = np.mean(prices[-fast:])
        ema_slow = np.mean(prices[-slow:])
        
        macd_line = ema_fast - ema_slow
        
        # For signal line, we need historical MACD values
        # Simplified version here
        signal_line = macd_line * 0.9  # Simplified
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram

    def generate_signal(self, symbol: str, indicators: Dict) -> TradeAction:
        """Generate trading signal based on scalping strategy"""
        if not indicators:
            return TradeAction.HOLD
        
        try:
            rsi = indicators.get('rsi', 50)
            ma_fast = indicators.get('ma_fast', 0)
            ma_slow = indicators.get('ma_slow', 0)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            volume = indicators.get('volume', 0)
            volume_avg = indicators.get('volume_avg', 1)
            current_price = indicators.get('current_price', 0)
            
            # Check if we have a position
            has_position = symbol in self.positions and self.positions[symbol].get('qty', 0) > 0
            
            # Volume filter
            if volume < self.config['min_volume'] or volume < volume_avg * 0.5:
                return TradeAction.HOLD
            
            # Buy signals (multiple conditions for confirmation)
            buy_signals = 0
            
            # RSI oversold
            if rsi < self.config['rsi_oversold']:
                buy_signals += 1
            
            # MA crossover
            if ma_fast > ma_slow and current_price > ma_fast:
                buy_signals += 1
            
            # MACD bullish crossover
            if macd > macd_signal and macd > 0:
                buy_signals += 1
            
            # Sell signals
            sell_signals = 0
            
            # RSI overbought
            if rsi > self.config['rsi_overbought']:
                sell_signals += 1
            
            # MA crossunder
            if ma_fast < ma_slow and current_price < ma_fast:
                sell_signals += 1
            
            # MACD bearish crossover
            if macd < macd_signal and macd < 0:
                sell_signals += 1
            
            # Decision logic
            if not has_position and buy_signals >= 2:
                return TradeAction.BUY
            elif has_position and sell_signals >= 2:
                return TradeAction.SELL
            elif has_position:
                # Check stop loss and take profit
                position = self.positions[symbol]
                entry_price = position.get('avg_entry_price', current_price)
                pnl_pct = (current_price - entry_price) / entry_price
                
                if pnl_pct <= -self.config['stop_loss_pct']:
                    logger.warning(f"🛑 Stop loss triggered for {symbol}")
                    return TradeAction.SELL
                elif pnl_pct >= self.config['take_profit_pct']:
                    logger.info(f"🎯 Take profit triggered for {symbol}")
                    return TradeAction.SELL
            
            return TradeAction.HOLD
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return TradeAction.HOLD

    def execute_trade(self, signal: TradeAction, symbol: str) -> Optional[TradeLog]:
        """Execute trade with comprehensive error handling"""
        if signal == TradeAction.HOLD:
            return None
        
        timestamp = datetime.now().isoformat()
        trade_log = TradeLog(
            timestamp=timestamp,
            action=signal.value,
            symbol=symbol,
            quantity=0,
            price=0,
            status=OrderStatusType.PENDING.value
        )
        
        try:
            # Rate limit check
            self._wait_for_rate_limit()
            
            # Get current price
            indicators = self.indicators_cache.get(symbol, {})
            current_price = indicators.get('current_price', 0)
            
            if current_price <= 0:
                raise ValueError(f"Invalid price for {symbol}: {current_price}")
            
            # Calculate quantity
            if signal == TradeAction.BUY:
                # Check max positions
                if len(self.positions) >= self.config['max_positions']:
                    trade_log.status = OrderStatusType.CANCELLED.value
                    trade_log.error_notes = "Max positions reached"
                    return trade_log
                
                # Calculate position size
                account = self.trading_client.get_account()
                available_cash = float(account.cash)
                position_value = available_cash * self.config['position_size']
                quantity = position_value / current_price
                
            else:  # SELL
                # Get position quantity
                position = self.positions.get(symbol)
                if not position:
                    trade_log.status = OrderStatusType.FAILED.value
                    trade_log.error_notes = "No position to sell"
                    return trade_log
                quantity = position.get('qty', 0)
            
            trade_log.quantity = quantity
            trade_log.price = current_price
            
            # Dry run mode
            if self.dry_run:
                trade_log.status = OrderStatusType.FILLED.value
                trade_log.error_notes = "(DRY RUN)"
                self._update_positions_dry_run(signal, symbol, quantity, current_price)
                return trade_log
            
            # Execute real trade
            order_data = MarketOrderRequest(
                symbol=symbol.replace('/', ''),  # Remove slash for Alpaca
                qty=quantity,
                side=OrderSide.BUY if signal == TradeAction.BUY else OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            
            order = self.trading_client.submit_order(order_data)
            trade_log.order_id = order.id
            
            # Wait for order to fill (with timeout)
            max_wait = 10  # seconds
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                order_status = self.trading_client.get_order_by_id(order.id)
                
                if order_status.status == OrderStatus.FILLED:
                    trade_log.status = OrderStatusType.FILLED.value
                    trade_log.price = float(order_status.filled_avg_price or current_price)
                    
                    # Update positions
                    self._update_positions(order_status)
                    
                    # Calculate P&L for sells
                    if signal == TradeAction.SELL:
                        position = self.positions.get(symbol, {})
                        entry_price = position.get('avg_entry_price', current_price)
                        trade_log.pnl = (trade_log.price - entry_price) * quantity
                        self.stats['total_pnl'] += trade_log.pnl
                    
                    break
                    
                elif order_status.status in [OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                    trade_log.status = OrderStatusType.FAILED.value
                    trade_log.error_notes = f"Order {order_status.status}"
                    break
                    
                time.sleep(0.5)
            
            if trade_log.status == OrderStatusType.PENDING.value:
                trade_log.status = OrderStatusType.FAILED.value
                trade_log.error_notes = "Order timeout"
                
                # Try to cancel the order
                try:
                    self.trading_client.cancel_order_by_id(order.id)
                except:
                    pass
            
            # Update statistics
            if trade_log.status == OrderStatusType.FILLED.value:
                self.stats['total_trades'] += 1
                if trade_log.pnl > 0:
                    self.stats['winning_trades'] += 1
                elif trade_log.pnl < 0:
                    self.stats['losing_trades'] += 1
            
            return trade_log
            
        except APIError as e:
            # Handle specific API errors
            if hasattr(e, 'code'):
                if e.code == 429:
                    trade_log.error_notes = "API rate limit exceeded"
                    logger.error("🚫 Rate limit hit, backing off...")
                    time.sleep(5)
                elif e.code == 403:
                    trade_log.error_notes = "Insufficient funds"
                elif e.code == 400:
                    trade_log.error_notes = f"Invalid request: {str(e)}"
                else:
                    trade_log.error_notes = f"API error {e.code}: {str(e)}"
            else:
                trade_log.error_notes = f"API error: {str(e)}"
            
            trade_log.status = OrderStatusType.FAILED.value
            logger.error(f"❌ Trade execution failed: {trade_log.error_notes}")
            
            self.error_count += 1
            if self.error_count >= self.max_errors:
                logger.critical("Too many errors, shutting down")
                self.running = False
            
            return trade_log
            
        except Exception as e:
            trade_log.status = OrderStatusType.FAILED.value
            trade_log.error_notes = f"Unexpected error: {str(e)}"
            logger.error(f"❌ Unexpected error in trade execution: {e}")
            
            self.error_count += 1
            return trade_log

    def _update_positions(self, order):
        """Update positions based on filled order"""
        symbol = order.symbol
        
        if order.side == OrderSide.BUY:
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'qty': 0,
                    'avg_entry_price': 0
                }
            
            position = self.positions[symbol]
            total_value = (position['qty'] * position['avg_entry_price']) + \
                         (float(order.filled_qty) * float(order.filled_avg_price))
            total_qty = position['qty'] + float(order.filled_qty)
            
            position['qty'] = total_qty
            position['avg_entry_price'] = total_value / total_qty if total_qty > 0 else 0
            
        else:  # SELL
            if symbol in self.positions:
                position = self.positions[symbol]
                position['qty'] -= float(order.filled_qty)
                
                if position['qty'] <= 0:
                    del self.positions[symbol]

    def _update_positions_dry_run(self, signal: TradeAction, symbol: str, quantity: float, price: float):
        """Update positions in dry run mode"""
        if signal == TradeAction.BUY:
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'qty': 0,
                    'avg_entry_price': 0
                }
            
            position = self.positions[symbol]
            total_value = (position['qty'] * position['avg_entry_price']) + (quantity * price)
            total_qty = position['qty'] + quantity
            
            position['qty'] = total_qty
            position['avg_entry_price'] = total_value / total_qty if total_qty > 0 else 0
            
        else:  # SELL
            if symbol in self.positions:
                self.positions[symbol]['qty'] -= quantity
                if self.positions[symbol]['qty'] <= 0:
                    del self.positions[symbol]

    def log_trade(self, trade_log: TradeLog):
        """Log trade to console and file"""
        if trade_log:
            self.trade_log.append(trade_log)
            
            # Console output
            print(trade_log.to_console_string())
            
            # File logging
            log_file = 'logs/trade_timeline.log'
            os.makedirs('logs', exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(asdict(trade_log)) + '\n')

    def print_summary(self):
        """Print trading summary"""
        print("\n" + "="*80)
        print("📊 TRADING SUMMARY")
        print("="*80)
        
        # Calculate metrics
        win_rate = (self.stats['winning_trades'] / self.stats['total_trades'] * 100) \
                  if self.stats['total_trades'] > 0 else 0
        
        print(f"Total Trades: {self.stats['total_trades']}")
        print(f"Winning Trades: {self.stats['winning_trades']}")
        print(f"Losing Trades: {self.stats['losing_trades']}")
        print(f"Win Rate: {win_rate:.2f}%")
        print(f"Total P&L: ${self.stats['total_pnl']:+,.2f}")
        print(f"Starting Balance: ${self.stats['start_balance']:,.2f}")
        print(f"Current Balance: ${self.stats['current_balance']:,.2f}")
        
        print("\n📝 RECENT TRADES:")
        for trade in self.trade_log[-10:]:  # Last 10 trades
            print(trade.to_console_string())
        
        print("="*80)

    def fetch_latest_bars(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch latest price bars with error handling"""
        try:
            self._wait_for_rate_limit()
            
            # Convert symbol format
            alpaca_symbol = symbol.replace('/', '')
            
            # Fetch bars
            request_params = CryptoBarsRequest(
                symbol_or_symbols=alpaca_symbol,
                timeframe=TimeFrame.Minute,
                start=datetime.now() - timedelta(minutes=100)
            )
            
            bars = self.data_client.get_crypto_bars(request_params)
            
            if alpaca_symbol in bars:
                df = bars[alpaca_symbol].df
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            return None

    async def run_async(self):
        """Async main loop for better performance"""
        self.running = True
        logger.info("🏃 Starting scalping bot main loop...")
        
        while self.running:
            try:
                for symbol in self.config['symbols']:
                    if not self.running:
                        break
                    
                    # Fetch latest data
                    bars = self.fetch_latest_bars(symbol)
                    if bars is None or len(bars) < 30:
                        continue
                    
                    # Calculate indicators
                    indicators = self.calculate_indicators(symbol, bars)
                    if not indicators:
                        continue
                    
                    # Generate signal
                    signal = self.generate_signal(symbol, indicators)
                    
                    # Execute trade if needed
                    if signal != TradeAction.HOLD:
                        trade_log = self.execute_trade(signal, symbol)
                        if trade_log:
                            self.log_trade(trade_log)
                    
                    # Small delay between symbols
                    await asyncio.sleep(0.5)
                
                # Update account balance
                if not self.dry_run:
                    try:
                        account = self.trading_client.get_account()
                        self.stats['current_balance'] = float(account.cash)
                    except:
                        pass
                
                # Sleep before next iteration
                await asyncio.sleep(5)  # 5 seconds between full cycles
                
            except KeyboardInterrupt:
                logger.info("⛔ Received interrupt signal")
                break
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.error_count += 1
                
                if self.error_count >= self.max_errors:
                    logger.critical("Too many errors, shutting down")
                    break
                
                # Exponential backoff for reconnection
                await asyncio.sleep(min(self.reconnect_delay * 2, self.max_reconnect_delay))

    def run(self):
        """Main entry point"""
        try:
            # Run the async loop
            asyncio.run(self.run_async())
            
        except KeyboardInterrupt:
            logger.info("⛔ Gracefully shutting down...")
            
        finally:
            self.print_summary()
            logger.info("👋 Scalping bot terminated")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False


def main():
    """Main function to run the scalping bot"""
    print("""
╔═══════════════════════════════════════════════╗
║     ALPACA CRYPTO SCALPING BOT v2.0          ║
║     High-Frequency Trading with AI           ║
╚═══════════════════════════════════════════════╝
    """)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Alpaca Crypto Scalping Bot')
    parser.add_argument('--config', type=str, help='Path to config file')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry mode (no real trades)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--symbols', nargs='+', help='Symbols to trade (e.g., BTCUSD ETHUSD)')
    
    args = parser.parse_args()
    
    # Create config path
    config_path = args.config or 'config/scalping_config.yaml'
    
    # Initialize and run bot
    bot = AlpacaScalpingBot(config_path)
    
    # Override settings from command line
    if args.dry_run:
        bot.dry_run = True
        logger.info("🏃 Running in DRY RUN mode - no real trades will be executed")
    
    if args.verbose:
        bot.verbose = True
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.symbols:
        bot.config['symbols'] = args.symbols
        logger.info(f"Trading symbols: {args.symbols}")
    
    # Run the bot
    bot.run()


if __name__ == "__main__":
    main()