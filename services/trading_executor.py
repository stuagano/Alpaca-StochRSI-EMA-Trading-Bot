#!/usr/bin/env python3
"""
Trading Execution Engine
Handles order placement, position management, and trade lifecycle
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import alpaca_trade_api as tradeapi
from dataclasses import dataclass
import asyncio
import json
from .position_manager import PositionManager, Position as PosManagerPosition

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    """Order status states"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class PositionState(Enum):
    """Position lifecycle states"""
    PENDING_ENTRY = "pending_entry"
    OPEN = "open"
    PENDING_EXIT = "pending_exit"
    CLOSED = "closed"

@dataclass
class TradingSignal:
    """Trading signal data structure"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    strength: float  # 0-100
    price: float
    timestamp: datetime
    reason: str
    indicators: Dict
    
@dataclass
class Position:
    """Position tracking data structure"""
    symbol: str
    quantity: int
    entry_price: float
    entry_time: datetime
    state: PositionState
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    signal_strength: Optional[float] = None

class TradingExecutor:
    """Main trading execution engine"""
    
    def __init__(self, api: tradeapi.REST, config: Dict):
        """
        Initialize trading executor
        
        Args:
            api: Alpaca API client
            config: Trading configuration parameters
        """
        self.api = api
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.active_orders: Dict[str, Dict] = {}
        self.order_history: List[Dict] = []
        
        # Initialize position manager
        self.position_manager = PositionManager(api, config)
        
        # Configuration
        self.max_positions = config.get('max_positions', 5)
        self.max_position_size_pct = config.get('max_position_size_pct', 0.10)
        self.max_account_exposure_pct = config.get('max_account_exposure_pct', 0.50)
        self.min_signal_strength = config.get('min_signal_strength', 70)
        
        # Risk parameters
        self.stop_loss_pct = config.get('stop_loss_pct', 0.02)
        self.take_profit_ratio = config.get('take_profit_ratio', 2.0)
        self.use_trailing_stop = config.get('use_trailing_stop', True)
        
        logger.info(f"Trading Executor initialized with enhanced position management")
        
    async def execute_signal(self, signal: TradingSignal) -> Optional[Dict]:
        """
        Execute a trading signal
        
        Args:
            signal: Trading signal to execute
            
        Returns:
            Order details if executed, None otherwise
        """
        try:
            # Validate signal strength
            if signal.strength < self.min_signal_strength:
                logger.info(f"Signal strength {signal.strength} below minimum {self.min_signal_strength}")
                return None
                
            # Check market status
            if not await self.is_market_open():
                logger.info("Market is closed, queuing order for next open")
                return await self.queue_for_market_open(signal)
                
            # Validate pre-trade conditions
            validation = await self.validate_pre_trade(signal)
            if not validation['valid']:
                logger.warning(f"Pre-trade validation failed: {validation['reason']}")
                return None
                
            # Calculate position size
            position_size = await self.calculate_position_size(signal)
            if position_size == 0:
                logger.warning("Calculated position size is 0")
                return None
                
            # Place the order
            order = await self.place_order(
                symbol=signal.symbol,
                qty=position_size,
                side='buy' if signal.action == 'BUY' else 'sell',
                order_type='market'
            )
            
            if order:
                # Add position to position manager
                if signal.action == 'BUY':
                    await self.position_manager.add_position(
                        symbol=signal.symbol,
                        qty=position_size,
                        side='long',
                        entry_price=signal.price,
                        strategy=self.config.get('strategy', 'auto')
                    )
                
                # Set stop loss and take profit
                await self.place_protection_orders(signal.symbol, position_size, signal.price)
                
                # Update position tracking
                await self.update_position(signal.symbol, order)
                
                # Log successful execution
                logger.info(f"Successfully executed {signal.action} order for {position_size} shares of {signal.symbol}")
                
                return order
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return None
            
    async def validate_pre_trade(self, signal: TradingSignal) -> Dict:
        """
        Validate pre-trade conditions
        
        Args:
            signal: Trading signal to validate
            
        Returns:
            Validation result with 'valid' boolean and 'reason' if invalid
        """
        try:
            account = self.api.get_account()
            
            # Check account status
            if account.trading_blocked:
                return {'valid': False, 'reason': 'Account trading is blocked'}
                
            # Check pattern day trader
            if account.pattern_day_trader and float(account.equity) < 25000:
                return {'valid': False, 'reason': 'PDT restriction - equity below $25,000'}
                
            # Check buying power
            if signal.action == 'BUY':
                buying_power = float(account.buying_power)
                estimated_cost = signal.price * 100  # Minimum 100 shares
                
                if buying_power < estimated_cost:
                    return {'valid': False, 'reason': f'Insufficient buying power: ${buying_power:.2f}'}
                    
            # Check position limits
            if signal.action == 'BUY':
                if len(self.positions) >= self.max_positions:
                    return {'valid': False, 'reason': f'Maximum positions ({self.max_positions}) reached'}
                    
                # Check if already have position in symbol
                if signal.symbol in self.positions:
                    if self.positions[signal.symbol].state == PositionState.OPEN:
                        return {'valid': False, 'reason': f'Already have open position in {signal.symbol}'}
                        
            # Check for pending orders
            orders = self.api.list_orders(status='open')
            for order in orders:
                if order.symbol == signal.symbol:
                    return {'valid': False, 'reason': f'Pending order exists for {signal.symbol}'}
                    
            return {'valid': True, 'reason': 'All validations passed'}
            
        except Exception as e:
            logger.error(f"Error in pre-trade validation: {e}")
            return {'valid': False, 'reason': f'Validation error: {str(e)}'}
            
    async def calculate_position_size(self, signal: TradingSignal) -> int:
        """
        Calculate appropriate position size based on account and risk parameters
        
        Args:
            signal: Trading signal
            
        Returns:
            Number of shares to trade
        """
        try:
            account = self.api.get_account()
            equity = float(account.equity)
            
            # Calculate maximum position value
            max_position_value = equity * self.max_position_size_pct
            
            # Calculate shares based on current price
            shares = int(max_position_value / signal.price)
            
            # Apply minimum share requirement
            shares = max(shares, 1)
            
            # Apply signal strength scaling (stronger signal = larger position)
            strength_multiplier = signal.strength / 100.0
            shares = int(shares * strength_multiplier)
            
            logger.info(f"Calculated position size: {shares} shares for {signal.symbol}")
            return shares
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
            
    async def place_order(self, symbol: str, qty: int, side: str, order_type: str = 'market') -> Optional[Dict]:
        """
        Place an order with Alpaca
        
        Args:
            symbol: Stock symbol
            qty: Number of shares
            side: 'buy' or 'sell'
            order_type: Type of order (market, limit, etc.)
            
        Returns:
            Order details if successful
        """
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force='day'
            )
            
            # Track the order
            self.active_orders[order.id] = {
                'symbol': symbol,
                'qty': qty,
                'side': side,
                'status': order.status,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'filled_qty': order.filled_qty or 0,
                'filled_price': order.filled_avg_price or 0
            }
            
            logger.info(f"Order placed: {side} {qty} shares of {symbol}, Order ID: {order.id}")
            return self.active_orders[order.id]
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
            
    async def place_protection_orders(self, symbol: str, qty: int, entry_price: float) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Place stop loss and take profit orders
        
        Args:
            symbol: Stock symbol
            qty: Number of shares
            entry_price: Entry price for the position
            
        Returns:
            Tuple of (stop_loss_order, take_profit_order)
        """
        try:
            # Calculate stop loss price
            stop_loss_price = entry_price * (1 - self.stop_loss_pct)
            
            # Calculate take profit price
            risk = entry_price * self.stop_loss_pct
            take_profit_price = entry_price + (risk * self.take_profit_ratio)
            
            # Place stop loss order
            stop_order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='stop',
                stop_price=stop_loss_price,
                time_in_force='gtc'
            )
            
            # Place take profit order
            profit_order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                type='limit',
                limit_price=take_profit_price,
                time_in_force='gtc'
            )
            
            logger.info(f"Protection orders placed for {symbol}: Stop@${stop_loss_price:.2f}, Target@${take_profit_price:.2f}")
            
            return (
                {'id': stop_order.id, 'stop_price': stop_loss_price},
                {'id': profit_order.id, 'limit_price': take_profit_price}
            )
            
        except Exception as e:
            logger.error(f"Error placing protection orders: {e}")
            return None, None
            
    async def update_position(self, symbol: str, order: Dict):
        """
        Update position tracking after order execution
        
        Args:
            symbol: Stock symbol
            order: Order details
        """
        try:
            if order['side'] == 'buy':
                # Create or update position
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=order['qty'],
                    entry_price=order['filled_price'] or 0,
                    entry_time=datetime.now(),
                    state=PositionState.OPEN
                )
                logger.info(f"Position opened: {symbol} - {order['qty']} shares @ ${order['filled_price']:.2f}")
                
            elif order['side'] == 'sell':
                # Close or reduce position
                if symbol in self.positions:
                    self.positions[symbol].state = PositionState.CLOSED
                    logger.info(f"Position closed: {symbol}")
                    
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            
    async def is_market_open(self) -> bool:
        """
        Check if market is currently open for trading
        
        Returns:
            True if market is open
        """
        try:
            clock = self.api.get_clock()
            return clock.is_open
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
            
    async def queue_for_market_open(self, signal: TradingSignal) -> Dict:
        """
        Queue an order for execution when market opens
        
        Args:
            signal: Trading signal to queue
            
        Returns:
            Queue confirmation
        """
        # This would typically store in a database or persistent queue
        # For now, we'll just log it
        logger.info(f"Order queued for market open: {signal.symbol} - {signal.action}")
        return {
            'status': 'queued',
            'symbol': signal.symbol,
            'action': signal.action,
            'queued_at': datetime.now().isoformat()
        }
        
    async def cancel_all_orders(self):
        """Emergency cancel all open orders"""
        try:
            self.api.cancel_all_orders()
            logger.info("All orders cancelled")
            self.active_orders.clear()
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
            
    async def get_position_summary(self) -> Dict:
        """
        Get comprehensive position summary using position manager
        
        Returns:
            Dictionary with enhanced position details and metrics
        """
        try:
            # Get positions from position manager
            positions = await self.position_manager.get_all_positions()
            metrics = await self.position_manager.get_portfolio_metrics()
            
            summary = {
                'total_positions': metrics.total_positions,
                'long_positions': metrics.long_positions,
                'short_positions': metrics.short_positions,
                'total_value': metrics.total_market_value,
                'total_pnl': metrics.total_unrealized_pnl,
                'total_pnl_pct': metrics.total_unrealized_pnl_pct,
                'largest_position': metrics.largest_position,
                'portfolio_concentration': metrics.portfolio_concentration,
                'win_rate': metrics.win_rate,
                'avg_hold_time_hours': metrics.avg_hold_time.total_seconds() / 3600,
                'positions': []
            }
            
            for pos in positions:
                position_data = {
                    'symbol': pos.symbol,
                    'qty': pos.qty,
                    'side': pos.side,
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_pct': pos.unrealized_pnl_pct,
                    'stop_loss': pos.stop_loss,
                    'take_profit': pos.take_profit,
                    'risk_amount': pos.risk_amount,
                    'strategy': pos.strategy,
                    'entry_time': pos.entry_time.isoformat(),
                    'is_profitable': pos.is_profitable,
                    'risk_reward_ratio': pos.risk_reward_ratio
                }
                summary['positions'].append(position_data)
                
            return summary
            
        except Exception as e:
            logger.error(f"Error getting position summary: {e}")
            return {'error': str(e)}
    
    async def check_risk_management(self) -> Dict:
        """
        Check all risk management rules and triggers
        
        Returns:
            Dictionary with risk status and any triggered alerts
        """
        try:
            # Check stop losses
            stop_loss_triggers = await self.position_manager.check_stop_losses()
            
            # Check take profits
            take_profit_triggers = await self.position_manager.check_take_profits()
            
            # Get risk report
            risk_report = await self.position_manager.get_risk_report()
            
            return {
                'stop_loss_triggers': stop_loss_triggers,
                'take_profit_triggers': take_profit_triggers,
                'risk_report': risk_report,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking risk management: {e}")
            return {'error': str(e)}
    
    async def update_position_levels(self, symbol: str, stop_loss: Optional[float] = None,
                                   take_profit: Optional[float] = None) -> bool:
        """
        Update stop loss and take profit levels for a position
        
        Args:
            symbol: Stock symbol
            stop_loss: New stop loss price
            take_profit: New take profit price
            
        Returns:
            True if successful
        """
        return await self.position_manager.update_position_levels(symbol, stop_loss, take_profit)
    
    async def close_position_by_symbol(self, symbol: str, reason: str = 'manual') -> bool:
        """
        Close a position by symbol
        
        Args:
            symbol: Stock symbol to close
            reason: Reason for closing
            
        Returns:
            True if successful
        """
        try:
            # Get current market price
            latest_trade = self.api.get_latest_trade(symbol)
            exit_price = float(latest_trade.price) if latest_trade else 0
            
            # Close position in position manager
            return await self.position_manager.close_position(symbol, exit_price, reason)
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return False