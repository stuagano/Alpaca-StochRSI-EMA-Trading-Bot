#!/usr/bin/env python3
"""
Base Strategy Class for Epic 2 Backtesting
==========================================

Abstract base class for all trading strategies used in Epic 2 backtesting engine.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd


class Strategy(ABC):
    """Abstract base class for trading strategies"""

    def __init__(self, name: Optional[str] = None):
        """Initialize strategy"""
        self.name = name or self.__class__.__name__
        self.parameters = {}
        self.signals_history = []

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on a single DataFrame of OHLCV data

        Args:
            df: DataFrame with OHLCV data

        Returns:
            List of signal dictionaries with keys: symbol, action, confidence, etc.
        """
        pass

    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return self.parameters

    def set_parameters(self, parameters: Dict[str, Any]):
        """Set strategy parameters"""
        self.parameters.update(parameters)

    def get_signals_history(self) -> List[Dict[str, Any]]:
        """Get historical signals generated"""
        return self.signals_history

    def reset(self):
        """Reset strategy state"""
        self.signals_history = []

    # ============================================================
    # Helper methods to reduce duplication across strategies
    # ============================================================

    def _get_symbol_from_df(self, df: pd.DataFrame, default: str = 'UNKNOWN') -> str:
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

    def _create_signal_dict(
        self,
        symbol: str,
        action: str,
        confidence: float,
        price: float,
        timestamp: Any,
        reason: str,
        **extra_fields
    ) -> Dict[str, Any]:
        """
        Create a standardized signal dictionary.

        Eliminates duplicate signal dict creation across strategies.

        Args:
            symbol: Trading symbol
            action: 'buy', 'sell', or 'hold'
            confidence: Signal confidence (0.0 to 1.0)
            price: Current price
            timestamp: Signal timestamp
            reason: Human-readable reason for signal
            **extra_fields: Additional fields to include

        Returns:
            Signal dictionary
        """
        signal = {
            'symbol': symbol,
            'action': action.lower(),
            'confidence': max(0.0, min(1.0, confidence)),
            'price': price,
            'timestamp': timestamp,
            'strategy': self.name,
            'reason': reason,
        }
        signal.update(extra_fields)
        return signal

    def _detect_crossover(
        self,
        short_series: pd.Series,
        long_series: pd.Series
    ) -> Optional[str]:
        """
        Detect crossover between two series.

        Args:
            short_series: Faster/shorter period series
            long_series: Slower/longer period series

        Returns:
            'bullish' if short crosses above long,
            'bearish' if short crosses below long,
            None if no crossover detected
        """
        if len(short_series) < 2 or len(long_series) < 2:
            return None

        current_short = short_series.iloc[-1]
        current_long = long_series.iloc[-1]
        prev_short = short_series.iloc[-2]
        prev_long = long_series.iloc[-2]

        # Check for NaN values
        if pd.isna(current_short) or pd.isna(current_long):
            return None
        if pd.isna(prev_short) or pd.isna(prev_long):
            return None

        # Bullish crossover
        if prev_short <= prev_long and current_short > current_long:
            return 'bullish'

        # Bearish crossover
        if prev_short >= prev_long and current_short < current_long:
            return 'bearish'

        return None

    def _record_signal(self, signal: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Record signal to history and return as list.

        Args:
            signal: Signal dictionary to record

        Returns:
            List containing the signal
        """
        self.signals_history.append(signal)
        return [signal]


# Alias for backward compatibility
BaseStrategy = Strategy


class SimpleMovingAverageStrategy(Strategy):
    """Simple Moving Average Crossover Strategy for testing"""

    def __init__(self, short_period: int = 10, long_period: int = 20):
        super().__init__("Simple MA Crossover")
        self.short_period = short_period
        self.long_period = long_period
        self.parameters = {
            'short_period': short_period,
            'long_period': long_period
        }

    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate MA crossover signals"""
        signals = []

        if len(df) < self.long_period:
            return []

        # Extract symbol if available, else default
        symbol = df['symbol'].iloc[-1] if 'symbol' in df.columns else 'UNKNOWN'
        timestamp = df.index[-1]

        # Calculate moving averages
        short_ma = df['close'].rolling(self.short_period).mean()
        long_ma = df['close'].rolling(self.long_period).mean()

        # Get current values
        current_short = short_ma.iloc[-1]
        current_long = long_ma.iloc[-1]
        prev_short = short_ma.iloc[-2] if len(short_ma) > 1 else current_short
        prev_long = long_ma.iloc[-2] if len(long_ma) > 1 else current_long

        # Detect crossover
        signal = None
        if prev_short <= prev_long and current_short > current_long:
            signal = {
                'symbol': symbol,
                'action': 'buy',
                'confidence': 0.7,
                'price': df['close'].iloc[-1],
                'timestamp': timestamp,
                'strategy': self.name,
                'reason': 'MA bullish crossover'
            }
        elif prev_short >= prev_long and current_short < current_long:
            signal = {
                'symbol': symbol,
                'action': 'sell',
                'confidence': 0.7,
                'price': df['close'].iloc[-1],
                'timestamp': timestamp,
                'strategy': self.name,
                'reason': 'MA bearish crossover'
            }

        if signal:
            signals.append(signal)
            self.signals_history.append(signal)

        return signals


def get_strategy_by_name(name: str, **kwargs) -> Strategy:
    """Factory function to get strategy by name"""
    strategies = {
        'ma_crossover': SimpleMovingAverageStrategy,
        'simple_ma': SimpleMovingAverageStrategy,
    }

    strategy_class = strategies.get(name.lower())
    if strategy_class:
        return strategy_class(**kwargs)
    else:
        # Default to simple MA strategy
        return SimpleMovingAverageStrategy(**kwargs)
