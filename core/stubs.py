import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class TradingDataServiceStub:
    """Simple data service stub to replace backend dependency"""
    def __init__(self):
        pass

    def get_market_data(self, symbol: str) -> pd.DataFrame:
        """Get market data for symbol as a DataFrame"""
        # Return a small mock DataFrame to allow strategies to run
        data = {
            'open': [30000.0, 30100.0, 30050.0],
            'high': [30200.0, 30150.0, 30100.0],
            'low': [29900.0, 30000.0, 30000.0],
            'close': [30100.0, 30050.0, 30100.0],
            'volume': [100, 150, 120],
            'symbol': [symbol, symbol, symbol]
        }
        df = pd.DataFrame(data)
        df.index = pd.date_range(end=datetime.now(), periods=3, freq='1min')
        return df


class PositionManagerStub:
    """Simple position manager stub to replace backend dependency"""
    def __init__(self, api, config):
        self.api = api
        self.config = config
        self.positions = {}

    async def add_position(self, symbol, qty, side, entry_price, strategy):
        """Add a position to tracking"""
        entry_time = datetime.utcnow()
        self.positions[symbol] = {
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'entry_price': entry_price,
            'strategy': strategy,
            'entry_time': entry_time,
            'current_price': entry_price,
            'market_value': entry_price * qty,
            'unrealized_pnl': 0.0,
            'unrealized_pnl_pct': 0.0,
            'stop_loss': None,
            'take_profit': None,
            'is_profitable': False
        }
        return True

    async def update_position_details(self, symbol, **updates):
        """Update tracked position fields."""
        if symbol in self.positions:
            self.positions[symbol].update(updates)
        return True

    async def get_all_positions(self):
        """Get all tracked positions"""
        return list(self.positions.values())

    async def check_stop_losses(self):
        """Check for stop loss triggers"""
        return []

    async def check_take_profits(self):
        """Check for take profit triggers"""
        return []

    async def close_position(self, symbol, exit_price, reason):
        """Close a position"""
        if symbol in self.positions:
            del self.positions[symbol]
        return True
