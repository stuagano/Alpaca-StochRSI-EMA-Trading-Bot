"""
High-Frequency Crypto Day Trading Strategy
Focuses on volatility, quick gains, and rapid position turnover
"""

import numpy as np
import pandas as pd
import asyncio
import websocket
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import logging
from threading import Lock

logger = logging.getLogger(__name__)

@dataclass
class CryptoSignal:
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    confidence: float
    price: float
    volatility: float
    volume_surge: bool
    momentum: float
    target_profit: float
    stop_loss: float
    timestamp: datetime

class CryptoVolatilityScanner:
    """Scans for high volatility crypto pairs suitable for day trading"""
    
    def __init__(self):
        self.high_volume_pairs = [
            'BTC/USD', 'ETH/USD', 'BNB/USD', 'XRP/USD', 'ADA/USD',
            'SOL/USD', 'DOGE/USD', 'DOT/USD', 'MATIC/USD', 'LTC/USD',
            'AVAX/USD', 'LINK/USD', 'UNI/USD', 'ATOM/USD', 'XLM/USD',
            'BCH/USD', 'ALGO/USD', 'VET/USD', 'ICP/USD', 'FIL/USD'
        ]
        
        # Minimum criteria for day trading
        self.min_24h_volume = 10000000  # $10M daily volume
        self.min_volatility = 0.02  # 2% price movement
        self.max_spread = 0.001  # 0.1% bid-ask spread
        
        self.price_data = {}
        self.volatility_data = {}
        self.volume_data = {}
        self.lock = Lock()
        
    def calculate_volatility(self, prices: List[float], window: int = 20) -> float:
        """Calculate price volatility using standard deviation"""
        if len(prices) < window:
            return 0.0
        
        returns = np.diff(np.log(prices[-window:]))
        return np.std(returns) * np.sqrt(1440)  # Annualized for 1-minute data
    
    def detect_volume_surge(self, volumes: List[float], window: int = 10) -> bool:
        """Detect if current volume is significantly higher than average"""
        if len(volumes) < window + 1:
            return False
        
        recent_avg = np.mean(volumes[-window-1:-1])
        current_volume = volumes[-1]
        
        return current_volume > recent_avg * 1.5  # 50% above average
    
    def calculate_momentum(self, prices: List[float], period: int = 14) -> float:
        """Calculate price momentum using RSI-like indicator"""
        if len(prices) < period + 1:
            return 0.5
        
        changes = np.diff(prices[-period-1:])
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, -changes, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 1.0
        
        rs = avg_gain / avg_loss
        momentum = rs / (1 + rs)
        
        return momentum
    
    def scan_for_opportunities(self) -> List[CryptoSignal]:
        """Scan all crypto pairs for day trading opportunities"""
        signals = []
        
        with self.lock:
            for symbol in self.high_volume_pairs:
                try:
                    if symbol not in self.price_data:
                        continue
                    
                    prices = self.price_data[symbol]
                    volumes = self.volume_data.get(symbol, [])
                    
                    if len(prices) < 20:  # Need enough data
                        continue
                    
                    current_price = prices[-1]
                    volatility = self.calculate_volatility(prices)
                    volume_surge = self.detect_volume_surge(volumes)
                    momentum = self.calculate_momentum(prices)
                    
                    # Check if meets day trading criteria
                    if volatility < self.min_volatility:
                        continue
                    
                    # Generate trading signal
                    signal = self._generate_signal(
                        symbol, current_price, volatility, 
                        volume_surge, momentum
                    )
                    
                    if signal:
                        signals.append(signal)
                        
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
        
        # Sort by best opportunities (high volatility + volume surge)
        return sorted(signals, key=lambda s: s.confidence, reverse=True)[:10]
    
    def _generate_signal(self, symbol: str, price: float, volatility: float, 
                        volume_surge: bool, momentum: float) -> Optional[CryptoSignal]:
        """Generate trading signal based on analysis"""
        
        # Scalping thresholds
        high_momentum_threshold = 0.7
        low_momentum_threshold = 0.3
        high_volatility_threshold = 0.05
        
        # Determine action
        action = 'hold'
        confidence = 0.0
        target_profit = 0.005  # Default 0.5% profit target
        stop_loss = 0.003      # Default 0.3% stop loss
        
        # High volatility + momentum signals
        if volatility > high_volatility_threshold:
            target_profit = 0.008  # 0.8% profit for high volatility
            stop_loss = 0.005      # 0.5% stop loss
            
            if momentum > high_momentum_threshold:
                action = 'buy'
                confidence = min(0.9, volatility * 10 + (0.3 if volume_surge else 0))
            elif momentum < low_momentum_threshold:
                action = 'sell'
                confidence = min(0.9, volatility * 10 + (0.3 if volume_surge else 0))
        
        # Medium volatility signals
        elif volatility > self.min_volatility:
            if momentum > 0.8 and volume_surge:
                action = 'buy'
                confidence = 0.7
            elif momentum < 0.2 and volume_surge:
                action = 'sell'
                confidence = 0.7
        
        # Volume surge signals (momentum plays)
        if volume_surge and action == 'hold':
            if momentum > 0.6:
                action = 'buy'
                confidence = 0.6
                target_profit = 0.004  # Quick 0.4% target
                stop_loss = 0.002      # Tight 0.2% stop
            elif momentum < 0.4:
                action = 'sell'
                confidence = 0.6
                target_profit = 0.004
                stop_loss = 0.002
        
        if action != 'hold' and confidence > 0.5:
            return CryptoSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price,
                volatility=volatility,
                volume_surge=volume_surge,
                momentum=momentum,
                target_profit=target_profit,
                stop_loss=stop_loss,
                timestamp=datetime.now()
            )
        
        return None
    
    def update_market_data(self, symbol: str, price: float, volume: float):
        """Update real-time market data"""
        with self.lock:
            if symbol not in self.price_data:
                self.price_data[symbol] = []
                self.volume_data[symbol] = []
            
            self.price_data[symbol].append(price)
            self.volume_data[symbol].append(volume)
            
            # Keep only recent data (1000 data points ≈ 16-17 hours of 1-min data)
            if len(self.price_data[symbol]) > 1000:
                self.price_data[symbol] = self.price_data[symbol][-1000:]
                self.volume_data[symbol] = self.volume_data[symbol][-1000:]

class CryptoDayTradingBot:
    """High-frequency crypto day trading bot"""
    
    def __init__(self, alpaca_client, initial_capital: float = 10000):
        self.alpaca = alpaca_client
        self.scanner = CryptoVolatilityScanner()
        self.initial_capital = initial_capital
        self.max_position_size = initial_capital * 0.05  # 5% per trade
        self.max_concurrent_positions = 10
        self.min_profit_target = 0.003  # 0.3% minimum profit
        
        # Trading metrics
        self.active_positions = {}
        self.daily_trades = 0
        self.daily_profit = 0.0
        self.win_rate = 0.0
        self.total_trades = 0
        self.wins = 0
        
        # Risk management
        self.max_daily_loss = initial_capital * 0.02  # 2% daily loss limit
        self.max_drawdown = initial_capital * 0.05    # 5% maximum drawdown
        
        self.is_running = False
        self.executor = ThreadPoolExecutor(max_workers=5)
        
    async def start_trading(self):
        """Start the day trading bot"""
        logger.info("🚀 Starting Crypto Day Trading Bot")
        self.is_running = True
        
        # Start market data feed
        self.executor.submit(self._start_market_data_feed)
        
        # Main trading loop
        while self.is_running:
            try:
                await self._trading_cycle()
                await asyncio.sleep(1)  # 1-second cycle for high frequency
                
            except Exception as e:
                logger.error(f"Trading cycle error: {e}")
                await asyncio.sleep(5)
    
    async def _trading_cycle(self):
        """Main trading cycle - runs every second"""
        
        # Check for exit signals on existing positions
        await self._check_exit_conditions()
        
        # Look for new entry opportunities every 5 seconds
        if int(time.time()) % 5 == 0:
            await self._find_entry_opportunities()
        
        # Update metrics every minute
        if int(time.time()) % 60 == 0:
            self._update_metrics()
    
    async def _find_entry_opportunities(self):
        """Find new trading opportunities"""
        if len(self.active_positions) >= self.max_concurrent_positions:
            return
        
        if abs(self.daily_profit) > self.max_daily_loss:
            logger.warning("Daily loss limit reached, stopping new trades")
            return
        
        # Get trading signals
        signals = self.scanner.scan_for_opportunities()
        
        for signal in signals[:5]:  # Top 5 opportunities
            if signal.symbol in self.active_positions:
                continue
            
            if signal.confidence > 0.7:  # High confidence trades only
                await self._execute_entry(signal)
    
    async def _execute_entry(self, signal: CryptoSignal):
        """Execute entry trade"""
        try:
            # Calculate position size
            position_value = min(
                self.max_position_size,
                self.initial_capital * signal.confidence * 0.1  # Scale with confidence
            )
            
            quantity = position_value / signal.price
            
            # Place order
            order = await self._place_crypto_order(
                symbol=signal.symbol,
                side=signal.action,
                quantity=quantity,
                order_type='market'
            )
            
            if order:
                # Track position
                self.active_positions[signal.symbol] = {
                    'signal': signal,
                    'entry_price': signal.price,
                    'quantity': quantity,
                    'side': signal.action,
                    'entry_time': datetime.now(),
                    'target_price': signal.price * (1 + signal.target_profit) if signal.action == 'buy' else signal.price * (1 - signal.target_profit),
                    'stop_price': signal.price * (1 - signal.stop_loss) if signal.action == 'buy' else signal.price * (1 + signal.stop_loss),
                    'order_id': order.get('id')
                }
                
                logger.info(f"🎯 Opened {signal.action.upper()} position: {signal.symbol} @ {signal.price:.4f}")
        
        except Exception as e:
            logger.error(f"Failed to execute entry for {signal.symbol}: {e}")
    
    async def _check_exit_conditions(self):
        """Check exit conditions for all active positions"""
        positions_to_close = []
        
        for symbol, position in self.active_positions.items():
            try:
                # Get current price
                current_price = await self._get_current_price(symbol)
                if not current_price:
                    continue
                
                signal = position['signal']
                entry_price = position['entry_price']
                side = position['side']
                
                # Calculate current P&L
                if side == 'buy':
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price
                
                should_exit = False
                exit_reason = ""
                
                # Profit target hit
                if ((side == 'buy' and current_price >= position['target_price']) or 
                    (side == 'sell' and current_price <= position['target_price'])):
                    should_exit = True
                    exit_reason = "PROFIT_TARGET"
                
                # Stop loss hit
                elif ((side == 'buy' and current_price <= position['stop_price']) or 
                      (side == 'sell' and current_price >= position['stop_price'])):
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                
                # Time-based exit (hold for max 30 minutes for scalping)
                elif (datetime.now() - position['entry_time']).seconds > 1800:
                    should_exit = True
                    exit_reason = "TIME_LIMIT"
                
                # Trailing stop for profitable positions
                elif pnl_pct > 0.01:  # 1% profit
                    # Implement trailing stop
                    trail_distance = 0.005  # 0.5% trailing distance
                    if side == 'buy':
                        new_stop = current_price * (1 - trail_distance)
                        if new_stop > position['stop_price']:
                            position['stop_price'] = new_stop
                    else:
                        new_stop = current_price * (1 + trail_distance)
                        if new_stop < position['stop_price']:
                            position['stop_price'] = new_stop
                
                if should_exit:
                    positions_to_close.append((symbol, exit_reason, current_price, pnl_pct))
            
            except Exception as e:
                logger.error(f"Error checking exit for {symbol}: {e}")
        
        # Close positions
        for symbol, reason, price, pnl_pct in positions_to_close:
            await self._execute_exit(symbol, reason, price, pnl_pct)
    
    async def _execute_exit(self, symbol: str, reason: str, price: float, pnl_pct: float):
        """Execute exit trade"""
        try:
            position = self.active_positions[symbol]
            
            # Place closing order
            opposite_side = 'sell' if position['side'] == 'buy' else 'buy'
            
            order = await self._place_crypto_order(
                symbol=symbol,
                side=opposite_side,
                quantity=position['quantity'],
                order_type='market'
            )
            
            if order:
                # Update metrics
                profit = position['quantity'] * position['entry_price'] * pnl_pct
                self.daily_profit += profit
                self.total_trades += 1
                
                if pnl_pct > 0:
                    self.wins += 1
                
                self.win_rate = self.wins / self.total_trades if self.total_trades > 0 else 0
                
                # Remove from active positions
                del self.active_positions[symbol]
                
                logger.info(f"✅ Closed position: {symbol} | Reason: {reason} | P&L: {pnl_pct:.2%} | Profit: ${profit:.2f}")
        
        except Exception as e:
            logger.error(f"Failed to execute exit for {symbol}: {e}")
    
    async def _place_crypto_order(self, symbol: str, side: str, quantity: float, order_type: str = 'market'):
        """Place crypto order via Alpaca API"""
        try:
            # Convert symbol format if needed (BTC/USD -> BTCUSD)
            alpaca_symbol = symbol.replace('/', '')
            
            order_data = {
                'symbol': alpaca_symbol,
                'qty': quantity,
                'side': side,
                'type': order_type,
                'time_in_force': 'ioc'  # Immediate or cancel for crypto
            }
            
            # Use Alpaca crypto API
            order = self.alpaca.submit_order(**order_data)
            return order
            
        except Exception as e:
            logger.error(f"Order placement failed for {symbol}: {e}")
            return None
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            # Get from price data
            with self.scanner.lock:
                if symbol in self.scanner.price_data and self.scanner.price_data[symbol]:
                    return self.scanner.price_data[symbol][-1]
            return None
        except:
            return None
    
    def _start_market_data_feed(self):
        """Start WebSocket feed for market data"""
        # This would connect to crypto exchange WebSocket
        # For now, simulate with random data updates
        import threading
        
        def simulate_data():
            # Initialize with base prices for each symbol
            base_prices = {}
            for symbol in self.scanner.high_volume_pairs:
                if 'BTC' in symbol:
                    base_prices[symbol] = 45000 + np.random.random() * 10000
                elif 'ETH' in symbol:
                    base_prices[symbol] = 2800 + np.random.random() * 500
                elif 'DOGE' in symbol:
                    base_prices[symbol] = 0.08 + np.random.random() * 0.02
                else:
                    base_prices[symbol] = 10 + hash(symbol) % 1000
                
                # Initialize with some historical data for volatility calculation
                for _ in range(50):
                    price_change = (np.random.random() - 0.5) * 0.05  # ±2.5% for history
                    price = base_prices[symbol] * (1 + price_change)
                    volume = np.random.exponential(5000000) + 1000000
                    self.scanner.update_market_data(symbol, price, volume)
            
            while self.is_running:
                try:
                    for symbol in self.scanner.high_volume_pairs:
                        # Create more volatile price movements
                        if np.random.random() < 0.1:  # 10% chance of high volatility event
                            price_change = (np.random.random() - 0.5) * 0.08  # ±4% spike
                            volume_multiplier = 2 + np.random.random() * 3  # 2-5x volume
                        else:
                            price_change = (np.random.random() - 0.5) * 0.02  # Normal ±1%
                            volume_multiplier = 0.8 + np.random.random() * 0.4  # 0.8-1.2x
                        
                        # Update base price with trend
                        base_prices[symbol] *= (1 + price_change)
                        volume = np.random.exponential(2000000) * volume_multiplier + 1000000
                        
                        self.scanner.update_market_data(symbol, base_prices[symbol], volume)
                    
                    time.sleep(1)  # Update every second
                except Exception as e:
                    logger.error(f"Market data simulation error: {e}")
                    time.sleep(5)
        
        threading.Thread(target=simulate_data, daemon=True).start()
        logger.info("📊 Market data feed started")
    
    def _update_metrics(self):
        """Update trading metrics"""
        current_time = datetime.now()
        
        # Reset daily metrics at midnight
        if current_time.hour == 0 and current_time.minute == 0:
            self.daily_trades = 0
            self.daily_profit = 0.0
        
        logger.info(f"📈 Metrics: Active Positions: {len(self.active_positions)} | "
                   f"Daily P&L: ${self.daily_profit:.2f} | Win Rate: {self.win_rate:.1%} | "
                   f"Total Trades: {self.total_trades}")
    
    def get_status(self) -> Dict:
        """Get current bot status"""
        return {
            'is_running': self.is_running,
            'active_positions': len(self.active_positions),
            'daily_profit': self.daily_profit,
            'daily_trades': self.daily_trades,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'positions': list(self.active_positions.keys())
        }
    
    def stop(self):
        """Stop the trading bot"""
        logger.info("🛑 Stopping Crypto Day Trading Bot")
        self.is_running = False
        self.executor.shutdown(wait=True)

# Integration function for the main bot
def create_crypto_day_trader(alpaca_client, config: Dict) -> CryptoDayTradingBot:
    """Create and configure crypto day trading bot"""
    
    initial_capital = config.get('crypto_capital', 10000)
    bot = CryptoDayTradingBot(alpaca_client, initial_capital)
    
    # Configure from settings
    bot.max_position_size = config.get('max_position_size', initial_capital * 0.05)
    bot.max_concurrent_positions = config.get('max_positions', 10)
    bot.min_profit_target = config.get('min_profit', 0.003)
    bot.max_daily_loss = config.get('max_daily_loss', initial_capital * 0.02)
    
    return bot