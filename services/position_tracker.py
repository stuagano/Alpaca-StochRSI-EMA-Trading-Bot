#!/usr/bin/env python3
"""
Position Tracker Service - Proper position and P&L tracking
Based on industry best practices for scalping bots
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class Position:
    """Represents a trading position with entry/exit tracking"""
    symbol: str
    entry_price: float
    qty: float
    entry_time: datetime
    entry_order_id: str
    state: str = 'OPEN'  # OPEN, CLOSING, CLOSED
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_order_id: Optional[str] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    fees: float = 0.0
    
    def calculate_pnl(self, exit_price: float, fee_rate: float = 0.0) -> Tuple[float, float]:
        """Calculate P&L for this position"""
        # Gross P&L
        gross_pnl = (exit_price - self.entry_price) * self.qty
        
        # Calculate fees (entry + exit)
        entry_fee = self.entry_price * self.qty * fee_rate
        exit_fee = exit_price * self.qty * fee_rate
        total_fees = entry_fee + exit_fee
        
        # Net P&L
        net_pnl = gross_pnl - total_fees
        
        # P&L percentage
        pnl_percent = (net_pnl / (self.entry_price * self.qty)) * 100
        
        return net_pnl, pnl_percent
    
    def close(self, exit_price: float, exit_order_id: str, fee_rate: float = 0.0):
        """Close this position"""
        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.exit_order_id = exit_order_id
        self.pnl, self.pnl_percent = self.calculate_pnl(exit_price, fee_rate)
        self.state = 'CLOSED'

@dataclass
class Order:
    """Represents a trading order"""
    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    qty: float
    order_type: str  # 'market' or 'limit'
    price: Optional[float] = None
    status: str = 'pending'  # pending, filled, cancelled
    filled_price: Optional[float] = None
    filled_qty: Optional[float] = None
    filled_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

class PositionTracker:
    """
    Manages positions and tracks P&L properly
    Based on Alpaca's official scalping example
    """
    
    def __init__(self, fee_rate: float = 0.0):
        self.fee_rate = fee_rate
        self.positions: Dict[str, List[Position]] = defaultdict(list)
        self.closed_positions: List[Position] = []
        self.pending_orders: Dict[str, Order] = {}
        self.filled_orders: Dict[str, Order] = {}
        
        # Statistics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.daily_pnl = 0.0
        self.session_start = datetime.now()
        
    def can_open_position(self, symbol: str) -> bool:
        """Check if we can open a new position for this symbol"""
        # Get open positions for this symbol
        open_positions = [p for p in self.positions[symbol] if p.state == 'OPEN']
        
        # For scalping, typically only one position per symbol
        return len(open_positions) == 0
    
    def has_open_position(self, symbol: str) -> bool:
        """Check if there's an open position for this symbol"""
        return any(p.state == 'OPEN' for p in self.positions[symbol])
    
    def get_open_position(self, symbol: str) -> Optional[Position]:
        """Get the open position for a symbol"""
        open_positions = [p for p in self.positions[symbol] if p.state == 'OPEN']
        return open_positions[0] if open_positions else None
    
    def open_position(self, symbol: str, entry_price: float, qty: float, order_id: str) -> Position:
        """Open a new position"""
        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            qty=qty,
            entry_time=datetime.now(),
            entry_order_id=order_id
        )
        self.positions[symbol].append(position)
        logger.info(f"Opened position: {symbol} - {qty} @ ${entry_price:.2f}")
        return position
    
    def close_position(self, symbol: str, exit_price: float, order_id: str) -> Optional[Position]:
        """Close an open position using FIFO"""
        open_positions = [p for p in self.positions[symbol] if p.state == 'OPEN']
        
        if not open_positions:
            logger.warning(f"No open position to close for {symbol}")
            return None
        
        # Use FIFO - close the oldest position first
        position = open_positions[0]
        position.close(exit_price, order_id, self.fee_rate)
        
        # Update statistics
        self.total_trades += 1
        self.total_pnl += position.pnl
        self.daily_pnl += position.pnl
        
        if position.pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Move to closed positions
        self.closed_positions.append(position)
        
        logger.info(f"Closed position: {symbol} - P&L: ${position.pnl:.2f} ({position.pnl_percent:.2f}%)")
        return position
    
    def submit_order(self, symbol: str, side: str, qty: float, order_type: str = 'market', price: Optional[float] = None) -> Optional[Order]:
        """Submit a new order with deduplication"""
        # Check for existing pending orders
        for order in self.pending_orders.values():
            if order.symbol == symbol and order.side == side and order.status == 'pending':
                logger.warning(f"Already have pending {side} order for {symbol}")
                return None
        
        # Create new order
        order_id = f"{symbol}_{side}_{datetime.now().timestamp()}"
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            qty=qty,
            order_type=order_type,
            price=price
        )
        
        self.pending_orders[order_id] = order
        logger.info(f"Submitted {side} order: {symbol} - {qty} @ {price or 'market'}")
        return order
    
    def fill_order(self, order_id: str, filled_price: float, filled_qty: Optional[float] = None):
        """Mark an order as filled"""
        if order_id not in self.pending_orders:
            logger.warning(f"Order {order_id} not found in pending orders")
            return None
        
        order = self.pending_orders[order_id]
        order.status = 'filled'
        order.filled_price = filled_price
        order.filled_qty = filled_qty or order.qty
        order.filled_at = datetime.now()
        
        # Move to filled orders
        self.filled_orders[order_id] = order
        del self.pending_orders[order_id]
        
        # Handle position tracking
        if order.side == 'buy':
            self.open_position(order.symbol, filled_price, order.filled_qty, order_id)
        elif order.side == 'sell':
            self.close_position(order.symbol, filled_price, order_id)
        
        return order
    
    def cancel_order(self, order_id: str):
        """Cancel a pending order"""
        if order_id in self.pending_orders:
            order = self.pending_orders[order_id]
            order.status = 'cancelled'
            del self.pending_orders[order_id]
            logger.info(f"Cancelled order: {order_id}")
    
    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        avg_win = sum(p.pnl for p in self.closed_positions if p.pnl > 0) / self.winning_trades if self.winning_trades > 0 else 0
        avg_loss = sum(p.pnl for p in self.closed_positions if p.pnl < 0) / self.losing_trades if self.losing_trades > 0 else 0
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'session_duration': str(datetime.now() - self.session_start)
        }
    
    def get_open_positions_summary(self) -> List[Dict]:
        """Get summary of all open positions"""
        summary = []
        for symbol, positions in self.positions.items():
            for position in positions:
                if position.state == 'OPEN':
                    summary.append({
                        'symbol': position.symbol,
                        'qty': position.qty,
                        'entry_price': position.entry_price,
                        'entry_time': position.entry_time.isoformat(),
                        'age': str(datetime.now() - position.entry_time)
                    })
        return summary
    
    def cleanup_old_positions(self, max_age_hours: int = 24):
        """Clean up old closed positions to save memory"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        self.closed_positions = [
            p for p in self.closed_positions 
            if p.exit_time and p.exit_time > cutoff_time
        ]