"""
Main indicator module for crypto scalping bot
Imports optimized indicators for performance
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging
from indicators.optimized_indicators import (
    calculate_stoch_rsi_optimized,
    calculate_stochastic_optimized,
    calculate_ema_optimized,
    calculate_all_indicators_optimized,
    calculate_atr_optimized
)

logger = logging.getLogger(__name__)

class Indicator:
    """Technical indicator calculator for crypto scalping"""

    def __init__(self, data_fetcher=None):
        self.data_fetcher = data_fetcher
        self.logger = logger

    def calculate_indicators(self, df: pd.DataFrame, symbol: str = "BTCUSD") -> Dict[str, Any]:
        """
        Calculate all indicators for crypto scalping

        Args:
            df: DataFrame with OHLCV data
            symbol: Crypto symbol being analyzed

        Returns:
            Dict with all calculated indicators
        """
        try:
            # Calculate all indicators using optimized functions
            df_with_indicators = calculate_all_indicators_optimized(
                df,
                include_atr=True,
                include_stoch=True,
                include_stoch_rsi=True,
                include_dynamic_bands=False,  # Simplified for scalping
                atr={'period': 14},
                stoch={'period': 9, 'smooth_k': 3, 'smooth_d': 3},
                stoch_rsi={'rsi_period': 14, 'stoch_period': 9, 'k_period': 3, 'd_period': 3}
            )

            # Calculate fast EMA for scalping
            df_with_indicators['EMA'] = calculate_ema_optimized(df_with_indicators['close'], span=5)

            # Get latest values
            latest = df_with_indicators.iloc[-1] if not df_with_indicators.empty else {}

            return {
                'symbol': symbol,
                'stoch_rsi': {
                    'value': latest.get('StochRSI', 0),
                    'k': latest.get('StochRSI %K', 0),
                    'd': latest.get('StochRSI %D', 0)
                },
                'stochastic': {
                    'k': latest.get('Stoch %K', 0),
                    'd': latest.get('Stoch %D', 0)
                },
                'rsi': latest.get('RSI', 50),
                'ema': latest.get('EMA', 0),
                'atr': latest.get('ATR', 0),
                'price': latest.get('close', 0),
                'volume': latest.get('volume', 0)
            }

        except Exception as e:
            self.logger.error(f"Error calculating indicators for {symbol}: {e}")
            return self._get_default_indicators(symbol)

    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Compute RSI value from a price series."""
        if len(prices) < period + 1:
            return 50.0

        series = pd.Series(prices, dtype='float64')
        delta = series.diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)

        avg_gain = gains.rolling(window=period).mean()
        avg_loss = losses.rolling(window=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.dropna().empty else 50.0

    def _get_default_indicators(self, symbol: str) -> Dict[str, Any]:
        """Return default indicator values on error"""
        return {
            'symbol': symbol,
            'stoch_rsi': {'value': 50, 'k': 50, 'd': 50},
            'stochastic': {'k': 50, 'd': 50},
            'rsi': 50,
            'ema': 0,
            'atr': 0,
            'price': 0,
            'volume': 0
        }

    def get_trading_signal(self, indicators: Dict[str, Any]) -> str:
        """
        Generate trading signal based on indicators

        Returns:
            'BUY', 'SELL', or 'HOLD'
        """
        try:
            stoch_rsi_k = indicators['stoch_rsi']['k']
            stoch_rsi_d = indicators['stoch_rsi']['d']
            stoch_k = indicators['stochastic']['k']
            rsi = indicators['rsi']

            # Aggressive crypto scalping signals
            if stoch_rsi_k < 25 and stoch_k < 30 and rsi < 35:
                return 'BUY'
            elif stoch_rsi_k > 75 and stoch_k > 70 and rsi > 65:
                return 'SELL'
            else:
                return 'HOLD'

        except Exception as e:
            self.logger.error(f"Error generating signal: {e}")
            return 'HOLD'

# Maintain backwards compatibility
def calculate_indicators(df: pd.DataFrame, config: Optional[Dict] = None) -> pd.DataFrame:
    """
    Legacy function for calculating indicators

    Args:
        df: DataFrame with OHLCV data
        config: Optional configuration dict

    Returns:
        DataFrame with indicators added
    """
    return calculate_all_indicators_optimized(
        df,
        include_atr=True,
        include_stoch=True,
        include_stoch_rsi=True,
        include_dynamic_bands=False
    )
