"""
Trading strategy constants and risk parameters.

Centralizes magic numbers to provide a single source of truth
for risk management and trading thresholds.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskParameters:
    """Default risk management parameters for trading strategies."""

    # Standard stop-loss and take-profit (balanced risk/reward)
    STOP_LOSS_DEFAULT: float = 0.015      # 1.5% stop loss
    TAKE_PROFIT_DEFAULT: float = 0.015    # 1.5% take profit
    TRAILING_STOP_DEFAULT: float = 0.01   # 1% trailing stop

    # Strong signal thresholds (tighter stops, higher targets)
    STRONG_SIGNAL_STOP_LOSS: float = 0.012    # 1.2% for strong signals
    STRONG_SIGNAL_TAKE_PROFIT: float = 0.02  # 2% for strong signals

    # Minimum thresholds
    MIN_PROFIT_TARGET: float = 0.01       # 1% minimum profit to exit
    MAX_DAILY_LOSS: float = 0.02          # 2% max daily loss

    # Spread and volatility
    MAX_SPREAD_DEFAULT: float = 0.01      # 1% max spread


@dataclass(frozen=True)
class PositionParameters:
    """Position sizing and management parameters."""

    MAX_CONCURRENT_POSITIONS: int = 5
    MAX_POSITION_SIZE_PCT: float = 0.10   # 10% of portfolio per position
    MIN_POSITION_VALUE: float = 10.0      # Minimum $10 position
    MAX_HOLD_TIME_SECONDS: int = 3600     # 1 hour max hold


@dataclass(frozen=True)
class ScannerParameters:
    """Market scanner thresholds."""

    MIN_24H_VOLUME: float = 100000        # $100k minimum volume
    TARGET_SYMBOL_COUNT: int = 50         # Number of symbols to track
    VOLATILITY_MIN: float = 0.001
    VOLATILITY_MAX: float = 0.01


# Default instances for easy import
RISK = RiskParameters()
POSITION = PositionParameters()
SCANNER = ScannerParameters()
