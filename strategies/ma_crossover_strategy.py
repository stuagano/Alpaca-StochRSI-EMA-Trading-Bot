"""Compatibility shim for the legacy MACrossover strategy import."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from strategies.base_strategy import Strategy


class MACrossoverStrategy(Strategy):
    """
    Moving Average Crossover Strategy.
    Standard implementation using short and long period EMAs.
    """

    def __init__(self, config: Any) -> None:
        super().__init__(name="MACrossover")
        self.config = config
        
        # Extract params from config if available, else use defaults
        if hasattr(config, 'indicators') and hasattr(config.indicators, 'EMA'):
            ema_config = config.indicators.EMA
            self.short_period = getattr(ema_config, 'fast_period', 10)
            self.long_period = getattr(ema_config, 'slow_period', 20)
        else:
            self.short_period = 10
            self.long_period = 20
            
        self.parameters = {
            'short_period': self.short_period,
            'long_period': self.long_period
        }

    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate MA crossover signals using standardized signature."""
        if len(df) < self.long_period:
            return []

        # Calculate moving averages
        short_ma = df['close'].rolling(self.short_period).mean()
        long_ma = df['close'].rolling(self.long_period).mean()

        # Use base class helper for crossover detection
        crossover = self._detect_crossover(short_ma, long_ma)
        if not crossover:
            return []

        # Determine action and reason from crossover type
        if crossover == 'bullish':
            action = 'buy'
            reason = f'EMA Bullish Crossover ({self.short_period}/{self.long_period})'
        else:
            action = 'sell'
            reason = f'EMA Bearish Crossover ({self.short_period}/{self.long_period})'

        # Use base class helper for signal creation
        symbol = self._get_symbol_from_df(df)
        signal = self._create_signal_dict(
            symbol=symbol,
            action=action,
            confidence=0.75,
            price=df['close'].iloc[-1],
            timestamp=df.index[-1],
            reason=reason
        )

        return self._record_signal(signal)
