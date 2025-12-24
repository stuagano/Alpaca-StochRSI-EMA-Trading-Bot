"""
Shared utilities for trading strategies.

This module provides common utility functions to reduce code duplication
across strategy implementations.
"""

from strategies.utils.calculations import (
    calculate_position_pnl,
    calculate_pnl_percentage,
    calculate_target_price,
    calculate_stop_price,
    to_decimal,
)
from strategies.utils.signal_builder import SignalBuilder
from strategies.utils.indicators import (
    detect_crossover,
    calculate_ma,
    calculate_ema,
    get_crossover_values,
    calculate_rsi,
    calculate_atr,
)

__all__ = [
    # Calculations
    'calculate_position_pnl',
    'calculate_pnl_percentage',
    'calculate_target_price',
    'calculate_stop_price',
    'to_decimal',
    # Signal building
    'SignalBuilder',
    # Indicators
    'detect_crossover',
    'calculate_ma',
    'calculate_ema',
    'get_crossover_values',
    'calculate_rsi',
    'calculate_atr',
]
