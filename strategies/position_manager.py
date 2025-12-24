"""
Position Manager Module
Handles position tracking, synchronization, and P&L calculations
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    entry_price: float
    quantity: float
    side: str  # 'buy' or 'sell'
    entry_time: datetime
    target_price: float
    stop_price: float
    order_id: Optional[str] = None
    synced_from_alpaca: bool = False
    unrealized_pnl: float = 0.0
    current_price: float = 0.0
    highest_price: float = 0.0  # For trailing stop
    signal: Optional[Any] = None

    @property
    def entry_price_dec(self) -> Decimal:
        return Decimal(str(self.entry_price))

    @property
    def quantity_dec(self) -> Decimal:
        return Decimal(str(self.quantity))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return {
            'symbol': self.symbol,
            'entry_price': self.entry_price,
            'entry_price_dec': self.entry_price_dec,
            'quantity': self.quantity,
            'quantity_dec': self.quantity_dec,
            'side': self.side,
            'entry_time': self.entry_time,
            'target_price': self.target_price,
            'stop_price': self.stop_price,
            'order_id': self.order_id,
            'synced_from_alpaca': self.synced_from_alpaca,
            'unrealized_pnl': self.unrealized_pnl,
            'current_price': self.current_price,
            'highest_price': self.highest_price,
            'signal': self.signal,
        }


class PositionManager:
    """Manages trading positions with synchronization to Alpaca"""

    def __init__(
        self,
        alpaca_api,
        stop_loss_pct: float = 0.015,
        take_profit_pct: float = 0.015,
        max_positions: int = 10,
    ):
        self.api = alpaca_api
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_positions = max_positions
        self._positions: Dict[str, Position] = {}

    @property
    def positions(self) -> Dict[str, Position]:
        """Get all active positions"""
        return self._positions

    @property
    def count(self) -> int:
        """Get number of active positions"""
        return len(self._positions)

    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in a symbol"""
        return symbol in self._positions

    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol"""
        return self._positions.get(symbol)

    def add_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        side: str = 'buy',
        order_id: Optional[str] = None,
        signal: Optional[Any] = None,
    ) -> Position:
        """Add a new position"""
        target_price = entry_price * (1 + self.take_profit_pct) if side == 'buy' else entry_price * (1 - self.take_profit_pct)
        stop_price = entry_price * (1 - self.stop_loss_pct) if side == 'buy' else entry_price * (1 + self.stop_loss_pct)

        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            side=side,
            entry_time=datetime.now(),
            target_price=target_price,
            stop_price=stop_price,
            order_id=order_id,
            current_price=entry_price,
            highest_price=entry_price,
            signal=signal,
        )

        self._positions[symbol] = position
        logger.info(f"📈 Added position: {symbol} | Entry: ${entry_price:.4f} | Qty: {quantity}")
        return position

    def remove_position(self, symbol: str) -> Optional[Position]:
        """Remove a position"""
        position = self._positions.pop(symbol, None)
        if position:
            logger.info(f"📉 Removed position: {symbol}")
        return position

    def update_price(self, symbol: str, current_price: float) -> None:
        """Update current price for a position"""
        if symbol in self._positions:
            pos = self._positions[symbol]
            pos.current_price = current_price
            if current_price > pos.highest_price:
                pos.highest_price = current_price

            # Update unrealized P&L
            if pos.side == 'buy':
                pos.unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
            else:
                pos.unrealized_pnl = (pos.entry_price - current_price) * pos.quantity

    def sync_from_alpaca(self) -> int:
        """Sync positions from Alpaca API. Returns number of positions synced."""
        try:
            positions = self.api.list_positions()
            synced_count = 0

            for pos in positions:
                symbol = pos.symbol
                # Only track crypto positions
                if not symbol.endswith('USD') and not symbol.endswith('USDT'):
                    continue

                if symbol not in self._positions:
                    entry_price = float(pos.avg_entry_price)
                    qty = float(pos.qty)
                    side = 'buy' if qty > 0 else 'sell'

                    position = Position(
                        symbol=symbol,
                        entry_price=entry_price,
                        quantity=abs(qty),
                        side=side,
                        entry_time=datetime.now(),  # Approximate
                        target_price=entry_price * (1 + self.take_profit_pct) if side == 'buy' else entry_price * (1 - self.take_profit_pct),
                        stop_price=entry_price * (1 - self.stop_loss_pct) if side == 'buy' else entry_price * (1 + self.stop_loss_pct),
                        synced_from_alpaca=True,
                        unrealized_pnl=float(pos.unrealized_pl) if hasattr(pos, 'unrealized_pl') else 0,
                        current_price=float(pos.current_price) if hasattr(pos, 'current_price') else entry_price,
                    )
                    self._positions[symbol] = position
                    synced_count += 1
                    logger.info(f"📥 Synced position: {symbol} | Entry: ${entry_price:.4f} | Qty: {qty}")

            # Remove positions that no longer exist on Alpaca
            alpaca_symbols = {pos.symbol for pos in positions}
            to_remove = [s for s in self._positions if s not in alpaca_symbols]
            for symbol in to_remove:
                del self._positions[symbol]
                logger.info(f"📤 Removed closed position: {symbol}")

            if synced_count > 0:
                logger.info(f"✅ Synced {synced_count} positions. Total: {len(self._positions)}")

            return synced_count

        except Exception as e:
            logger.error(f"Failed to sync positions: {e}")
            return 0

    def check_exit_conditions(
        self,
        symbol: str,
        current_price: float,
        max_hold_time_seconds: int = 1800,
        trailing_stop_pct: float = 0.01,
    ) -> Optional[str]:
        """
        Check if position should be closed.
        Returns exit reason if should close, None otherwise.
        """
        if symbol not in self._positions:
            return None

        pos = self._positions[symbol]
        self.update_price(symbol, current_price)

        hold_time = (datetime.now() - pos.entry_time).total_seconds()

        # Check take profit
        if pos.side == 'buy' and current_price >= pos.target_price:
            return 'take_profit'
        elif pos.side == 'sell' and current_price <= pos.target_price:
            return 'take_profit'

        # Check stop loss
        if pos.side == 'buy' and current_price <= pos.stop_price:
            return 'stop_loss'
        elif pos.side == 'sell' and current_price >= pos.stop_price:
            return 'stop_loss'

        # Check trailing stop
        if pos.side == 'buy' and pos.highest_price > pos.entry_price:
            trailing_stop_price = pos.highest_price * (1 - trailing_stop_pct)
            if current_price <= trailing_stop_price and current_price > pos.entry_price:
                return 'trailing_stop'

        # Check max hold time
        if hold_time >= max_hold_time_seconds:
            return 'max_hold_time'

        return None

    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized P&L across all positions"""
        return sum(pos.unrealized_pnl for pos in self._positions.values())

    def get_positions_summary(self) -> Dict[str, Any]:
        """Get summary of all positions"""
        return {
            'count': len(self._positions),
            'symbols': list(self._positions.keys()),
            'total_unrealized_pnl': self.get_total_unrealized_pnl(),
            'positions': {
                symbol: {
                    'entry_price': pos.entry_price,
                    'current_price': pos.current_price,
                    'quantity': pos.quantity,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'side': pos.side,
                }
                for symbol, pos in self._positions.items()
            }
        }
