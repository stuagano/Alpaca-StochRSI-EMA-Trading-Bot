"""
Common technical indicator utilities.

Provides shared indicator calculation and detection functions
to reduce duplication across strategies.
"""

from typing import Optional, Tuple
import pandas as pd


def detect_crossover(
    short_series: pd.Series,
    long_series: pd.Series
) -> Optional[str]:
    """
    Detect crossover between two series (e.g., moving averages).

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

    # Bullish crossover: short crosses above long
    if prev_short <= prev_long and current_short > current_long:
        return 'bullish'

    # Bearish crossover: short crosses below long
    if prev_short >= prev_long and current_short < current_long:
        return 'bearish'

    return None


def calculate_ma(
    series: pd.Series,
    period: int,
    ma_type: str = 'sma'
) -> pd.Series:
    """
    Calculate moving average of a series.

    Args:
        series: Price series (typically close prices)
        period: Moving average period
        ma_type: Type of MA ('sma' or 'ema')

    Returns:
        Moving average series
    """
    if ma_type.lower() == 'ema':
        return series.ewm(span=period, adjust=False).mean()
    else:  # Default to SMA
        return series.rolling(window=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate exponential moving average.

    Args:
        series: Price series
        period: EMA period

    Returns:
        EMA series
    """
    return series.ewm(span=period, adjust=False).mean()


def get_crossover_values(
    short_series: pd.Series,
    long_series: pd.Series
) -> Tuple[float, float, float, float]:
    """
    Get current and previous values for crossover detection.

    Args:
        short_series: Faster/shorter period series
        long_series: Slower/longer period series

    Returns:
        Tuple of (current_short, current_long, prev_short, prev_long)
    """
    current_short = short_series.iloc[-1]
    current_long = long_series.iloc[-1]
    prev_short = short_series.iloc[-2] if len(short_series) > 1 else current_short
    prev_long = long_series.iloc[-2] if len(long_series) > 1 else current_long

    return current_short, current_long, prev_short, prev_long


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.

    Args:
        series: Price series (typically close prices)
        period: RSI period (default 14)

    Returns:
        RSI series (0-100 range)
    """
    delta = series.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Calculate Average True Range.

    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ATR period (default 14)

    Returns:
        ATR series
    """
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = true_range.ewm(span=period, adjust=False).mean()

    return atr
