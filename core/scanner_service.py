"""
Centralized Scanner Service - singleton via ServiceRegistry.

This service provides a single, shared scanner instance for all components
that need market data indicators and signals. It eliminates the issue of
multiple isolated scanner instances with different state.

Usage:
    from core.service_registry import get_service_registry
    scanner = get_service_registry().get('scanner_service')
    indicators = scanner.get_indicators('BTCUSD')
"""

import threading
import logging
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from config.unified_config import CryptoScannerConfig

# Import CryptoSignal for signal generation
try:
    from strategies.crypto_scalping_strategy import CryptoSignal
except ImportError:
    CryptoSignal = None

# Import RISK constants
try:
    from strategies.constants import RISK
except ImportError:
    # Fallback defaults
    class RISK:
        TAKE_PROFIT_DEFAULT = 0.015
        STOP_LOSS_DEFAULT = 0.015
        STRONG_SIGNAL_TAKE_PROFIT = 0.02
        STRONG_SIGNAL_STOP_LOSS = 0.012

logger = logging.getLogger(__name__)


class ScannerService:
    """Centralized market data scanner - singleton via ServiceRegistry.

    This service manages all price/volume data and indicator calculations
    in one place, ensuring consistency across all components.
    """

    # Default crypto pairs
    DEFAULT_PAIRS = [
        'BTCUSD', 'ETHUSD', 'SOLUSD', 'DOGEUSD', 'LTCUSD',
        'AVAXUSD', 'LINKUSD', 'UNIUSD', 'XRPUSD', 'DOTUSD',
        'MATICUSD', 'ADAUSD', 'ALGOUSD', 'ATOMUSD', 'BCHUSD'
    ]

    def __init__(
        self,
        config: Optional[CryptoScannerConfig] = None,
        enabled_symbols: Optional[List[str]] = None,
    ):
        """Initialize the scanner service.

        Args:
            config: Optional scanner configuration
            enabled_symbols: Optional list of symbols to track
        """
        self.config = config
        self.lock = threading.Lock()

        # Market data storage
        self.price_data: Dict[str, List[float]] = {}
        self.volume_data: Dict[str, List[float]] = {}
        self.volatility_data: Dict[str, float] = {}

        # Symbol management
        self.default_pairs = list(self.DEFAULT_PAIRS)
        self.enabled_trading_symbols: Set[str] = set()
        self.high_volume_pairs: List[str] = []

        # Initialize symbols
        initial_symbols = enabled_symbols or []
        merged = self._merge_symbol_lists(self.default_pairs, initial_symbols)
        self.high_volume_pairs = merged
        self.enabled_trading_symbols = set(merged)

        # Configuration thresholds
        self.min_volatility = config.min_volatility if config else 0.005
        self.max_spread = config.max_spread if config and hasattr(config, 'max_spread') else 0.01
        self.min_24h_volume = config.min_24h_volume if config and hasattr(config, 'min_24h_volume') else 100000

        logger.info(
            "ScannerService initialized with %d symbols",
            len(self.high_volume_pairs)
        )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normalize symbols to scanner format (e.g., BTC/USD -> BTCUSD)."""
        return symbol.replace("/", "").upper()

    @classmethod
    def _merge_symbol_lists(
        cls,
        defaults: List[str],
        overrides: List[str],
    ) -> List[str]:
        """Combine default and override symbols while preserving order."""
        merged: List[str] = []
        seen: Set[str] = set()

        for raw_symbol in list(defaults) + list(overrides):
            if not raw_symbol:
                continue
            normalized = cls._normalize_symbol(raw_symbol)
            if normalized not in seen:
                merged.append(normalized)
                seen.add(normalized)

        return merged

    def update_enabled_symbols(
        self,
        enabled_symbols: List[str],
        *,
        merge_with_defaults: bool = True,
    ) -> None:
        """Update the list of symbols enabled for trading."""
        with self.lock:
            base = self.default_pairs if merge_with_defaults else []
            merged = self._merge_symbol_lists(base, enabled_symbols)
            self.enabled_trading_symbols = set(merged)
            self.high_volume_pairs = merged
            logger.info(
                "Updated enabled trading symbols: %d total",
                len(self.enabled_trading_symbols)
            )

    def get_enabled_symbols(self) -> List[str]:
        """Get list of currently enabled trading symbols."""
        with self.lock:
            return list(self.high_volume_pairs)

    def update_market_data(self, symbol: str, price: float, volume: float) -> None:
        """Thread-safe update of price/volume data for a symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSD')
            price: Current price
            volume: Current volume
        """
        with self.lock:
            if symbol not in self.price_data:
                self.price_data[symbol] = []
                self.volume_data[symbol] = []

            self.price_data[symbol].append(price)
            self.volume_data[symbol].append(volume)

            # Keep only recent data (1000 points ≈ 16-17 hours of 1-min data)
            if len(self.price_data[symbol]) > 1000:
                self.price_data[symbol] = self.price_data[symbol][-1000:]
                self.volume_data[symbol] = self.volume_data[symbol][-1000:]

    def bulk_load(self, symbol: str, df: pd.DataFrame) -> None:
        """Load full DataFrame for a symbol (for initialization).

        Args:
            symbol: Trading pair symbol
            df: DataFrame with 'close' and optionally 'volume' columns
        """
        if df.empty:
            return

        with self.lock:
            if symbol not in self.price_data:
                self.price_data[symbol] = []
                self.volume_data[symbol] = []

            for idx in range(len(df)):
                price = float(df['close'].iloc[idx])
                volume = float(df['volume'].iloc[idx]) if 'volume' in df.columns else 0
                self.price_data[symbol].append(price)
                self.volume_data[symbol].append(volume)

            # Trim to max size
            if len(self.price_data[symbol]) > 1000:
                self.price_data[symbol] = self.price_data[symbol][-1000:]
                self.volume_data[symbol] = self.volume_data[symbol][-1000:]

        logger.debug("Bulk loaded %d bars for %s", len(df), symbol)

    def get_data_length(self, symbol: str) -> int:
        """Get the number of data points available for a symbol."""
        with self.lock:
            return len(self.price_data.get(symbol, []))

    def has_sufficient_data(self, symbol: str, min_points: int = 26) -> bool:
        """Check if symbol has sufficient data for indicator calculation."""
        return self.get_data_length(symbol) >= min_points

    # =========================================================================
    # Indicator Calculations
    # =========================================================================

    def calculate_volatility(self, prices: List[float], window: int = 20) -> float:
        """Calculate price volatility using standard deviation."""
        actual_window = min(window, len(prices))
        if actual_window < 3:
            return 0.0
        returns = np.diff(np.log(prices[-actual_window:]))
        return float(np.std(returns) * np.sqrt(1440))  # Annualized for 1-min data

    def calculate_momentum(self, prices: List[float], period: int = 14) -> float:
        """Calculate price momentum using RSI-like indicator."""
        if len(prices) < period + 1:
            return 0.5
        changes = np.diff(prices[-period-1:])
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, -changes, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 1.0
        rs = avg_gain / avg_loss
        return float(rs / (1 + rs))

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index) - 0-100 scale."""
        if len(prices) < period + 1:
            return 50.0
        changes = np.diff(prices[-period-1:])
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, -changes, 0)
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        if avg_loss == 0:
            return 100.0
        if avg_gain == 0:
            return 0.0
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        multiplier = 2 / (period + 1)
        ema = prices[-period]
        for price in prices[-period+1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return float(ema)

    def calculate_macd(self, prices: List[float]) -> tuple:
        """Calculate MACD (12, 26, 9) - returns (macd_line, signal_line, histogram)."""
        if len(prices) < 26:
            return 0.0, 0.0, 0.0
        ema_12 = self.calculate_ema(prices, 12)
        ema_26 = self.calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        signal_line = macd_line * 0.9  # Approximation
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def calculate_stoch_rsi(self, prices: List[float], rsi_period: int = 14, stoch_period: int = 14) -> tuple:
        """Calculate Stochastic RSI - returns (K, D)."""
        if len(prices) < rsi_period + stoch_period:
            return 50.0, 50.0
        rsi_values = []
        for i in range(stoch_period):
            end_idx = len(prices) - stoch_period + i + 1
            rsi = self.calculate_rsi(prices[:end_idx], rsi_period)
            rsi_values.append(rsi)
        if not rsi_values:
            return 50.0, 50.0
        current_rsi = rsi_values[-1]
        min_rsi = min(rsi_values)
        max_rsi = max(rsi_values)
        if max_rsi == min_rsi:
            stoch_k = 50.0
        else:
            stoch_k = ((current_rsi - min_rsi) / (max_rsi - min_rsi)) * 100
        stoch_d = stoch_k  # Simplified
        return stoch_k, stoch_d

    def detect_volume_surge(self, volumes: List[float], window: int = 10) -> bool:
        """Detect if current volume is significantly higher than average."""
        if len(volumes) < window + 1:
            return False
        recent_avg = np.mean(volumes[-window-1:-1])
        current_volume = volumes[-1]
        return bool(current_volume > recent_avg * 1.1)

    def get_indicators(self, symbol: str) -> Dict[str, Any]:
        """Get all indicators for a symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary of indicator values, or empty dict if insufficient data
        """
        with self.lock:
            if symbol not in self.price_data or len(self.price_data[symbol]) < 26:
                return {}

            prices = self.price_data[symbol]
            volumes = self.volume_data.get(symbol, [])

            rsi = self.calculate_rsi(prices)
            macd_line, signal_line, histogram = self.calculate_macd(prices)
            stoch_k, stoch_d = self.calculate_stoch_rsi(prices)
            ema_9 = self.calculate_ema(prices, 9)
            ema_21 = self.calculate_ema(prices, 21)
            volatility = self.calculate_volatility(prices)
            volume_surge = self.detect_volume_surge(volumes)

            return {
                'price': prices[-1],
                'rsi': rsi,
                'macd': macd_line,
                'macd_signal': signal_line,
                'macd_histogram': histogram,
                'stoch_k': stoch_k,
                'stoch_d': stoch_d,
                'ema_9': ema_9,
                'ema_21': ema_21,
                'ema_cross': 'bullish' if ema_9 > ema_21 else 'bearish',
                'volatility': volatility,
                'volume_surge': volume_surge,
                'data_points': len(prices),
            }

    def get_all_indicators(self) -> Dict[str, Dict[str, Any]]:
        """Get indicators for all tracked symbols.

        Returns:
            Dictionary mapping symbols to their indicator dictionaries
        """
        result = {}
        symbols = self.get_enabled_symbols()
        for symbol in symbols:
            indicators = self.get_indicators(symbol)
            if indicators:
                result[symbol] = indicators
        return result

    def _generate_signal(
        self,
        symbol: str,
        price: float,
        volatility: float,
        volume_surge: bool,
        momentum: float,
    ) -> Optional[Any]:
        """Generate trading signal - CONSERVATIVE MODE - only trade on strong signals.

        This method provides interface compatibility with CryptoVolatilityScanner.

        Args:
            symbol: Trading pair symbol
            price: Current price
            volatility: Current volatility
            volume_surge: Whether there's a volume surge
            momentum: Current momentum value

        Returns:
            CryptoSignal if conditions are met, None otherwise
        """
        if CryptoSignal is None:
            logger.warning("CryptoSignal not available - cannot generate signals")
            return None

        # Get full indicator set
        indicators = self.get_indicators(symbol)
        if not indicators:
            logger.debug(f"    ⏳ {symbol}: Waiting for indicators (need more data)")
            return None

        rsi = indicators.get('rsi', 50)
        macd = indicators.get('macd', 0)
        macd_hist = indicators.get('macd_histogram', 0)
        stoch_k = indicators.get('stoch_k', 50)
        ema_cross = indicators.get('ema_cross', 'neutral')

        action = 'hold'
        confidence = 0.0
        target_profit = RISK.TAKE_PROFIT_DEFAULT
        stop_loss = RISK.STOP_LOSS_DEFAULT
        signal_reasons = []

        # ============ BUY SIGNALS (CONSERVATIVE - need strong oversold) ============
        buy_score = 0

        if rsi < 25:
            buy_score += 3
            signal_reasons.append(f"RSI very low ({rsi:.1f})")
        elif rsi < 30:
            buy_score += 2
            signal_reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi < 35:
            buy_score += 1
            signal_reasons.append(f"RSI low ({rsi:.1f})")

        if macd_hist > 0:
            buy_score += 1
            signal_reasons.append("MACD positive")

        if stoch_k < 20:
            buy_score += 3
            signal_reasons.append(f"StochRSI very low ({stoch_k:.1f})")
        elif stoch_k < 30:
            buy_score += 2
            signal_reasons.append(f"StochRSI oversold ({stoch_k:.1f})")

        if ema_cross == 'bullish':
            buy_score += 2
            signal_reasons.append("EMA bullish cross")

        if volume_surge:
            buy_score += 1
            signal_reasons.append("Volume confirmation")

        # ============ SELL SIGNALS (CONSERVATIVE - need strong overbought) ============
        sell_score = 0
        sell_reasons = []

        if rsi > 75:
            sell_score += 3
            sell_reasons.append(f"RSI very high ({rsi:.1f})")
        elif rsi > 70:
            sell_score += 2
            sell_reasons.append(f"RSI overbought ({rsi:.1f})")
        elif rsi > 65:
            sell_score += 1
            sell_reasons.append(f"RSI high ({rsi:.1f})")

        if macd_hist < 0:
            sell_score += 1
            sell_reasons.append("MACD negative")

        if stoch_k > 80:
            sell_score += 3
            sell_reasons.append(f"StochRSI very high ({stoch_k:.1f})")
        elif stoch_k > 70:
            sell_score += 2
            sell_reasons.append(f"StochRSI overbought ({stoch_k:.1f})")

        if ema_cross == 'bearish':
            sell_score += 2
            sell_reasons.append("EMA bearish cross")

        if volume_surge:
            sell_score += 1
            sell_reasons.append("Volume confirmation")

        # ============ DETERMINE ACTION (REQUIRE STRONG SIGNALS) ============
        min_score = 3

        if buy_score >= min_score and buy_score > sell_score:
            action = 'buy'
            confidence = min(0.95, 0.5 + (buy_score * 0.1))
            if buy_score >= 5:
                target_profit = RISK.STRONG_SIGNAL_TAKE_PROFIT
                stop_loss = RISK.STRONG_SIGNAL_STOP_LOSS
            logger.info(f"    📈 BUY: score={buy_score} | {', '.join(signal_reasons)}")

        elif sell_score >= min_score and sell_score > buy_score:
            action = 'sell'
            confidence = min(0.95, 0.5 + (sell_score * 0.1))
            signal_reasons = sell_reasons
            if sell_score >= 5:
                target_profit = RISK.STRONG_SIGNAL_TAKE_PROFIT
                stop_loss = RISK.STRONG_SIGNAL_STOP_LOSS
            logger.info(f"    📉 SELL: score={sell_score} | {', '.join(sell_reasons)}")

        else:
            logger.debug(
                f"    ⏸️ {symbol}: No signal (buy={buy_score}, sell={sell_score}, need {min_score})"
            )
            return None

        # Create the signal only with sufficient confidence
        if action != 'hold' and confidence >= 0.6:
            return CryptoSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                price=price,
                volatility=volatility,
                volume_surge=volume_surge,
                momentum=momentum,
                target_profit=target_profit,
                stop_loss=stop_loss,
                timestamp=datetime.now(),
            )

        return None

    def get_status(self) -> Dict[str, Any]:
        """Return scanner health/status for monitoring."""
        with self.lock:
            symbols_with_data = [s for s in self.high_volume_pairs if s in self.price_data]
            symbols_sufficient = [s for s in symbols_with_data if len(self.price_data[s]) >= 26]

            return {
                'enabled_symbols': len(self.high_volume_pairs),
                'symbols_with_data': len(symbols_with_data),
                'symbols_with_sufficient_data': len(symbols_sufficient),
                'total_data_points': sum(len(v) for v in self.price_data.values()),
                'symbols': {
                    symbol: {
                        'data_points': len(self.price_data.get(symbol, [])),
                        'has_sufficient_data': len(self.price_data.get(symbol, [])) >= 26,
                    }
                    for symbol in self.high_volume_pairs[:10]  # Top 10 for brevity
                }
            }


# Module-level singleton access (for convenience)
_scanner_service: Optional[ScannerService] = None


def get_scanner_service() -> Optional[ScannerService]:
    """Get the scanner service from the service registry.

    Returns:
        ScannerService instance or None if not registered
    """
    try:
        from core.service_registry import get_service_registry
        return get_service_registry().get('scanner_service')
    except (ImportError, ValueError):
        return None
