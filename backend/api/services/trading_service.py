#!/usr/bin/env python3
"""
Trading Service
Core business logic for trading operations
Integrates with existing trading_bot.py and trading_executor.py
"""

import logging
from datetime import datetime
from dataclasses import asdict, is_dataclass
from typing import Dict, List, Optional, Any

from trading_bot import TradingBot
from trading_executor import TradingExecutor
from signal_processor import SignalProcessor
from indicator import Indicator

logger = logging.getLogger(__name__)

class TradingService:
    """
    Service layer for trading operations
    Bridges Flask app with existing trading infrastructure
    """

    def __init__(self, alpaca_client, config):
        """
        Initialize trading service

        Args:
            alpaca_client: Alpaca API client
            config: Unified configuration object
        """
        self.client = alpaca_client
        self.config = config
        self.api = alpaca_client.api

        # Initialize components
        self.indicator = Indicator()
        self.signal_processor = None
        self.trading_executor = None
        self.trading_bot = None

        # Trading state
        self.is_trading = False
        self.last_update = datetime.now()
        
        # Scanner state
        self.scanner = None
        self._scanned_symbols_cache = []
        self._last_scan_time = datetime.min

        # Cache for rate limit protection (cache duration in seconds)
        self._cache_duration = 5  # 5 second cache
        self._account_cache = None
        self._account_cache_time = datetime.min
        self._positions_cache = None
        self._positions_cache_time = datetime.min

    def get_system_status(self) -> Dict:
        """Get system status information"""
        try:
            account = self.api.get_account()
            market_status = 'OPEN' if account.trading_blocked == False else 'CLOSED'

            status = {
                'last_update': self.last_update.isoformat(),
                'market_status': market_status,
                'is_trading': self.is_trading,
                'services': {
                    'alpaca': 'connected' if self.api else 'disconnected',
                    'trading_bot': 'running' if self.is_trading else 'stopped'
                }
            }
            
            # Enrich with detailed bot status if available
            if self.is_trading and self.trading_bot and hasattr(self.trading_bot, 'get_status'):
                status['bot_status'] = self.trading_bot.get_status()
                
            return status
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'last_update': self.last_update.isoformat(),
                'market_status': 'UNKNOWN',
                'is_trading': self.is_trading,
                'services': {'alpaca': 'error'}
            }

    def get_account_data(self) -> Dict:
        """Get account information - with caching to reduce API calls"""
        # Check cache first
        now = datetime.now()
        if self._account_cache and (now - self._account_cache_time).total_seconds() < self._cache_duration:
            return self._account_cache

        try:
            account = self.api.get_account()
            self._account_cache = {
                'status': account.status,
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'equity': float(account.equity),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked
            }
            self._account_cache_time = now
            return self._account_cache
        except Exception as e:
            logger.error(f"Error getting account data: {e}")
            # Return cached data if available, otherwise error state
            if self._account_cache:
                return self._account_cache
            return {
                'status': 'ERROR',
                'buying_power': 0,
                'portfolio_value': 0,
                'cash': 0,
                'equity': 0
            }

    def get_positions(self) -> List[Dict]:
        """Get current crypto positions - with caching to reduce API calls"""
        # Check cache first
        now = datetime.now()
        if self._positions_cache is not None and (now - self._positions_cache_time).total_seconds() < self._cache_duration:
            return self._positions_cache

        try:
            positions = self.api.list_positions()
            position_data = []

            for pos in positions:
                if not self._is_crypto(pos.symbol):
                    continue

                entry_price = float(pos.avg_entry_price)
                current_price = float(pos.current_price) if hasattr(pos, 'current_price') else 0
                position_data.append({
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'avg_entry_price': entry_price,
                    'avg_price': entry_price,  # Frontend compatibility
                    'entry_price': entry_price,  # Frontend compatibility
                    'current_price': current_price,
                    'market_value': float(pos.market_value),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                    'side': pos.side,
                    'asset_class': 'crypto'
                })

            self._positions_cache = position_data
            self._positions_cache_time = now
            self.last_update = now
            return position_data

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            # Return cached data if available
            if self._positions_cache is not None:
                return self._positions_cache
            return []

    def calculate_signals(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """
        Calculate trading signals for symbols - uses CACHED DATA to avoid API rate limits

        Args:
            symbols: List of symbols to analyze
        """
        logger.debug(
            "Calculating signals: has_bot=%s, has_scanner=%s, symbols=%s",
            self.trading_bot is not None,
            self.trading_bot.scanner is not None if self.trading_bot and hasattr(self.trading_bot, 'scanner') else False,
            symbols
        )
        signals = []

        # FIRST: Try to get signals from the trading bot's scanner (cached data)
        if self.trading_bot and hasattr(self.trading_bot, 'scanner'):
            try:
                scanner = self.trading_bot.scanner
                if hasattr(scanner, 'price_data') and scanner.price_data:
                    logger.debug(
                        "Using cached scanner data: %d symbols",
                        len(scanner.price_data) if scanner.price_data else 0
                    )

                    for symbol, prices in scanner.price_data.items():
                        if len(prices) < 2:
                            continue

                        try:
                            current_price = prices[-1]
                            volumes = scanner.volume_data.get(symbol, [0])
                            current_volume = volumes[-1] if volumes else 0

                            # Get indicators from scanner
                            indicators = scanner.get_indicators(symbol) if hasattr(scanner, 'get_indicators') else {}

                            rsi = indicators.get('rsi', 50)
                            stoch_k = indicators.get('stoch_k', 50)
                            stoch_d = indicators.get('stoch_d', 50)

                            # Calculate momentum for action
                            momentum = scanner.calculate_momentum(prices) if hasattr(scanner, 'calculate_momentum') else 0.5

                            # Determine action
                            if rsi < 35 or stoch_k < 30:
                                action = 'BUY'
                            elif rsi > 65 or stoch_k > 70:
                                action = 'SELL'
                            else:
                                action = 'HOLD'

                            signal_strength = self._calculate_signal_strength(rsi, stoch_k, stoch_d)

                            signals.append({
                                'symbol': symbol,
                                'action': action,
                                'rsi': round(float(rsi), 2),
                                'stoch_k': round(float(stoch_k), 2),
                                'stoch_d': round(float(stoch_d), 2),
                                'price': round(float(current_price), 4),
                                'volume': int(current_volume),
                                'strength': signal_strength,
                                'momentum': round(float(momentum), 3),
                                'timestamp': datetime.now().isoformat(),
                                'source': 'cached'
                            })
                        except Exception as e:
                            logger.debug(f"Error processing cached {symbol}: {e}")

                    if signals:
                        logger.info(f"Returning {len(signals)} signals from cached data (0 API calls)")
                        return signals

            except Exception as e:
                logger.debug(f"Could not use scanner cache: {e}")

        # FALLBACK: Return empty list instead of making API calls
        # This preserves rate limit budget for trading operations
        logger.info("No cached signals available - returning empty (rate limit protection)")
        return []

    def place_order(self, order_params: Dict) -> Dict:
        """Place an order"""
        try:
            order = self.api.submit_order(
                symbol=order_params['symbol'],
                qty=order_params['qty'],
                side=order_params['side'],
                type=order_params.get('type', 'market'),
                time_in_force=order_params.get('time_in_force', 'gtc'),
                limit_price=order_params.get('limit_price'),
                stop_price=order_params.get('stop_price')
            )

            return {
                'id': order.id,
                'symbol': order.symbol,
                'qty': order.qty,
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'submitted_at': order.submitted_at
            }

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise

    def get_orders(self, status: str = 'all', limit: int = 50) -> List[Dict]:
        """Get orders"""
        try:
            orders = self.api.list_orders(status=status, limit=limit)
            return [
                {
                    'id': order.id,
                    'symbol': order.symbol,
                    'qty': order.qty,
                    'side': order.side,
                    'type': order.type,
                    'status': order.status,
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at,
                    'filled_qty': order.filled_qty
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []

    def start_trading(self, config_overrides: Optional[Dict] = None) -> Dict:
        """Start automated trading"""
        if self.is_trading:
            return {'status': 'already_running', 'config': self._config_snapshot()}

        try:
            # Apply config overrides if provided
            if config_overrides:
                # Update config with overrides
                pass

            # Initialize trading bot
            # Strategy and data manager placeholders
            strategy_name = getattr(self.config, 'strategy', 'stoch_rsi')
            
            # Check for crypto scalping strategy override or default
            if strategy_name == 'crypto_scalping' or getattr(self.config, 'crypto_scanner', {}).get('enabled', False):
                try:
                    from strategies.crypto_scalping_strategy import create_crypto_day_trader
                    self.trading_bot = create_crypto_day_trader(self.client, self.config)
                    # CryptoDayTradingBot handles its own execution logic
                    self.trading_executor = getattr(self.trading_bot, 'trading_executor', None) 
                    
                    # Start bot in a background thread with its own event loop
                    import threading
                    import asyncio
                    def run_async_bot():
                        try:
                            asyncio.run(self.trading_bot.start_trading())
                        except Exception as e:
                            logger.error(f"Trading bot thread crashed: {e}")
                            import traceback
                            logger.error(traceback.format_exc())
                            self.is_trading = False

                    self._bot_thread = threading.Thread(target=run_async_bot, daemon=True)
                    self._bot_thread.start()
                    
                    logger.info("Crypto Scalping Bot started in background thread")
                    
                except ImportError as e:
                    logger.error(f"Failed to import crypto strategy: {e}")
                    # Fallback to stub
                    self.trading_bot = TradingBot(self, strategy_name)
                    self.trading_executor = self.trading_bot.trading_executor
            else:
                self.trading_bot = TradingBot(self, strategy_name)  # Pass self as data_manager placeholder
                self.trading_executor = self.trading_bot.trading_executor

            # Start trading
            self.is_trading = True

            logger.info("Trading bot started")
            return {
                'status': 'started',
                'config': self._config_snapshot(),
                'strategy': strategy_name
            }

        except Exception as e:
            logger.error(f"Error starting trading: {e}")
            self.is_trading = False
            raise

    def stop_trading(self, close_positions: bool = False) -> Dict:
        """Stop automated trading"""
        if not self.is_trading:
            return {'status': 'not_running', 'positions_closed': 0}

        try:
            positions_closed = 0

            if close_positions:
                results = self.close_all_positions()
                positions_closed = len(results)

            if hasattr(self.trading_bot, 'stop'):
                self.trading_bot.stop()
                
            self.is_trading = False
            self.trading_bot = None
            self.trading_executor = None

            logger.info(f"Trading bot stopped. Positions closed: {positions_closed}")
            return {
                'status': 'stopped',
                'positions_closed': positions_closed
            }

        except Exception as e:
            logger.error(f"Error stopping trading: {e}")
            raise

    def close_position(self, symbol: str) -> Optional[Dict]:
        """Close a specific position"""
        try:
            position = self.api.get_position(symbol)
            order = self.api.submit_order(
                symbol=symbol,
                qty=abs(float(position.qty)),
                side='sell' if position.side == 'long' else 'buy',
                type='market',
                time_in_force='gtc'
            )

            return {
                'order_id': order.id,
                'symbol': symbol,
                'qty': order.qty,
                'side': order.side
            }

        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}")
            return None

    def close_all_positions(self) -> List[Dict]:
        """Close all positions"""
        try:
            positions = self.api.list_positions()
            results = []

            for position in positions:
                result = self.close_position(position.symbol)
                if result:
                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return []

    def _resolve_symbols(self, override: Optional[List[str]] = None) -> List[str]:
        if override:
            return list(override)

        # Check if scanner is enabled in config
        crypto_scanner_cfg = getattr(self.config, 'crypto_scanner', None)
        
        if crypto_scanner_cfg and getattr(crypto_scanner_cfg, 'enable_market_scan', False):
            # Use cached symbols if available and recent (5 mins)
            if self._scanned_symbols_cache and \
               (datetime.now() - self._last_scan_time).total_seconds() < 300:
                logger.info("Using cached scanned symbols")
                return self._scanned_symbols_cache

            try:
                # Initialize scanner if needed
                if not self.scanner:
                    from strategies.crypto_scalping_strategy import CryptoVolatilityScanner
                    self.scanner = CryptoVolatilityScanner(
                        config=crypto_scanner_cfg
                    )
                
                logger.info("Scanning market for top volatile pairs...")
                # Allow scanner to fetch all assets and select top 20
                top_pairs = self.scanner.select_top_volatile_pairs(self.api, target_count=20)

                # Normalize symbols to BASE/QUOTE format (e.g. BTCUSD -> BTC/USD)
                formatted_pairs = []
                for symbol in top_pairs:
                    if "/" not in symbol:
                        if symbol.endswith("USD"):
                            formatted_pairs.append(f"{symbol[:-3]}/USD")
                        elif symbol.endswith("USDT"):
                            formatted_pairs.append(f"{symbol[:-4]}/USDT")
                        elif symbol.endswith("USDC"):
                            formatted_pairs.append(f"{symbol[:-4]}/USDC")
                        else:
                            formatted_pairs.append(symbol)
                    else:
                        formatted_pairs.append(symbol)
                
                self._scanned_symbols_cache = formatted_pairs
                self._last_scan_time = datetime.now()
                return formatted_pairs
            except Exception as e:
                logger.error(f"Scanner failed, falling back to configured symbols: {e}", exc_info=True)

        symbols = getattr(self.config, 'symbols', None)
        if symbols:
            return list(symbols)

        trading_cfg = getattr(self.config, 'trading', None)
        if trading_cfg is not None:
            cfg_symbols = getattr(trading_cfg, 'symbols', None)
            if cfg_symbols:
                return list(cfg_symbols)

        return []

    def _resolve_timeframe(self) -> str:
        timeframe = getattr(self.config, 'timeframe', None)
        if timeframe:
            return timeframe

        trading_cfg = getattr(self.config, 'trading', None)
        if trading_cfg is not None:
            cfg_timeframe = getattr(trading_cfg, 'timeframe', None)
            if cfg_timeframe:
                return cfg_timeframe

        return '1Min'

    def _config_snapshot(self) -> Dict[str, Any]:
        cfg = self.config
        if is_dataclass(cfg):
            return asdict(cfg)
        if hasattr(cfg, '__dict__'):
            snapshot = {}
            for key, value in cfg.__dict__.items():
                if key.startswith('_'):
                    continue
                snapshot[key] = value
            return snapshot
        return {}

    def update_strategy(self, strategy_name: str, parameters: Optional[Dict] = None) -> Dict:
        """Update trading strategy"""
        # TODO: Implement strategy update logic
        return {
            'strategy': strategy_name,
            'parameters': parameters or {}
        }

    def _is_crypto(self, symbol: str) -> bool:
        """Check if symbol is cryptocurrency"""
        crypto_suffixes = ['USD', 'USDT', 'USDC', 'BTC', 'ETH']
        return any(symbol.endswith(suffix) for suffix in crypto_suffixes)

    def _calculate_signal_strength(self, rsi: float, stoch_k: float, stoch_d: float) -> str:
        """Calculate signal strength"""
        if (rsi < 25 and stoch_k < 20) or (rsi > 75 and stoch_k > 80):
            return 'Strong'
        elif (rsi < 35 and stoch_k < 30) or (rsi > 65 and stoch_k > 70):
            return 'Medium'
        else:
            return 'Weak'

    def _determine_action(self, rsi: float, stoch_k: float, stoch_d: float) -> str:
        """Determine trading action"""
        if rsi < 30 and stoch_k < 20 and stoch_k > stoch_d:
            return 'BUY'
        elif rsi > 70 and stoch_k > 80 and stoch_k < stoch_d:
            return 'SELL'
        else:
            return 'HOLD'
