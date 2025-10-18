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

    def get_system_status(self) -> Dict:
        """Get system status information"""
        try:
            account = self.api.get_account()
            market_status = 'OPEN' if account.trading_blocked == False else 'CLOSED'

            return {
                'last_update': self.last_update.isoformat(),
                'market_status': market_status,
                'is_trading': self.is_trading,
                'services': {
                    'alpaca': 'connected' if self.api else 'disconnected',
                    'trading_bot': 'running' if self.is_trading else 'stopped'
                }
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {
                'last_update': self.last_update.isoformat(),
                'market_status': 'UNKNOWN',
                'is_trading': self.is_trading,
                'services': {'alpaca': 'error'}
            }

    def get_account_data(self) -> Dict:
        """Get account information"""
        try:
            account = self.api.get_account()
            return {
                'status': account.status,
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'cash': float(account.cash),
                'equity': float(account.equity),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked
            }
        except Exception as e:
            logger.error(f"Error getting account data: {e}")
            return {
                'status': 'ERROR',
                'buying_power': 0,
                'portfolio_value': 0,
                'cash': 0,
                'equity': 0
            }

    def get_positions(self) -> List[Dict]:
        """Get current crypto positions."""
        try:
            positions = self.api.list_positions()
            position_data = []

            for pos in positions:
                if not self._is_crypto(pos.symbol):
                    continue

                position_data.append({
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price) if hasattr(pos, 'current_price') else 0,
                    'market_value': float(pos.market_value),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                    'side': pos.side,
                    'asset_class': 'crypto'
                })

            self.last_update = datetime.now()
            return position_data

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def calculate_signals(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """
        Calculate trading signals for symbols

        Args:
            symbols: List of symbols to analyze
        """
        effective_symbols = self._resolve_symbols(symbols)

        if not effective_symbols:
            logger.warning("No symbols configured for signal calculation; returning empty list")
            return []

        signals = []
        timeframe = self._resolve_timeframe()

        for symbol in effective_symbols:
            try:
                # Get market data
                bars = self.api.get_bars(
                    symbol,
                    timeframe,
                    limit=100
                ).df

                if len(bars) < 20:
                    continue

                # Calculate indicators
                prices = bars['close'].values
                volumes = bars['volume'].values

                rsi = self.indicator.calculate_rsi(prices)
                stoch_k, stoch_d = self.indicator.calculate_stochastic(
                    bars['high'].values,
                    bars['low'].values,
                    bars['close'].values
                )

                # Generate signal
                signal_strength = self._calculate_signal_strength(rsi, stoch_k, stoch_d)
                action = self._determine_action(rsi, stoch_k, stoch_d)

                signals.append({
                    'symbol': symbol,
                    'action': action,
                    'rsi': round(rsi, 2),
                    'stoch_k': round(stoch_k, 2),
                    'stoch_d': round(stoch_d, 2),
                    'price': round(prices[-1], 4),
                    'volume': int(volumes[-1]),
                    'strength': signal_strength,
                    'timestamp': datetime.now().isoformat()
                })

            except Exception as e:
                logger.error(f"Error calculating signals for {symbol}: {e}")

        return signals

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
            self.trading_bot = TradingBot(self.config)
            self.trading_executor = self.trading_bot.executor

            # Start trading
            self.is_trading = True

            logger.info("Trading bot started")
            return {
                'status': 'started',
                'config': self._config_snapshot()
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
