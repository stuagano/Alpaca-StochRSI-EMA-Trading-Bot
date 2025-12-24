"""
Signal builder utility for creating consistent trading signals.

Provides a fluent interface for building signal dictionaries with
all required fields.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import pandas as pd


class SignalBuilder:
    """
    Builder class for creating trading signal dictionaries.

    Eliminates duplicate signal creation code across strategies.

    Usage:
        signal = (SignalBuilder()
            .symbol("BTCUSD")
            .action("buy")
            .confidence(0.85)
            .price(45000.0)
            .reason("RSI oversold")
            .build())
    """

    def __init__(self):
        self._signal: Dict[str, Any] = {
            'symbol': 'UNKNOWN',
            'action': 'hold',
            'confidence': 0.5,
            'price': 0.0,
            'timestamp': datetime.now(),
            'strategy': 'Unknown',
            'reason': '',
        }
        self._indicators: Dict[str, Any] = {}

    def symbol(self, symbol: str) -> 'SignalBuilder':
        """Set the trading symbol."""
        self._signal['symbol'] = symbol
        return self

    def action(self, action: str) -> 'SignalBuilder':
        """Set the action (buy/sell/hold)."""
        self._signal['action'] = action.lower()
        return self

    def confidence(self, confidence: float) -> 'SignalBuilder':
        """Set the signal confidence (0.0 to 1.0)."""
        self._signal['confidence'] = max(0.0, min(1.0, confidence))
        return self

    def price(self, price: float) -> 'SignalBuilder':
        """Set the current price."""
        self._signal['price'] = price
        return self

    def timestamp(self, timestamp: Any) -> 'SignalBuilder':
        """Set the signal timestamp."""
        self._signal['timestamp'] = timestamp
        return self

    def strategy(self, strategy_name: str) -> 'SignalBuilder':
        """Set the strategy name."""
        self._signal['strategy'] = strategy_name
        return self

    def reason(self, reason: str) -> 'SignalBuilder':
        """Set the signal reason/description."""
        self._signal['reason'] = reason
        return self

    def indicator(self, name: str, value: Any) -> 'SignalBuilder':
        """Add an indicator value to the signal."""
        self._indicators[name] = value
        return self

    def indicators(self, indicators: Dict[str, Any]) -> 'SignalBuilder':
        """Add multiple indicators at once."""
        self._indicators.update(indicators)
        return self

    def extra(self, key: str, value: Any) -> 'SignalBuilder':
        """Add an extra field to the signal."""
        self._signal[key] = value
        return self

    def from_dataframe(self, df: pd.DataFrame) -> 'SignalBuilder':
        """
        Extract common fields from a DataFrame.

        Sets symbol, price, and timestamp from the last row.
        """
        if len(df) == 0:
            return self

        # Extract symbol
        if 'symbol' in df.columns:
            self._signal['symbol'] = df['symbol'].iloc[-1]

        # Extract price
        if 'close' in df.columns:
            self._signal['price'] = float(df['close'].iloc[-1])

        # Extract timestamp
        self._signal['timestamp'] = df.index[-1]

        return self

    def build(self) -> Dict[str, Any]:
        """
        Build and return the signal dictionary.

        Returns:
            Complete signal dictionary with all fields
        """
        signal = self._signal.copy()

        if self._indicators:
            signal['indicators'] = self._indicators.copy()

        return signal

    @staticmethod
    def get_symbol_from_df(df: pd.DataFrame, default: str = 'UNKNOWN') -> str:
        """
        Extract symbol from DataFrame.

        Args:
            df: DataFrame with potential 'symbol' column
            default: Default symbol if not found

        Returns:
            Symbol string
        """
        if 'symbol' in df.columns and len(df) > 0:
            return str(df['symbol'].iloc[-1])
        return default
