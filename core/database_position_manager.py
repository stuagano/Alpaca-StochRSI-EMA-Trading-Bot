import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from utils.trade_store import TradeStore

logger = logging.getLogger(__name__)

class DatabasePositionManager:
    """
    Production-ready position manager that persists active positions 
    to the database and syncs with TradeStore.
    """
    def __init__(self, api, config):
        self.api = api
        self.config = config
        self.trade_store = TradeStore()
        
        # We still keep a small memory cache for fast access
        self.active_positions: Dict[str, Dict] = {}
        
        # Try to recover any active positions from the API on startup
        asyncio.create_task(self._sync_with_alpaca())

    async def _sync_with_alpaca(self):
        """Sync local state with Alpaca active positions."""
        try:
            positions = self.api.list_positions()
            for pos in positions:
                self.active_positions[pos.symbol] = {
                    'symbol': pos.symbol,
                    'qty': float(pos.qty),
                    'side': 'long' if pos.side == 'long' else 'short',
                    'entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'unrealized_pnl': float(pos.unrealized_pl),
                    'entry_time': datetime.now(), # Estimate or fetch from orders
                }
            logger.info(f"Synced {len(self.active_positions)} positions from Alpaca.")
        except Exception as e:
            logger.error(f"Failed to sync with Alpaca: {e}")

    async def add_position(self, symbol: str, qty: float, side: str, entry_price: float, strategy: str):
        """Record a new position and log it to TradeStore."""
        entry_time = datetime.now()
        
        # 1. Update memory cache
        self.active_positions[symbol] = {
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'entry_price': entry_price,
            'strategy': strategy,
            'entry_time': entry_time,
            'current_price': entry_price,
            'unrealized_pnl': 0.0
        }

        # 2. Persist to TradeStore (recorded as a partial trade or pending entry)
        try:
            self.trade_store.add_trade(
                symbol=symbol,
                action='BUY' if side == 'long' else 'SELL',
                qty=qty,
                price=entry_price,
                timestamp=entry_time.isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to record entry in TradeStore: {e}")
            
        return True

    async def close_position(self, symbol: str, exit_price: float, reason: str):
        """Close a position and log the exit to TradeStore."""
        if symbol in self.active_positions:
            pos = self.active_positions.pop(symbol)
            
            # Record the exit in TradeStore
            try:
                self.trade_store.add_trade(
                    symbol=symbol,
                    action='SELL' if pos['side'] == 'long' else 'BUY',
                    qty=pos['qty'],
                    price=exit_price,
                    timestamp=datetime.now().isoformat()
                )
            except Exception as e:
                logger.error(f"Failed to record exit in TradeStore: {e}")
                
            logger.info(f"Closed position {symbol} at {exit_price}. Reason: {reason}")
            return True
        return False

    async def get_all_positions(self) -> List[Dict]:
        """Return all active positions."""
        return list(self.active_positions.values())

    async def update_position_details(self, symbol: str, **updates):
        """Update fields for an active position."""
        if symbol in self.active_positions:
            self.active_positions[symbol].update(updates)
        return True
