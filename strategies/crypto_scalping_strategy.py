"""
High-Frequency Crypto Day Trading Strategy
Focuses on volatility, quick gains, and rapid position turnover
WITH COMPREHENSIVE ERROR HANDLING AND TRADE LOGGING
"""

import numpy as np
import pandas as pd
import asyncio
import websocket
import json
import threading
import math
import time
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor
import logging
from threading import Lock, RLock
from enum import Enum
from alpaca.common.exceptions import APIError

from utils.trade_store import TradeStore
from config.unified_config import CryptoScannerConfig, TradingConfig
from strategies.trading_metrics import TradeLog  # Import instead of duplicate
from strategies.constants import RISK, POSITION, SCANNER
from strategies.trade_learner import get_trade_learner


# Activity logger for dashboard stream-of-consciousness view
# Uses callback pattern to avoid circular imports with main.py
_activity_log_callback = None


def register_activity_logger(callback):
    """Register a callback function for activity logging (called by main.py)."""
    global _activity_log_callback
    _activity_log_callback = callback


class _ActivityLogger:
    """Logs bot activity to dashboard via registered callback."""

    def _log(self, message: str, level: str = "info", symbol: str = None):
        if _activity_log_callback:
            _activity_log_callback(message, level, symbol)

    def log_scan_start(self, symbol_count: int):
        self._log(f"🔍 Scanning {symbol_count} symbols...")

    def log_scan_complete(self, signal_count: int, rejected_count: int = 0):
        """Log scan completion with signal summary"""
        if signal_count > 0:
            self._log(f"✅ Scan complete: {signal_count} signals found, {rejected_count} rejected")
        else:
            self._log(f"⏸️ Scan complete: No signals, {rejected_count} rejected")

    def log_signal(self, symbol: str, action: str, confidence: float, price: float,
                   reason: str = "", accepted: bool = False):
        if accepted:
            self._log(f"✅ {action.upper()} signal @ ${price:.4f} (conf: {confidence:.0%})", "success", symbol)
        else:
            self._log(f"⏭️ {action.upper()} skipped - {reason}", "info", symbol)

    def log_analysis(self, symbol: str, message: str):
        self._log(message, "debug", symbol)

    def log_decision(self, symbol: str, decision: str, reason: str, details: dict = None):
        """Log a trading decision (SKIP, WAIT, etc.)"""
        self._log(f"⚖️ {decision}: {reason}", "info", symbol)

    def log_rejection(self, symbol: str, reason: str, details: dict = None):
        self._log(f"❌ Rejected - {reason}", "info", symbol)

    def log_order_submit(self, symbol: str, side: str, qty: float, price: float):
        """Log when an order is being submitted"""
        emoji = "📤"
        self._log(f"{emoji} Submitting {side.upper()} order: {qty:.6f} @ ${price:.4f}", "info", symbol)

    def log_order_filled(self, symbol: str, side: str, qty: float, price: float):
        """Log when an order is filled"""
        emoji = "🟢" if side.lower() == "buy" else "🔴"
        self._log(f"{emoji} FILLED: {side.upper()} {qty:.6f} @ ${price:.4f}", "trade", symbol)

    def log_trade(self, symbol: str, side: str, qty: float, price: float, reason: str = ""):
        """Log a completed trade entry"""
        emoji = "🟢" if side.lower() == "buy" else "🔴"
        msg = f"{emoji} ENTERED: {side.upper()} {qty:.6f} @ ${price:.4f}"
        if reason:
            msg += f" - {reason}"
        self._log(msg, "trade", symbol)

    def log_holding(self, symbol: str, entry_price: float, current_price: float, pnl_pct: float):
        """Log position status while holding"""
        emoji = "📈" if pnl_pct >= 0 else "📉"
        self._log(f"{emoji} Holding @ ${current_price:.4f} (entry: ${entry_price:.4f}, P&L: {pnl_pct:+.2%})", "debug", symbol)

    def log_position_update(self, symbol: str, entry_price: float, current_price: float,
                           pnl_pct: float, stop_price: float, target_price: float):
        """Log position monitoring status"""
        emoji = "📈" if pnl_pct >= 0 else "📉"
        self._log(
            f"{emoji} Position: ${current_price:.2f} (entry: ${entry_price:.2f}, P&L: {pnl_pct:+.2%})",
            "debug",
            symbol,
        )

    def log_exit_trigger(self, symbol: str, reason: str, pnl_pct: float):
        """Log when exit conditions are triggered"""
        emoji = "🎯" if pnl_pct >= 0 else "🛑"
        self._log(f"{emoji} Exit triggered: {reason} (P&L: {pnl_pct:+.2%})", "info", symbol)

    def log_exit(self, symbol: str, reason: str, pnl: float, pnl_pct: float = 0):
        """Log completed exit with realized P&L"""
        emoji = "💰" if pnl >= 0 else "📉"
        self._log(f"{emoji} CLOSED: {reason} | P&L: ${pnl:+.2f} ({pnl_pct:+.2%})", "trade", symbol)


_activity_instance = _ActivityLogger()


def _get_activity():
    return _activity_instance


try:
    from prometheus_client import Counter, Gauge  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Counter = Gauge = None  # type: ignore[assignment]


SCANNER_SCAN_METRIC_NAME = "crypto_scanner_scans_total"
SCANNER_ERROR_METRIC_NAME = "crypto_scanner_errors_total"
SCANNER_TRACKED_SYMBOLS_METRIC_NAME = "crypto_scanner_tracked_pairs"
SCANNER_SIGNALS_METRIC_NAME = "crypto_scanner_signals_last"
SCANNER_LAST_RUN_METRIC_NAME = "crypto_scanner_last_run_timestamp"

SCANNER_SCAN_COUNTER = (
    Counter(
        SCANNER_SCAN_METRIC_NAME,
        "Total number of crypto scanner runs",
    )
    if Counter
    else None
)

SCANNER_ERROR_COUNTER = (
    Counter(
        SCANNER_ERROR_METRIC_NAME,
        "Total number of crypto scanner errors",
    )
    if Counter
    else None
)

SCANNER_TRACKED_SYMBOLS_GAUGE = (
    Gauge(
        SCANNER_TRACKED_SYMBOLS_METRIC_NAME,
        "Number of symbols currently tracked by the crypto scanner",
    )
    if Gauge
    else None
)

SCANNER_SIGNALS_GAUGE = (
    Gauge(
        SCANNER_SIGNALS_METRIC_NAME,
        "Number of signals generated by the most recent crypto scan",
    )
    if Gauge
    else None
)

SCANNER_LAST_RUN_GAUGE = (
    Gauge(
        SCANNER_LAST_RUN_METRIC_NAME,
        "Unix timestamp of the most recent crypto scanner run",
    )
    if Gauge
    else None
)


def _metric_inc(metric: Optional[Counter], amount: float = 1.0) -> None:
    """Increase a Prometheus counter when available."""

    if metric is None:
        return

    try:
        metric.inc(amount)
    except (RuntimeError, TypeError, ValueError):  # pragma: no cover - defensive guard
        logging.getLogger(__name__).debug("Failed to increment metric", exc_info=True)


def _metric_set(metric: Optional[Gauge], value: float) -> None:
    """Set a Prometheus gauge when available."""

    if metric is None:
        return

    try:
        metric.set(value)
    except (RuntimeError, TypeError, ValueError):  # pragma: no cover - defensive guard
        logging.getLogger(__name__).debug("Failed to set metric", exc_info=True)


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class CryptoSignal:
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    confidence: float
    price: float
    volatility: float
    volume_surge: bool
    momentum: float
    target_profit: float
    stop_loss: float
    timestamp: datetime
    signal_reasons: list = None  # List of reasons for the signal


class CryptoVolatilityScanner:
    """Scans for high volatility crypto pairs suitable for day trading"""

    def __init__(
        self,
        config: Optional[CryptoScannerConfig] = None,
        enabled_symbols: Optional[List[str]] = None,
    ):
        self.config = config
        self.lock = threading.RLock()  # Use RLock to allow reentrant locking

        # Use config if available, otherwise defaults
        self.target_count = (
            config.target_count if config and hasattr(config, "target_count") else 50
        )
        self.max_spread = (
            config.max_spread
            if config and hasattr(config, "max_spread")
            else RISK.MAX_SPREAD_DEFAULT
        )
        self.min_volume = (
            config.min_24h_volume
            if config and hasattr(config, "min_24h_volume")
            else 100000
        )

        # Define base pairs - EXPANDED list of quality crypto assets
        self.default_pairs = [
            # Major pairs (always include)
            "BTCUSD",
            "ETHUSD",
            "SOLUSD",
            "XRPUSD",
            "DOGEUSD",
            # Layer 1s
            "AVAXUSD",
            "ADAUSD",
            "DOTUSD",
            "ATOMUSD",
            "NEARUSD",
            "ALGOUSD",
            "FTMUSD",
            "MANAUSD",
            "SANDUSD",
            # DeFi
            "LINKUSD",
            "UNIUSD",
            "AABORUSD",
            "MKRUSD",
            "SNXUSD",
            "CRVUSD",
            "LDOUSD",
            "COMPUSD",
            # Layer 2s
            "MATICUSD",
            "ARBUSD",
            "OPUSD",
            # Other majors
            "LTCUSD",
            "BCHUSD",
            "ETCUSD",
            "XLMUSD",
            "VETUSD",
            # Meme & momentum coins (volatile!)
            "SHIBUSD",
            "PEPEUSD",
            "FLOKIUSD",
            "BONKUSD",
            # Gaming/Metaverse
            "AXSUSD",
            "GALAUSD",
            "ENJUSD",
            "IMXUSD",
        ]

        # Track last volatility scan time
        self.last_volatility_scan = None
        self.volatile_pairs_cache: List[str] = []
        # The original `self.configured_universe` and `self.default_pairs = list(self.configured_universe)`
        # lines are replaced by the hardcoded `self.default_pairs` above.
        # The `self.configured_universe` is no longer explicitly set here,
        # but `_merge_symbol_lists` will still use `self.default_pairs` as a base.
        self.configured_universe = self._merge_symbol_lists(
            [], self.config.universe if self.config else []
        )  # Re-added for merge_symbol_lists

        initial_overrides = enabled_symbols or []
        merged_symbols = self._merge_symbol_lists(
            self.configured_universe, initial_overrides
        )

        self.high_volume_pairs = merged_symbols
        self.enabled_trading_symbols: Set[str] = set(merged_symbols)
        _metric_set(SCANNER_TRACKED_SYMBOLS_GAUGE, float(len(self.high_volume_pairs)))

        # Scanner thresholds sourced from configuration
        # These now use the new config-driven defaults or the hardcoded ones
        self.min_24h_volume = self.min_volume
        self.min_volatility = (
            self.config.min_volatility if self.config else 0.005
        )  # Default if config is None
        self.max_spread = self.max_spread

        self.price_data: Dict[str, List[float]] = {}
        self.volatility_data: Dict[str, float] = {}
        self.volume_data: Dict[str, List[float]] = {}
        # Track indicator history per symbol for relative thresholds
        # Structure: {symbol: {"rsi": [values], "stoch_k": [values]}}
        self.indicator_history: Dict[str, Dict[str, List[float]]] = {}

        logger.info(
            "Initialized crypto scanner with %d configured symbols (%d defaults, %d overrides)",
            len(self.high_volume_pairs),
            len(self.configured_universe),
            max(0, len(self.high_volume_pairs) - len(self.configured_universe)),
        )

    def preseed_historical_data(self, api) -> int:
        """
        Pre-seed price and indicator history with historical bars.

        This enables relative thresholds to work immediately on startup,
        rather than waiting for real-time data to accumulate.

        Returns number of symbols successfully seeded.
        """
        from datetime import datetime, timedelta
        from alpaca.data.historical.crypto import CryptoHistoricalDataClient
        from alpaca.data.requests import CryptoBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        logger.info("📊 Pre-seeding historical data for relative thresholds...")

        try:
            # Create data client from trading API credentials
            data_client = CryptoHistoricalDataClient()
        except Exception as e:
            logger.warning(f"Could not create data client for pre-seeding: {e}")
            return 0

        # Fetch last 3 hours of 1-minute bars (180 data points per symbol)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=3)

        symbols_seeded = 0
        symbols_to_seed = self.high_volume_pairs[:20]  # Limit to top 20 to avoid rate limits

        for symbol in symbols_to_seed:
            try:
                # Alpaca expects format like "BTC/USD" for crypto
                api_symbol = f"{symbol[:3]}/{symbol[3:]}" if len(symbol) >= 6 else symbol

                request_params = CryptoBarsRequest(
                    symbol_or_symbols=[api_symbol],
                    timeframe=TimeFrame(1, TimeFrameUnit.Minute),
                    start=start_time,
                    end=end_time,
                )

                bars_response = data_client.get_crypto_bars(request_params)

                if api_symbol not in bars_response.data:
                    logger.debug(f"No historical data for {symbol}")
                    continue

                bars = bars_response.data[api_symbol]
                if len(bars) < 50:
                    logger.debug(f"Insufficient bars for {symbol}: {len(bars)}")
                    continue

                # Extract prices and volumes
                prices = [float(bar.close) for bar in bars]
                volumes = [float(bar.volume) for bar in bars]

                # Store price data
                self.price_data[symbol] = prices
                self.volume_data[symbol] = volumes

                # Now compute indicators for the historical data to build indicator_history
                # We'll compute RSI and StochK at multiple points to build history
                self.indicator_history[symbol] = {"rsi": [], "stoch_k": []}

                # Compute indicators at rolling windows through the data
                min_window = 26  # Minimum needed for indicators
                for i in range(min_window, len(prices), 5):  # Every 5 bars to save compute
                    window_prices = prices[:i+1]
                    rsi = self.calculate_rsi(window_prices)
                    stoch_k, _ = self.calculate_stoch_rsi(window_prices)

                    self.indicator_history[symbol]["rsi"].append(rsi)
                    self.indicator_history[symbol]["stoch_k"].append(stoch_k)

                symbols_seeded += 1
                logger.debug(
                    f"✅ {symbol}: Seeded {len(prices)} prices, "
                    f"{len(self.indicator_history[symbol]['rsi'])} indicator samples"
                )

            except Exception as e:
                logger.debug(f"Failed to preseed {symbol}: {e}")
                continue

        logger.info(
            f"📊 Pre-seeded {symbols_seeded}/{len(symbols_to_seed)} symbols with historical data"
        )
        return symbols_seeded

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        """Normalise symbols to scanner format."""

        return symbol.replace("/", "").upper()

    @classmethod
    def _merge_symbol_lists(
        cls,
        defaults: Iterable[str],
        overrides: Iterable[str],
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
            base = self.configured_universe if merge_with_defaults else []
            merged = self._merge_symbol_lists(base, enabled_symbols)

            self.enabled_trading_symbols = set(merged)
            self.high_volume_pairs = merged

            logger.info(
                "Updated enabled trading symbols: %d total (defaults merged: %s)",
                len(self.enabled_trading_symbols),
                merge_with_defaults,
            )
            logger.info(
                "Scanner now tracking high volume pairs: %s",
                ", ".join(self.high_volume_pairs),
            )
            _metric_set(
                SCANNER_TRACKED_SYMBOLS_GAUGE, float(len(self.high_volume_pairs))
            )

    def get_enabled_symbols(self) -> List[str]:
        """Get list of currently enabled trading symbols"""
        with self.lock:
            return list(self.high_volume_pairs)

    def fetch_all_crypto_assets(self, api) -> List[str]:
        """Fetch all available crypto assets from Alpaca"""
        try:
            # Try the alpaca_trade_api.REST method first
            if hasattr(api, "list_assets"):
                # Using alpaca_trade_api.REST
                assets = api.list_assets(status="active", asset_class="crypto")
                crypto_symbols = []
                for asset in assets:
                    symbol = asset.symbol
                    # Only include USD pairs for trading
                    if "USD" in symbol and len(symbol) <= 10:
                        # Normalize to remove slashes (BTC/USD -> BTCUSD)
                        normalized = symbol.replace("/", "")
                        crypto_symbols.append(normalized)

                logger.info(
                    f"📡 Fetched {len(crypto_symbols)} crypto assets from Alpaca"
                )
                return sorted(crypto_symbols)
            else:
                # Try newer alpaca-py SDK
                from alpaca.trading.requests import GetAssetsRequest
                from alpaca.trading.enums import AssetClass, AssetStatus

                search_params = GetAssetsRequest(
                    status=AssetStatus.ACTIVE, asset_class=AssetClass.CRYPTO
                )
                assets = api.get_all_assets(search_params)

                crypto_symbols = []
                for asset in assets:
                    symbol = asset.symbol
                    if "USD" in symbol and len(symbol) <= 10:
                        # Normalize to remove slashes (BTC/USD -> BTCUSD)
                        normalized = symbol.replace("/", "")
                        crypto_symbols.append(normalized)

                logger.info(
                    f"📡 Fetched {len(crypto_symbols)} crypto assets from Alpaca"
                )
                return sorted(crypto_symbols)

        except APIError as e:
            logger.error(f"Alpaca API error fetching crypto assets: {e}")
            return self.default_pairs
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Network error fetching crypto assets: {e}")
            return self.default_pairs
        except AttributeError as e:
            logger.warning(f"API client attribute error (incompatible client?): {e}")
            return self.default_pairs
        except Exception as e:
            logger.exception(f"Unexpected error fetching crypto assets: {e}")
            # Fallback to default pairs
            return self.default_pairs

    def calculate_market_volatility(
        self, api, symbols: List[str], lookback_hours: int = 24
    ) -> Dict[str, float]:
        """Calculate 24h volatility for all symbols using Alpaca data client"""
        volatility_scores = {}

        try:
            from alpaca.data.historical import CryptoHistoricalDataClient
            from alpaca.data.requests import CryptoBarsRequest
            from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
            from datetime import datetime, timedelta

            # Create data client (free tier, no auth needed for crypto data)
            data_client = CryptoHistoricalDataClient()

            # Calculate timeframe
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=lookback_hours)

            for symbol in symbols:
                try:
                    # Convert to slash format for API (BTCUSD -> BTC/USD)
                    api_symbol = (
                        symbol[:-3] + "/" + symbol[-3:] if "/" not in symbol else symbol
                    )
                    # Create bars request
                    request_params = CryptoBarsRequest(
                        symbol_or_symbols=[api_symbol],
                        timeframe=TimeFrame(1, TimeFrameUnit.Minute),
                        start=start_time,
                        end=end_time,
                    )

                    # Get historical bars
                    bars_response = data_client.get_crypto_bars(request_params)

                    if (
                        api_symbol not in bars_response.data
                        or len(bars_response.data[api_symbol]) < 50
                    ):
                        continue

                    # Extract price and volume data
                    bars = bars_response.data[api_symbol]
                    prices = [float(bar.close) for bar in bars]
                    volumes = [float(bar.volume) for bar in bars]

                    if len(prices) < 2:
                        continue

                    # Calculate price volatility
                    volatility = self.calculate_volatility(prices)

                    # Calculate 24h price change percentage
                    price_change_pct = abs((prices[-1] - prices[0]) / prices[0]) * 100

                    # NEW: Check for recent spike (last 5-10 minutes of data)
                    spike_lookback = getattr(SCANNER, "SPIKE_LOOKBACK_MINUTES", 5)
                    spike_boost = getattr(SCANNER, "SPIKE_PRIORITY_BOOST", 2.0)
                    is_spiking, spike_magnitude, spike_direction = self.detect_spike(
                        prices, volumes, spike_lookback
                    )

                    # Combine volatility metrics (favor both volatility and price movement)
                    combined_score = (volatility * 0.7) + (price_change_pct * 0.3)

                    # BOOST score for spiking coins - these are the opportunities!
                    if is_spiking:
                        combined_score *= spike_boost
                        logger.info(
                            f"🔥 {symbol}: SPIKING {spike_direction} {spike_magnitude*100:.2f}% - "
                            f"boosted score to {combined_score:.4f}"
                        )

                    volatility_scores[symbol] = combined_score

                except KeyError as e:
                    logger.debug(f"Missing data for {symbol}: {e}")
                    continue
                except (ZeroDivisionError, ValueError) as e:
                    logger.debug(f"Math error calculating volatility for {symbol}: {e}")
                    continue
                except (ConnectionError, TimeoutError) as e:
                    logger.debug(f"Network error fetching bars for {symbol}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Could not calculate volatility for {symbol}: {e}")
                    continue

        except ImportError as e:
            logger.error(f"Failed to import Alpaca data client modules: {e}")
            return {}
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Network error creating data client: {e}")
            logger.error(
                "FAKE DATA BLOCKED: Not using random volatility - returning empty results"
            )
            return {}
        except Exception as e:
            logger.exception(f"Unexpected error in calculate_market_volatility: {e}")
            logger.error(
                "FAKE DATA BLOCKED: Not using random volatility - returning empty results"
            )
            # NEVER use fake volatility data - return empty when real data unavailable
            return {}

        return volatility_scores

    def select_top_volatile_pairs(
        self, api, target_count: Optional[int] = None
    ) -> List[str]:
        """Dynamically select the most volatile crypto pairs"""
        if target_count is None:
            target_count = self.target_count

        try:
            # Fetch all available crypto assets
            all_symbols = self.fetch_all_crypto_assets(api)

            if not all_symbols:
                logger.warning("No crypto symbols found, using defaults")
                return self.default_pairs[:target_count]

            # Calculate volatility for all symbols
            logger.info(
                f"🔍 Analyzing volatility for {len(all_symbols)} crypto pairs..."
            )
            volatility_scores = self.calculate_market_volatility(api, all_symbols)

            if not volatility_scores:
                logger.warning("No volatility data available, using defaults")
                return self.default_pairs[:target_count]

            # Sort by volatility score (highest first)
            sorted_pairs = sorted(
                volatility_scores.items(), key=lambda x: x[1], reverse=True
            )

            # Select top N most volatile pairs
            top_pairs = [symbol for symbol, score in sorted_pairs[:target_count]]

            logger.info(f"🎯 Selected top {len(top_pairs)} volatile crypto pairs:")
            for i, (symbol, score) in enumerate(sorted_pairs[:target_count]):
                logger.info(f"  {i + 1}. {symbol}: Volatility Score {score:.4f}")

            return top_pairs

        except APIError as e:
            logger.error(f"Alpaca API error selecting volatile pairs: {e}")
            return self.default_pairs[:target_count]
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Network error selecting volatile pairs: {e}")
            return self.default_pairs[:target_count]
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"Data processing error selecting volatile pairs: {e}")
            return self.default_pairs[:target_count]
        except Exception as e:
            logger.exception(f"Unexpected error selecting volatile pairs: {e}")
            return self.default_pairs[:target_count]

    def calculate_volatility(self, prices: List[float], window: int = 20) -> float:
        """Calculate price volatility using standard deviation"""
        # Use smaller window if not enough data, minimum 3 points
        actual_window = min(window, len(prices))
        if actual_window < 3:
            return 0.0

        returns = np.diff(np.log(prices[-actual_window:]))
        return np.std(returns) * np.sqrt(1440)  # Annualized for 1-minute data

    def detect_volume_surge(self, volumes: List[float], window: int = 10) -> bool:
        """Detect if current volume is significantly higher than average"""
        if len(volumes) < window + 1:
            return False

        recent_avg = np.mean(volumes[-window - 1 : -1])
        current_volume = volumes[-1]

        return (
            current_volume > recent_avg * 1.1
        )  # Only 10% above average (much more aggressive)

    def calculate_momentum(self, prices: List[float], period: int = 14) -> float:
        """Calculate price momentum using RSI-like indicator"""
        if len(prices) < period + 1:
            return 0.5

        changes = np.diff(prices[-period - 1 :])
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, -changes, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 1.0

        rs = avg_gain / avg_loss
        momentum = rs / (1 + rs)

        return momentum

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index) - 0-100 scale"""
        if len(prices) < period + 1:
            return 50.0  # Neutral

        changes = np.diff(prices[-period - 1 :])
        gains = np.where(changes > 0, changes, 0)
        losses = np.where(changes < 0, -changes, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0
        if avg_gain == 0:
            return 0.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0.0

        multiplier = 2 / (period + 1)
        ema = prices[-period]  # Start with SMA

        for price in prices[-period + 1 :]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def calculate_macd(self, prices: List[float]) -> Tuple[float, float, float]:
        """Calculate MACD (12, 26, 9) - returns (macd_line, signal_line, histogram)"""
        if len(prices) < 26:
            return 0.0, 0.0, 0.0

        ema_12 = self.calculate_ema(prices, 12)
        ema_26 = self.calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26

        # Signal line is 9-period EMA of MACD line
        # For simplicity, we'll approximate with the current MACD
        # In production, you'd track historical MACD values
        signal_line = macd_line * 0.9  # Approximation

        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def calculate_stoch_rsi(
        self, prices: List[float], rsi_period: int = 14, stoch_period: int = 14
    ) -> Tuple[float, float]:
        """Calculate Stochastic RSI - returns (K, D)"""
        if len(prices) < rsi_period + stoch_period:
            return 50.0, 50.0

        # Calculate RSI values for stoch period
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

        # D is 3-period SMA of K
        stoch_d = stoch_k  # Simplified

        return stoch_k, stoch_d

    def detect_spike(
        self, prices: List[float], volumes: List[float], lookback_minutes: int = 5
    ) -> Tuple[bool, float, str]:
        """
        Detect if a coin is spiking (sudden price move with volume).

        Returns:
            (is_spiking, spike_magnitude, direction)
            - is_spiking: True if price moved significantly with volume
            - spike_magnitude: Percentage move (absolute value)
            - direction: 'up' or 'down'
        """
        if len(prices) < lookback_minutes + 1:
            return False, 0.0, "none"

        # Get spike detection parameters
        spike_threshold = getattr(SCANNER, "SPIKE_THRESHOLD_PCT", 0.01)
        volume_multiplier = getattr(SCANNER, "SPIKE_VOLUME_MULTIPLIER", 1.5)

        # Calculate price change over lookback period
        recent_prices = prices[-lookback_minutes:]
        price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        abs_change = abs(price_change)
        direction = "up" if price_change > 0 else "down"

        # Check volume confirmation
        volume_confirmed = True
        if volumes and len(volumes) >= lookback_minutes + 10:
            recent_volume = sum(volumes[-lookback_minutes:])
            avg_volume = sum(volumes[-lookback_minutes-10:-lookback_minutes]) / 10
            if avg_volume > 0:
                volume_confirmed = recent_volume > (avg_volume * volume_multiplier)

        # Spike = significant move + volume confirmation
        is_spiking = abs_change >= spike_threshold and volume_confirmed

        if is_spiking:
            logger.info(
                f"🚀 SPIKE DETECTED: {abs_change*100:.2f}% {direction} with volume confirmation"
            )

        return is_spiking, abs_change, direction

    def _get_relative_position(self, symbol: str, indicator: str, current_value: float) -> float:
        """
        Calculate where the current indicator value sits relative to its recent range.

        Returns 0.0 to 1.0:
          - 0.0 = at the lowest point seen recently (oversold relative to self)
          - 0.5 = middle of recent range
          - 1.0 = at the highest point seen recently (overbought relative to self)

        This enables per-symbol adaptive thresholds instead of fixed universal thresholds.
        """
        if symbol not in self.indicator_history:
            return 0.5  # No history, assume neutral

        history = self.indicator_history[symbol].get(indicator, [])
        if len(history) < 20:  # Need enough history for meaningful range
            return 0.5  # Not enough data, assume neutral

        recent_min = min(history)
        recent_max = max(history)
        range_size = recent_max - recent_min

        if range_size < 1.0:  # Very tight range, indicator barely moving
            return 0.5

        # Calculate position within range
        relative_pos = (current_value - recent_min) / range_size
        return max(0.0, min(1.0, relative_pos))  # Clamp to [0, 1]

    def get_indicators(self, symbol: str) -> Dict[str, float]:
        """Get all indicators for a symbol"""
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

            # Detect spikes for momentum trading
            spike_lookback = getattr(SCANNER, "SPIKE_LOOKBACK_MINUTES", 5)
            is_spiking, spike_magnitude, spike_direction = self.detect_spike(
                prices, volumes, spike_lookback
            )

            # Store indicator history for relative threshold calculations
            if symbol not in self.indicator_history:
                self.indicator_history[symbol] = {"rsi": [], "stoch_k": []}

            self.indicator_history[symbol]["rsi"].append(rsi)
            self.indicator_history[symbol]["stoch_k"].append(stoch_k)

            # Keep last 200 values (~3+ hours of data at 1 update/min)
            for key in ["rsi", "stoch_k"]:
                if len(self.indicator_history[symbol][key]) > 200:
                    self.indicator_history[symbol][key] = self.indicator_history[symbol][key][-200:]

            # Calculate relative positions (0.0 = at recent low, 1.0 = at recent high)
            rsi_relative = self._get_relative_position(symbol, "rsi", rsi)
            stoch_k_relative = self._get_relative_position(symbol, "stoch_k", stoch_k)

            return {
                "price": prices[-1],
                "rsi": rsi,
                "rsi_relative": rsi_relative,  # Where RSI sits in its recent range
                "macd": macd_line,
                "macd_signal": signal_line,
                "macd_histogram": histogram,
                "stoch_k": stoch_k,
                "stoch_k_relative": stoch_k_relative,  # Where StochK sits in its recent range
                "stoch_d": stoch_d,
                "ema_9": ema_9,
                "ema_21": ema_21,
                "ema_cross": "bullish" if ema_9 > ema_21 else "bearish",
                "volatility": volatility,
                "volume_surge": volume_surge,
                "is_spiking": is_spiking,
                "spike_magnitude": spike_magnitude,
                "spike_direction": spike_direction,
            }

    def refresh_volatile_pairs(self, api) -> None:
        """Periodically rescan market for most volatile pairs."""
        from datetime import datetime, timedelta

        # Check if we need to rescan (every 15 minutes)
        rescan_interval = getattr(SCANNER, "VOLATILITY_RESCAN_MINUTES", 15)

        if self.last_volatility_scan:
            time_since_scan = (
                datetime.now() - self.last_volatility_scan
            ).total_seconds() / 60
            if time_since_scan < rescan_interval:
                return  # Not time to rescan yet

        logger.info("🔄 Refreshing volatile pairs list...")

        try:
            # Get all crypto assets
            all_symbols = self.fetch_all_crypto_assets(api)

            if len(all_symbols) < 10:
                logger.warning("Not enough symbols found, keeping current list")
                return

            # Calculate volatility for a sample (to avoid rate limits)
            # Prioritize checking our defaults plus random others
            symbols_to_check = list(set(self.default_pairs + all_symbols[:50]))

            volatility_scores = self.calculate_market_volatility(api, symbols_to_check)

            if not volatility_scores:
                logger.warning("Could not calculate volatility, keeping current list")
                return

            # Sort by volatility and get top performers
            sorted_pairs = sorted(
                volatility_scores.items(), key=lambda x: x[1], reverse=True
            )

            # Get top 30 most volatile
            target_count = getattr(SCANNER, "TARGET_SYMBOL_COUNT", 30)
            # Normalize symbols to remove slashes (BTC/USD -> BTCUSD)
            new_volatile_pairs = [
                sym.replace("/", "") for sym, score in sorted_pairs[:target_count]
            ]

            # Always include major pairs for liquidity
            essential_pairs = ["BTCUSD", "ETHUSD", "SOLUSD", "XRPUSD", "DOGEUSD"]
            for pair in essential_pairs:
                if pair not in new_volatile_pairs:
                    new_volatile_pairs.append(pair)

            # Update tracked pairs
            old_count = len(self.high_volume_pairs)
            self.high_volume_pairs = new_volatile_pairs
            self.enabled_trading_symbols = set(new_volatile_pairs)
            self.volatile_pairs_cache = new_volatile_pairs.copy()
            self.last_volatility_scan = datetime.now()

            # Log the volatile pairs found
            logger.info(
                f"🎯 Updated to {len(new_volatile_pairs)} volatile pairs (was {old_count}):"
            )
            for i, (sym, score) in enumerate(sorted_pairs[:10]):
                logger.info(f"  {i + 1}. {sym}: volatility={score:.4f}")

            # Log any new additions
            new_additions = set(new_volatile_pairs) - set(self.default_pairs)
            if new_additions:
                logger.info(
                    f"  📈 New volatile additions: {', '.join(list(new_additions)[:5])}"
                )

        except Exception as e:
            logger.error(f"Error refreshing volatile pairs: {e}")
            # Keep existing list on error

    def scan_for_opportunities(self) -> List[CryptoSignal]:
        """Scan all crypto pairs for day trading opportunities - VOLATILITY HUNTING MODE"""
        signals = []
        signals_rejected = 0

        # Log scan start to activity feed
        activity = _get_activity()
        if activity:
            activity.log_scan_start(len(self.high_volume_pairs))

        with self.lock:
            _metric_inc(SCANNER_SCAN_COUNTER)
            _metric_set(SCANNER_LAST_RUN_GAUGE, float(time.time()))
            _metric_set(
                SCANNER_TRACKED_SYMBOLS_GAUGE, float(len(self.high_volume_pairs))
            )
            logger.info(
                f"🔍 Scanning {len(self.high_volume_pairs)} symbols for opportunities..."
            )

            symbols_with_data = [
                s for s in self.high_volume_pairs if s in self.price_data
            ]
            logger.info(f"📊 Scanning {len(symbols_with_data)} symbols with price data")

            for symbol in self.high_volume_pairs:
                try:
                    if symbol not in self.price_data:
                        continue

                    prices = self.price_data[symbol]
                    volumes = self.volume_data.get(symbol, [])

                    if len(prices) < 2:  # MINIMAL requirement for ultra-fast signals
                        logger.info(
                            f"  ❌ {symbol}: Insufficient price data ({len(prices)} points)"
                        )
                        continue

                    logger.info(f"  🔍 {symbol}: Processing {len(prices)} price points")

                    current_price = prices[-1]
                    volatility = self.calculate_volatility(prices)
                    volume_surge = self.detect_volume_surge(volumes)
                    momentum = self.calculate_momentum(prices)

                    # Generate trading signal
                    try:
                        signal = self._generate_signal(
                            symbol, current_price, volatility, volume_surge, momentum
                        )

                        if signal and signal.action == "buy":
                            signals.append(signal)
                            logger.info(
                                f"  ✅ {symbol}: BUY signal @ ${current_price:.2f} (conf={signal.confidence:.2f})"
                            )
                            # Log accepted signal to activity feed
                            if activity:
                                activity.log_signal(
                                    symbol=symbol,
                                    action=signal.action,
                                    confidence=signal.confidence,
                                    price=current_price,
                                    reason=f"Strong {signal.action} indicators",
                                    accepted=True,
                                )
                        elif signal:
                            # Signal generated but not buy (sell signals are logged but skipped)
                            signals_rejected += 1
                            logger.info(
                                f"  ⏭️ {symbol}: SELL signal skipped (no shorting)"
                            )
                            if activity:
                                activity.log_signal(
                                    symbol=symbol,
                                    action=signal.action,
                                    confidence=signal.confidence,
                                    price=current_price,
                                    reason="Sell signals not executed (no shorting)",
                                    accepted=False,
                                )
                        else:
                            # No signal generated (HOLD)
                            logger.debug(
                                f"  ⏸️ {symbol}: No signal from _generate_signal"
                            )
                    except (KeyError, TypeError) as sig_err:
                        logger.warning(
                            f"  {symbol}: Missing/invalid data for signal: {sig_err}"
                        )
                    except (ZeroDivisionError, ValueError) as sig_err:
                        logger.warning(
                            f"  {symbol}: Math error in signal generation: {sig_err}"
                        )
                    except Exception as sig_err:
                        logger.exception(
                            f"  {symbol}: Unexpected signal generation error: {sig_err}"
                        )

                except (KeyError, IndexError) as e:
                    logger.warning(f"Data access error scanning {symbol}: {e}")
                    _metric_inc(SCANNER_ERROR_COUNTER)
                except (ZeroDivisionError, ValueError) as e:
                    logger.warning(f"Calculation error scanning {symbol}: {e}")
                    _metric_inc(SCANNER_ERROR_COUNTER)
                except Exception as e:
                    logger.exception(f"Unexpected error scanning {symbol}: {e}")
                    _metric_inc(SCANNER_ERROR_COUNTER)

        logger.info(f"🎯 Total signals generated: {len(signals)}")
        # Sort by best opportunities (high volatility + volume surge)
        top_signals = sorted(signals, key=lambda s: s.confidence, reverse=True)[:10]
        _metric_set(SCANNER_SIGNALS_GAUGE, float(len(top_signals)))

        # Log scan completion to activity feed
        if activity:
            activity.log_scan_complete(len(top_signals), signals_rejected)

        return top_signals

    def _generate_signal(
        self,
        symbol: str,
        price: float,
        volatility: float,
        volume_surge: bool,
        momentum: float,
    ) -> Optional[CryptoSignal]:
        """Generate trading signal - CONSERVATIVE MODE - only trade on strong signals"""

        # Get full indicator set
        indicators = self.get_indicators(symbol)
        activity = _get_activity()
        if not indicators:
            # No indicators = no trade. Wait for proper data.
            logger.debug(f"    ⏳ {symbol}: Waiting for indicators (need more data)")
            if activity:
                activity.log_rejection(
                    symbol,
                    "Insufficient data for indicators",
                    {"reason": "need_more_data", "price": price},
                )
            return None

        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", 0)
        macd_hist = indicators.get("macd_histogram", 0)
        stoch_k = indicators.get("stoch_k", 50)
        ema_cross = indicators.get("ema_cross", "neutral")

        # RELATIVE thresholds - where each indicator sits within ITS OWN recent range
        # This creates diversity: same absolute RSI=55 can be "high" for one coin, "low" for another
        rsi_rel = indicators.get("rsi_relative", 0.5)
        stoch_rel = indicators.get("stoch_k_relative", 0.5)

        # DEBUG: Log all indicator values for each symbol (now includes relative positions)
        logger.info(
            f"    📊 {symbol} indicators: RSI={rsi:.1f} (rel:{rsi_rel:.0%}) | StochK={stoch_k:.1f} (rel:{stoch_rel:.0%}) | "
            f"MACD_hist={macd_hist:.4f} | EMA={ema_cross} | Vol={volatility:.4f}"
        )

        action = "hold"
        confidence = 0.0
        # Use wider stops to avoid getting stopped out by noise
        target_profit = RISK.TAKE_PROFIT_DEFAULT  # 1.5% target profit
        stop_loss = RISK.STOP_LOSS_DEFAULT  # 1.5% stop loss (matches config)
        signal_reasons = []

        # ============ BUY SIGNALS (RELATIVE - each coin scored against its own range) ============
        buy_score = 0

        # BLOCK conditions - using BOTH absolute (safety) and relative (context)
        # Absolute block: RSI truly overbought (>70) regardless of context
        # Relative block: RSI in top 15% of its range (coin-specific overbought)
        if rsi > 70:
            signal_reasons.append(f"BLOCKED: RSI overbought ({rsi:.1f})")
            buy_score = -10
        elif rsi_rel > 0.85:
            signal_reasons.append(f"BLOCKED: RSI at relative high ({rsi:.1f}, top {(1-rsi_rel)*100:.0f}%)")
            buy_score = -10
        elif stoch_k > 85:
            signal_reasons.append(f"BLOCKED: StochRSI very high ({stoch_k:.1f})")
            buy_score = -10
        elif stoch_rel > 0.90:
            signal_reasons.append(f"BLOCKED: StochRSI at relative high ({stoch_k:.1f}, top {(1-stoch_rel)*100:.0f}%)")
            buy_score = -10
        else:
            # SCORING based on RELATIVE position (creates diversity across symbols)

            # RSI relative scoring - where is RSI within THIS coin's recent range?
            if rsi_rel < 0.15:
                buy_score += 4  # In bottom 15% of its range = strong oversold for THIS coin
                signal_reasons.append(f"RSI at relative low ({rsi:.1f}, bottom {rsi_rel*100:.0f}%)")
            elif rsi_rel < 0.25:
                buy_score += 3
                signal_reasons.append(f"RSI low in range ({rsi:.1f}, {rsi_rel*100:.0f}%)")
            elif rsi_rel < 0.40:
                buy_score += 2
                signal_reasons.append(f"RSI lower half ({rsi:.1f}, {rsi_rel*100:.0f}%)")
            elif rsi_rel < 0.55:
                buy_score += 1
                signal_reasons.append(f"RSI neutral ({rsi:.1f}, {rsi_rel*100:.0f}%)")
            # rsi_rel 0.55-0.85: no points but not blocked

            # StochRSI relative scoring - key timing indicator
            if stoch_rel < 0.10:
                buy_score += 4  # Excellent entry - at the very bottom of its range
                signal_reasons.append(f"StochRSI at relative low ({stoch_k:.1f}, bottom {stoch_rel*100:.0f}%)")
            elif stoch_rel < 0.25:
                buy_score += 3
                signal_reasons.append(f"StochRSI low in range ({stoch_k:.1f}, {stoch_rel*100:.0f}%)")
            elif stoch_rel < 0.40:
                buy_score += 2
                signal_reasons.append(f"StochRSI lower half ({stoch_k:.1f}, {stoch_rel*100:.0f}%)")
            elif stoch_rel < 0.55:
                buy_score += 1
                signal_reasons.append(f"StochRSI neutral ({stoch_k:.1f}, {stoch_rel*100:.0f}%)")

            # MACD positive momentum - bonus only
            if macd_hist > 0:
                buy_score += 1
                signal_reasons.append("MACD positive")

            # EMA bullish crossover - bonus only
            if ema_cross == "bullish":
                buy_score += 1
                signal_reasons.append("EMA bullish cross")

            # Volume surge confirms
            if volume_surge and buy_score >= 3:
                buy_score += 1
                signal_reasons.append("Volume confirmation")

        # ============ SELL SIGNALS (RELATIVE - overbought for THIS coin's range) ============
        sell_score = 0
        sell_reasons = []

        # RSI relative scoring for sell signals
        if rsi_rel > 0.90:
            sell_score += 3  # In top 10% of its range = very overbought for THIS coin
            sell_reasons.append(f"RSI at relative high ({rsi:.1f}, top {(1-rsi_rel)*100:.0f}%)")
        elif rsi_rel > 0.80:
            sell_score += 2
            sell_reasons.append(f"RSI high in range ({rsi:.1f}, {rsi_rel*100:.0f}%)")
        elif rsi_rel > 0.70:
            sell_score += 1
            sell_reasons.append(f"RSI upper half ({rsi:.1f}, {rsi_rel*100:.0f}%)")

        # MACD turning negative
        if macd_hist < 0:
            sell_score += 1
            sell_reasons.append("MACD negative")

        # StochRSI relative scoring for sell signals
        if stoch_rel > 0.90:
            sell_score += 3  # At the very top of its range
            sell_reasons.append(f"StochRSI at relative high ({stoch_k:.1f}, top {(1-stoch_rel)*100:.0f}%)")
        elif stoch_rel > 0.80:
            sell_score += 2
            sell_reasons.append(f"StochRSI high in range ({stoch_k:.1f}, {stoch_rel*100:.0f}%)")

        # EMA bearish crossover
        if ema_cross == "bearish":
            sell_score += 2
            sell_reasons.append("EMA bearish cross")

        # Volume surge on sell
        if volume_surge:
            sell_score += 1
            sell_reasons.append("Volume confirmation")

        # ============ DETERMINE ACTION (QUALITY + MOMENTUM) ============
        # Get spike info for momentum bypass
        is_spiking = indicators.get("is_spiking", False)
        spike_direction = indicators.get("spike_direction", "none")
        spike_magnitude = indicators.get("spike_magnitude", 0)

        # Dynamic min_score: lower threshold if coin is spiking in our direction
        base_min_score = getattr(RISK, "MIN_SIGNAL_SCORE", 4)
        momentum_bypass = getattr(RISK, "MOMENTUM_BYPASS_SCORE", 2)

        # Allow momentum bypass for spiking coins - catch the move!
        if is_spiking and spike_direction == "up" and spike_magnitude >= 0.01:
            min_score = momentum_bypass
            signal_reasons.append(f"🚀 MOMENTUM: {spike_magnitude*100:.1f}% spike")
            logger.info(f"    🚀 {symbol}: Momentum bypass active (spike {spike_direction})")
        else:
            min_score = base_min_score

        if buy_score >= min_score and buy_score > sell_score:
            # Check learning system for trade approval
            learner = get_trade_learner()
            should_trade, learn_reason = learner.should_take_trade(
                symbol, indicators, buy_score
            )
            if not should_trade:
                logger.info(f"    🧠 {symbol}: BLOCKED by learner - {learn_reason}")
                if activity:
                    activity.log_rejection(
                        symbol,
                        f"Learning system: {learn_reason}",
                        {"buy_score": buy_score, "rsi": rsi, "stoch_k": stoch_k},
                    )
                return None

            action = "buy"
            confidence = min(0.95, 0.5 + (buy_score * 0.1))
            if buy_score >= 5:
                target_profit = (
                    RISK.STRONG_SIGNAL_TAKE_PROFIT
                )  # 2% target for very strong signals
                stop_loss = (
                    RISK.STRONG_SIGNAL_STOP_LOSS
                )  # Tighter stop for strong signals
            logger.info(
                f"    📈 BUY: score={buy_score} | {', '.join(signal_reasons)} | {learn_reason}"
            )

        elif sell_score >= min_score and sell_score > buy_score:
            # For sells, also check if spiking down (momentum short)
            sell_min_score = min_score
            if is_spiking and spike_direction == "down" and spike_magnitude >= 0.01:
                sell_min_score = momentum_bypass
                sell_reasons.append(f"📉 MOMENTUM: {spike_magnitude*100:.1f}% drop")

            if sell_score >= sell_min_score:
                action = "sell"
                confidence = min(0.95, 0.5 + (sell_score * 0.1))
                signal_reasons = sell_reasons
                if sell_score >= 5:
                    target_profit = RISK.STRONG_SIGNAL_TAKE_PROFIT
                    stop_loss = RISK.STRONG_SIGNAL_STOP_LOSS
                logger.info(f"    📉 SELL: score={sell_score} | {', '.join(sell_reasons)}")

        else:
            # No clear signal - DO NOT TRADE
            logger.info(
                f"    ⏸️ {symbol}: No signal (buy={buy_score}, sell={sell_score}, need {min_score})"
            )
            if activity:
                activity.log_decision(
                    symbol=symbol,
                    decision="HOLD",
                    reason=f"Signal too weak (buy={buy_score}, sell={sell_score}, need {min_score})",
                    details={
                        "buy_score": buy_score,
                        "sell_score": sell_score,
                        "min_required": min_score,
                        "rsi": rsi,
                        "stoch_k": stoch_k,
                        "ema_cross": ema_cross,
                        "price": price,
                    },
                )
            return None

        # Create the signal only with sufficient confidence
        if action != "hold" and confidence >= 0.6:
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
                signal_reasons=signal_reasons,
            )

        # Signal had action but confidence too low
        if action != "hold" and confidence < 0.6:
            if activity:
                activity.log_signal(
                    symbol=symbol,
                    action=action,
                    confidence=confidence,
                    price=price,
                    reason=f"Confidence {confidence:.0%} below 60% threshold",
                    accepted=False,
                )

        return None

    def update_market_data(self, symbol: str, price: float, volume: float):
        """Update real-time market data"""
        with self.lock:
            if symbol not in self.price_data:
                self.price_data[symbol] = []
                self.volume_data[symbol] = []

            self.price_data[symbol].append(price)
            self.volume_data[symbol].append(volume)

            # Keep only recent data (1000 data points ≈ 16-17 hours of 1-min data)
            if len(self.price_data[symbol]) > 1000:
                self.price_data[symbol] = self.price_data[symbol][-1000:]
                self.volume_data[symbol] = self.volume_data[symbol][-1000:]


class CryptoDayTradingBot:
    """High-frequency crypto day trading bot with comprehensive error handling"""

    name = "CryptoDayTradingBot"  # Required for TradingBot integration

    CASH_SAFETY_BUFFER = Decimal("0.995")
    DEFAULT_TICK_SIZE = Decimal("0.000001")
    TICK_SIZE_BY_SYMBOL = {
        "BTC": Decimal("0.000001"),  # 1e-6 BTC
        "ETH": Decimal("0.0001"),  # 1e-4 ETH
    }

    def __init__(
        self,
        alpaca_client,
        initial_capital: float = 10000,
        scanner_config: Optional[CryptoScannerConfig] = None,
        enabled_symbols: Optional[List[str]] = None,
        scanner: Optional[Any] = None,
    ):
        self.alpaca = alpaca_client
        # Use injected scanner if provided, otherwise create local instance
        if scanner is not None:
            self.scanner = scanner
            logger.info("CryptoDayTradingBot using injected shared scanner")
        else:
            self.scanner = CryptoVolatilityScanner(
                scanner_config, enabled_symbols=enabled_symbols
            )
            logger.info("CryptoDayTradingBot created local scanner instance")

        # Pre-seed historical data for immediate relative threshold support
        try:
            seeded = self.scanner.preseed_historical_data(alpaca_client)
            if seeded > 0:
                logger.info(f"✅ Relative thresholds ready with {seeded} symbols pre-seeded")
        except Exception as e:
            logger.warning(f"Could not preseed historical data (will build over time): {e}")
        self.initial_capital = initial_capital
        self.max_position_size = min(
            100, initial_capital * 0.03
        )  # 3% per trade, max $100
        self.max_concurrent_positions = 10  # Limit positions for better management
        self.min_profit_target = RISK.MIN_PROFIT_TARGET  # 1% minimum profit target

        # Trading metrics
        self.active_positions = {}
        self.daily_trades = 0
        self.daily_profit = 0.0
        self.win_rate = 0.0
        self.total_trades = 0
        self.wins = 0

        # Risk management - CONSERVATIVE to protect capital
        self.max_daily_loss = initial_capital * 0.03  # 3% daily loss limit
        self.max_drawdown = initial_capital * 0.08  # 8% maximum drawdown

        # Error handling
        self.error_count = 0
        self.max_errors = 10
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.rate_limit_errors = 0
        self.last_rate_limit_time = None

        # Trade logging
        self.trade_log: List[TradeLog] = []
        self.log_file = "logs/crypto_trade_timeline.log"
        os.makedirs("logs", exist_ok=True)

        self.is_running = False
        self.executor = ThreadPoolExecutor(
            max_workers=10
        )  # More workers for parallel operations

        # Configurable thresholds - Pulled from config or sensible defaults
        self.stop_loss_pct = getattr(
            scanner_config, "stop_loss", RISK.STOP_LOSS_DEFAULT
        )
        self.take_profit_pct = getattr(
            scanner_config, "take_profit", RISK.TAKE_PROFIT_DEFAULT
        )
        self.trailing_stop_pct = getattr(
            scanner_config, "trailing_stop", RISK.TRAILING_STOP_DEFAULT
        )
        self.max_hold_time_seconds = getattr(scanner_config, "max_hold_time", 1800)
        self.min_hold_time_seconds = getattr(scanner_config, "min_hold_time", 120)

        # Override with risk_management if available in config object
        if hasattr(scanner_config, "_parent") and hasattr(
            scanner_config._parent, "risk_management"
        ):
            rm = scanner_config._parent.risk_management
            if hasattr(rm, "stop_loss"):
                self.stop_loss_pct = rm.stop_loss
            if hasattr(rm, "take_profit"):
                self.take_profit_pct = rm.take_profit
            if hasattr(rm, "trailing_stop"):
                self.trailing_stop_pct = rm.trailing_stop

    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Generate trading signals from OHLCV DataFrame.
        Required by the Strategy interface for TradingBot integration.

        Args:
            df: DataFrame with columns: open, high, low, close, volume, symbol

        Returns:
            List of signal dictionaries with keys: symbol, action, confidence, price, etc.
        """
        signals = []

        if df.empty:
            return signals

        # Extract symbol from DataFrame
        symbol = df["symbol"].iloc[-1] if "symbol" in df.columns else "UNKNOWN"

        # Get current price and volume
        current_price = float(df["close"].iloc[-1])
        current_volume = float(df["volume"].iloc[-1]) if "volume" in df.columns else 0

        # Feed FULL DataFrame to scanner for indicator calculation (need 26+ points)
        # Check if we need to bulk load (scanner doesn't have enough data)
        with self.scanner.lock:
            current_data_len = len(self.scanner.price_data.get(symbol, []))

        if current_data_len < 26 and len(df) > 1:
            # Bulk load all historical data from DataFrame
            for idx in range(len(df)):
                row_price = float(df["close"].iloc[idx])
                row_volume = (
                    float(df["volume"].iloc[idx]) if "volume" in df.columns else 0
                )
                self.scanner.update_market_data(symbol, row_price, row_volume)
            logger.debug(f"Bulk loaded {len(df)} bars for {symbol} into scanner")
        else:
            # Just update with latest price
            self.scanner.update_market_data(symbol, current_price, current_volume)

        # Calculate volatility from recent price data
        if len(df) >= 10:
            returns = df["close"].pct_change().dropna()
            volatility = float(returns.std()) if len(returns) > 0 else 0.01
        else:
            volatility = 0.01

        # Check for volume surge
        avg_volume = (
            df["volume"].rolling(20).mean().iloc[-1]
            if len(df) >= 20
            else current_volume
        )
        volume_surge = current_volume > (avg_volume * 1.5) if avg_volume > 0 else False

        # Calculate momentum
        momentum = (
            self.scanner.calculate_momentum(list(df["close"]))
            if hasattr(self.scanner, "calculate_momentum")
            else 0.5
        )

        # Generate signal using internal method
        crypto_signal = self.scanner._generate_signal(
            symbol=symbol,
            price=current_price,
            volatility=volatility,
            volume_surge=volume_surge,
            momentum=momentum,
        )

        if crypto_signal and crypto_signal.action in ("buy", "sell"):
            # DEBUG: Log signal attributes
            logger.info(
                f"DEBUG: crypto_signal type={type(crypto_signal).__name__}, attrs={dir(crypto_signal)}"
            )
            # Construct reason from signal attributes
            reason_parts = []
            if crypto_signal.action == "buy":
                reason_parts.append(f"momentum={crypto_signal.momentum:.2f}")
            else:
                reason_parts.append(f"overbought conditions")
            if crypto_signal.volume_surge:
                reason_parts.append("volume surge detected")
            reason_parts.append(f"confidence={crypto_signal.confidence:.1%}")
            reason = ", ".join(reason_parts)

            signals.append(
                {
                    "symbol": symbol,
                    "action": crypto_signal.action.upper(),
                    "confidence": crypto_signal.confidence,
                    "price": current_price,
                    "timestamp": datetime.now().isoformat(),
                    "reason": reason,
                    "target_profit": crypto_signal.target_profit,
                    "stop_loss": crypto_signal.stop_loss,
                }
            )

        return signals

    @property
    def _api(self):
        """Get the raw Alpaca REST API object, handling both wrapper and direct types."""
        # If alpaca has an 'api' attribute (it's a wrapper), use that
        if hasattr(self.alpaca, "api"):
            return self.alpaca.api
        # If alpaca has a 'get_api' method, use that
        if hasattr(self.alpaca, "get_api"):
            return self.alpaca.get_api()
        # Otherwise assume it's already the raw API
        return self.alpaca

    async def _sync_positions_from_alpaca(self):
        """Sync active_positions with actual Alpaca positions"""
        try:
            positions = self._api.list_positions()
            synced_count = 0

            for pos in positions:
                symbol = pos.symbol
                # Only track crypto positions
                if not symbol.endswith("USD") and not symbol.endswith("USDT"):
                    continue

                entry_price = float(pos.avg_entry_price)
                qty = abs(float(pos.qty))
                side = "buy" if float(pos.qty) > 0 else "sell"

                if symbol not in self.active_positions:
                    # Create position entry with default thresholds
                    self.active_positions[symbol] = {
                        "signal": None,  # External position, no signal
                        "entry_price": entry_price,
                        "entry_price_dec": Decimal(str(entry_price)),
                        "quantity": qty,
                        "quantity_dec": Decimal(str(qty)),
                        "side": side,
                        "entry_time": datetime.now(),  # Approximate
                        "target_price": entry_price * (1 + self.take_profit_pct)
                        if side == "buy"
                        else entry_price * (1 - self.take_profit_pct),
                        "stop_price": entry_price * (1 - self.stop_loss_pct)
                        if side == "buy"
                        else entry_price * (1 + self.stop_loss_pct),
                        "order_id": None,
                        "synced_from_alpaca": True,
                        "unrealized_pnl": float(pos.unrealized_pl)
                        if hasattr(pos, "unrealized_pl")
                        else 0,
                        "current_price": float(pos.current_price)
                        if hasattr(pos, "current_price")
                        else entry_price,
                    }
                    synced_count += 1
                    logger.info(
                        f"📥 Synced existing position: {symbol} | Entry: ${entry_price:.4f} | Qty: {qty}"
                    )
                else:
                    # Update quantity for existing position (may have changed due to partial fills)
                    tracked_qty = self.active_positions[symbol]["quantity"]
                    if abs(tracked_qty - qty) > 0.0001:
                        logger.info(
                            f"🔄 {symbol}: Updating qty from {tracked_qty:.6f} to {qty:.6f}"
                        )
                        self.active_positions[symbol]["quantity"] = qty
                        self.active_positions[symbol]["quantity_dec"] = Decimal(
                            str(qty)
                        )

            # Remove positions that no longer exist on Alpaca
            alpaca_symbols = {pos.symbol for pos in positions}
            to_remove = [s for s in self.active_positions if s not in alpaca_symbols]
            for symbol in to_remove:
                del self.active_positions[symbol]
                logger.info(f"📤 Removed closed position from tracking: {symbol}")

            if synced_count > 0:
                logger.info(
                    f"✅ Synced {synced_count} positions from Alpaca. Total tracked: {len(self.active_positions)}"
                )

        except APIError as e:
            logger.error(f"Alpaca API error syncing positions: {e}")
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Network error syncing positions from Alpaca: {e}")
        except (KeyError, AttributeError, TypeError) as e:
            logger.warning(f"Data parsing error syncing positions: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error syncing positions from Alpaca: {e}")

    async def start_trading(self):
        """Start the day trading bot"""
        logger.info("🚀 Starting Crypto Day Trading Bot")
        self.is_running = True

        # Sync existing positions from Alpaca first
        await self._sync_positions_from_alpaca()

        # Start market data feed
        self.executor.submit(self._start_market_data_feed)

        # Main trading loop
        logger.info("🔄 Starting main trading loop")
        cycle_count = 0
        while self.is_running:
            try:
                cycle_count += 1
                if cycle_count % 60 == 0:  # Log every 60 seconds
                    logger.info(
                        f"🔄 Trading loop heartbeat: {cycle_count} cycles completed"
                    )
                await self._trading_cycle()
                await asyncio.sleep(1)  # 1-second cycle for high frequency

            except APIError as e:
                logger.error(f"Alpaca API error in trading cycle: {e}")
                await asyncio.sleep(5)
            except (ConnectionError, TimeoutError) as e:
                logger.warning(f"Network error in trading cycle: {e}")
                await asyncio.sleep(10)  # Longer wait for network issues
            except asyncio.CancelledError:
                logger.info("Trading cycle cancelled")
                raise  # Re-raise to allow proper shutdown
            except Exception as e:
                logger.exception(f"Unexpected error in trading cycle: {e}")
                await asyncio.sleep(5)

        logger.info(f"🛑 Trading loop exited (is_running={self.is_running})")

    async def _trading_cycle(self):
        """Main trading cycle - SCALPING MODE (faster cycles)

        API Budget: 200 requests/min
        For scalping we need faster scans but must stay under limit.
        - Exit checks: Every 5 seconds (uses cached prices)
        - Entry scans: Every 10 seconds
        - Position sync: Every 30 seconds
        - Data updates handled by background polling
        """

        current_time = int(time.time())

        # SCALPING: Check exits every 5 seconds for quick profit taking
        if current_time % 5 == 0:
            await self._check_exit_conditions()

        # Sync positions from Alpaca every 30 seconds
        if current_time % 30 == 0:
            await self._sync_positions_from_alpaca()

        # SCALPING: Scan for entries every 10 seconds for rapid opportunities
        if current_time % 10 == 5:  # Offset from sync
            await self._find_entry_opportunities()

        # Update metrics every 2 minutes
        if current_time % 120 == 0:
            self._update_metrics()

        # Refresh volatile pairs every 15 minutes (always enabled)
        if current_time % 900 == 0:  # 900 seconds = 15 minutes
            try:
                self.scanner.refresh_volatile_pairs(self._api)
            except Exception as e:
                logger.error(f"Failed to refresh volatile pairs: {e}")

    async def _find_entry_opportunities(self):
        """Find new trading opportunities"""
        activity = _get_activity()
        try:
            # Log entry scan start to activity feed
            active_symbols = list(self.active_positions.keys())[:5]  # First 5 for brevity
            if activity:
                pos_display = f"[{', '.join(active_symbols)}]" if active_symbols else "[]"
                activity._log(
                    f"📊 Entry check: {len(self.active_positions)}/{self.max_concurrent_positions} positions {pos_display}, P&L: ${self.daily_profit:.2f}",
                    "info",
                )

            logger.info(
                f"🔎 Entry scan: {len(self.active_positions)}/{self.max_concurrent_positions} positions, daily P&L: ${self.daily_profit:.2f}"
            )

            if len(self.active_positions) >= self.max_concurrent_positions:
                logger.info("⏸️  Max positions reached, skipping entry scan")
                if activity:
                    activity._log(
                        f"⏸️ Max positions ({len(self.active_positions)}/{self.max_concurrent_positions}) - waiting for exit",
                        "info",
                    )
                return

            if self.daily_profit < -self.max_daily_loss:
                logger.warning(
                    f"Daily loss limit reached (${self.daily_profit:.2f}), stopping new trades"
                )
                if activity:
                    activity._log(
                        f"🛑 Daily loss limit reached (${self.daily_profit:.2f}) - trading paused",
                        "error",
                    )
                return

            # Get trading signals
            logger.info("📡 Getting trading signals from scanner...")
            signals = self.scanner.scan_for_opportunities()
            logger.info(f"📊 Got {len(signals)} signals from scanner")

            # Log signal count to activity feed for visibility
            if activity:
                if signals:
                    symbols_list = [s.symbol for s in signals[:5]]
                    activity._log(
                        f"📡 Processing {len(signals)} signals: {', '.join(symbols_list)}",
                        "info",
                    )
                else:
                    activity._log("📡 No signals returned from scanner", "info")

            for signal in signals[:5]:  # Top 5 opportunities
                if signal.symbol in self.active_positions:
                    if activity:
                        activity.log_decision(
                            symbol=signal.symbol,
                            decision="SKIP",
                            reason="Already have position in this symbol",
                            details={
                                "confidence": signal.confidence,
                                "price": signal.price,
                            },
                        )
                    continue

                if signal.confidence > 0.5:  # Lower threshold for more trades
                    logger.info(
                        f"🎯 Executing entry for {signal.symbol} (conf={signal.confidence:.2f})"
                    )
                    if activity:
                        activity._log(
                            f"🎯 Attempting entry @ ${signal.price:.4f} (conf: {signal.confidence:.0%})",
                            "info",
                            signal.symbol,
                        )
                    await self._execute_entry(signal)
                else:
                    if activity:
                        activity.log_decision(
                            symbol=signal.symbol,
                            decision="SKIP",
                            reason=f"Confidence {signal.confidence:.0%} below 50% entry threshold",
                            details={
                                "confidence": signal.confidence,
                                "price": signal.price,
                            },
                        )

            logger.info("Entry scan complete")
        except APIError as e:
            logger.error(f"Alpaca API error in entry scan: {e}")
        except (ConnectionError, TimeoutError) as e:
            logger.warning(f"Network error in entry scan: {e}")
        except (KeyError, AttributeError) as e:
            logger.warning(f"Data access error in entry scan: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in _find_entry_opportunities: {e}")

    async def _execute_entry(self, signal: CryptoSignal):
        """Execute entry trade with comprehensive error handling and logging"""
        start_time = time.time()
        activity = _get_activity()
        trade_log = TradeLog(
            timestamp=datetime.now().isoformat(),
            action=signal.action.upper(),
            symbol=signal.symbol,
            quantity=0,
            price=signal.price,
            status="pending",
            error_notes="",
        )

        try:
            # IMPORTANT: Skip SELL signals (no short selling in crypto)
            # Only execute BUY signals
            if signal.action.lower() == "sell":
                logger.info(
                    f"⏭️  Skipping SELL signal for {signal.symbol} (no short selling)"
                )
                return

            # SCALPING: Check spread before entry - don't let spread eat our profit
            try:
                alpaca_symbol = signal.symbol.replace("/", "")
                snapshot = self._api.get_crypto_snapshot(alpaca_symbol)
                if snapshot and hasattr(snapshot, "latest_quote"):
                    quote = snapshot.latest_quote
                    bid = float(quote.bid_price) if hasattr(quote, "bid_price") else 0
                    ask = float(quote.ask_price) if hasattr(quote, "ask_price") else 0
                    if bid > 0 and ask > 0:
                        spread_pct = (ask - bid) / bid
                        max_spread = RISK.MAX_SPREAD_DEFAULT  # 0.2%
                        if spread_pct > max_spread:
                            logger.info(
                                f"⏭️  Skipping {signal.symbol}: spread {spread_pct:.3%} > max {max_spread:.3%}"
                            )
                            if activity:
                                activity.log_decision(
                                    symbol=signal.symbol,
                                    decision="SKIP",
                                    reason=f"Spread too wide ({spread_pct:.3%} > {max_spread:.3%})",
                                    details={
                                        "spread_pct": spread_pct,
                                        "bid": bid,
                                        "ask": ask,
                                    },
                                )
                            return
            except Exception as spread_err:
                logger.debug(
                    f"Could not check spread for {signal.symbol}: {spread_err}"
                )
                # Continue anyway if spread check fails

            # Calculate position size - scale with confidence for better risk/reward
            # Higher confidence = larger position (but still capped)
            base_position = POSITION.MIN_POSITION_VALUE  # $10 minimum
            max_position = 100.0  # Increased from $25 - need meaningful positions!
            confidence_multiplier = 0.5 + (signal.confidence * 0.5)  # 0.5-1.0 range

            position_value = max(
                base_position,
                min(
                    self.max_position_size,
                    max_position * confidence_multiplier
                ),
            )

            # Clamp against available funds with a safety margin
            try:
                account = self._api.get_account()
                available_cash = float(
                    getattr(account, "cash", getattr(account, "buying_power", 0.0))
                )
            except Exception as exc:
                logger.warning(
                    f"Unable to fetch account balance, defaulting to configured limits: {exc}"
                )
                available_cash = position_value

            quantity = self._calculate_affordable_quantity(
                price=signal.price,
                desired_notional=position_value,
                available_cash=available_cash,
                symbol=signal.symbol,
            )

            if quantity <= 0:
                logger.warning("Calculated crypto quantity is 0 after precision clamp")
                return

            quantity_dec = (
                quantity if isinstance(quantity, Decimal) else Decimal(str(quantity))
            )
            quantity_float = float(quantity_dec)
            price_dec = Decimal(str(signal.price))

            trade_log.quantity = quantity_float

            # Log order submission
            if activity:
                activity.log_order_submit(signal.symbol, signal.action, quantity_float, signal.price)

            # Place order with error handling
            order = await self._place_crypto_order_with_retry(
                symbol=signal.symbol,
                side=signal.action,
                quantity=quantity_float,
                order_type="market",
            )

            if order:
                # Track position
                self.active_positions[signal.symbol] = {
                    "signal": signal,
                    "entry_price": signal.price,
                    "entry_price_dec": price_dec,
                    "quantity": quantity_float,
                    "quantity_dec": quantity_dec,
                    "side": signal.action,
                    "entry_time": datetime.now(),
                    "target_price": signal.price * (1 + signal.target_profit)
                    if signal.action == "buy"
                    else signal.price * (1 - signal.target_profit),
                    "stop_price": signal.price * (1 - signal.stop_loss)
                    if signal.action == "buy"
                    else signal.price * (1 + signal.stop_loss),
                    "order_id": order.id if hasattr(order, "id") else str(order),
                }

                trade_log.status = "filled"
                trade_log.order_id = order.id if hasattr(order, "id") else str(order)
                trade_log.execution_time_ms = int((time.time() - start_time) * 1000)

                logger.info(
                    f"🎯 Opened {signal.action.upper()} position: {signal.symbol} @ {signal.price:.4f}"
                )

                # Record entry for learning
                try:
                    learner = get_trade_learner()
                    indicators = (
                        self.scanner.get_indicators(signal.symbol)
                        if self.scanner
                        else {}
                    )
                    learner.record_entry(
                        symbol=signal.symbol,
                        side=signal.action,
                        entry_price=signal.price,
                        indicators=indicators,
                        signal_score=getattr(signal, "score", 3),
                        spread_pct=0.0,
                    )
                except Exception as learn_err:
                    logger.debug(f"Could not record entry for learning: {learn_err}")

                # Log successful trade to activity feed
                if activity:
                    activity.log_order_filled(signal.symbol, signal.action, quantity_float, signal.price)
                    # Log targets
                    target = self.active_positions[signal.symbol]["target_price"]
                    stop = self.active_positions[signal.symbol]["stop_price"]
                    activity._log(f"🎯 Target: ${target:.4f} | Stop: ${stop:.4f}", "info", signal.symbol)
            else:
                trade_log.status = "failed"
                trade_log.error_notes = "Order placement failed"
                if activity:
                    activity.log_rejection(
                        signal.symbol,
                        "Order placement failed",
                        {"confidence": signal.confidence, "price": signal.price},
                    )

        except APIError as e:
            trade_log.status = "failed"
            if hasattr(e, "code"):
                if e.code == 429:
                    trade_log.error_notes = "API rate limit exceeded"
                    self.rate_limit_errors += 1
                    self.last_rate_limit_time = datetime.now()
                    logger.error(f"🚫 Rate limit hit for {signal.symbol}: {e}")
                    await self._handle_rate_limit()
                elif e.code == 403:
                    trade_log.error_notes = "Insufficient funds"
                    logger.error(f"💸 Insufficient funds for {signal.symbol}")
                elif e.code == 400:
                    trade_log.error_notes = f"Invalid request: {str(e)}"
                    logger.error(f"❌ Invalid request for {signal.symbol}: {e}")
                else:
                    trade_log.error_notes = f"API error {e.code}: {str(e)}"
                    logger.error(f"❌ API error for {signal.symbol}: {e}")
            else:
                trade_log.error_notes = f"API error: {str(e)}"
                logger.error(f"❌ API error for {signal.symbol}: {e}")

        except ConnectionError as e:
            trade_log.status = "failed"
            trade_log.error_notes = "Connection lost, attempting reconnect"
            logger.error(f"🔌 Connection error for {signal.symbol}: {e}")
            await self._handle_connection_error()

        except (KeyError, AttributeError, TypeError) as e:
            trade_log.status = "failed"
            trade_log.error_notes = f"Data error: {str(e)}"
            logger.warning(f"Data error for {signal.symbol}: {e}")
            self.error_count += 1

        except (ZeroDivisionError, ValueError) as e:
            trade_log.status = "failed"
            trade_log.error_notes = f"Calculation error: {str(e)}"
            logger.warning(f"Calculation error for {signal.symbol}: {e}")
            self.error_count += 1

        except Exception as e:
            trade_log.status = "failed"
            trade_log.error_notes = f"Unexpected error: {str(e)}"
            logger.exception(
                f"Unexpected error executing entry for {signal.symbol}: {e}"
            )
            self.error_count += 1

        finally:
            # Log trade to timeline
            trade_log.execution_time_ms = int((time.time() - start_time) * 1000)
            self._log_trade(trade_log)

    @classmethod
    def _crypto_tick_size(cls, symbol: str) -> Decimal:
        base = symbol.split("/")[0].upper() if "/" in symbol else symbol.upper()
        return cls.TICK_SIZE_BY_SYMBOL.get(base, cls.DEFAULT_TICK_SIZE)

    @classmethod
    def _calculate_affordable_quantity(
        cls,
        *,
        price: float,
        desired_notional: float,
        available_cash: float,
        symbol: str,
    ) -> Decimal:
        price_dec = Decimal(str(price))
        desired_dec = Decimal(str(desired_notional))
        available_dec = Decimal(str(available_cash))

        if price_dec <= 0:
            return Decimal("0")

        safe_cash = (available_dec * cls.CASH_SAFETY_BUFFER).quantize(
            Decimal("0.000000001"), rounding=ROUND_DOWN
        )
        notional_cap = min(desired_dec, safe_cash)
        if notional_cap <= 0:
            return Decimal("0")

        raw_qty = notional_cap / price_dec
        tick_size = cls._crypto_tick_size(symbol)
        if tick_size <= 0:
            tick_size = cls.DEFAULT_TICK_SIZE

        ticks = (raw_qty / tick_size).to_integral_value(rounding=ROUND_DOWN)
        qty = ticks * tick_size
        if qty < tick_size:
            return Decimal("0")
        return qty

    async def _check_exit_conditions(self):
        """Check exit conditions for all active positions"""
        positions_to_close = []
        activity = _get_activity()

        # Make a copy of items to iterate (avoid dict modification during iteration)
        for symbol, position in list(self.active_positions.items()):
            try:
                # Get current price
                current_price = await self._get_current_price(symbol)
                if not current_price:
                    # Try to get from Alpaca position directly
                    try:
                        alpaca_pos = self._api.get_position(symbol)
                        current_price = float(alpaca_pos.current_price)
                    except Exception:
                        logger.warning(
                            f"Cannot get current price for {symbol}, skipping exit check"
                        )
                        continue

                entry_price = position["entry_price"]
                side = position["side"]

                # Calculate current P&L
                if side == "buy":
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price

                should_exit = False
                exit_reason = ""

                # Log position status periodically (every ~60 checks = ~1 min)
                if int(time.time()) % 60 == 0:
                    logger.info(
                        f"📊 {symbol}: Entry ${entry_price:.4f} | Current ${current_price:.4f} | P&L: {pnl_pct:.2%} | Stop: ${position['stop_price']:.4f} | Target: ${position['target_price']:.4f}"
                    )
                    # Log to activity feed
                    if activity:
                        activity.log_position_update(
                            symbol=symbol,
                            entry_price=entry_price,
                            current_price=current_price,
                            pnl_pct=pnl_pct,
                            stop_price=position["stop_price"],
                            target_price=position["target_price"],
                        )

                # Profit target hit
                if (side == "buy" and current_price >= position["target_price"]) or (
                    side == "sell" and current_price <= position["target_price"]
                ):
                    should_exit = True
                    exit_reason = "PROFIT_TARGET"

                # Stop loss hit
                elif (side == "buy" and current_price <= position["stop_price"]) or (
                    side == "sell" and current_price >= position["stop_price"]
                ):
                    should_exit = True
                    exit_reason = "STOP_LOSS"

                # SCALPING: Momentum fade exit - take profit early if momentum reverses
                elif pnl_pct > RISK.MIN_PROFIT_TARGET:  # 0.2% minimum profit
                    # Check if momentum is fading (indicators turning against us)
                    indicators = self.scanner.get_indicators(symbol)
                    if indicators:
                        rsi = indicators.get("rsi", 50)
                        stoch_k = indicators.get("stoch_k", 50)
                        macd_hist = indicators.get("macd_histogram", 0)

                        # Exit if we're profitable and momentum is reversing
                        if side == "buy":
                            # For longs: exit if overbought or momentum fading
                            if rsi > 65 or stoch_k > 70 or macd_hist < 0:
                                should_exit = True
                                exit_reason = f"MOMENTUM_FADE (RSI={rsi:.0f}, Stoch={stoch_k:.0f}, P&L={pnl_pct:.2%})"
                                logger.info(
                                    f"📉 {symbol}: Taking profit on momentum fade"
                                )

                # Time-based exit (configurable max hold time)
                if (
                    not should_exit
                    and (datetime.now() - position["entry_time"]).total_seconds()
                    > self.max_hold_time_seconds
                ):
                    should_exit = True
                    exit_reason = "TIME_LIMIT"

                # Trailing stop for profitable positions (activate at 0.3% profit for scalping)
                elif pnl_pct > self.trailing_stop_pct:
                    # Implement trailing stop
                    trail_distance = (
                        self.trailing_stop_pct * 0.5
                    )  # Trail at half the activation threshold
                    if side == "buy":
                        new_stop = current_price * (1 - trail_distance)
                        if new_stop > position["stop_price"]:
                            old_stop = position["stop_price"]
                            position["stop_price"] = new_stop
                            logger.info(
                                f"📈 {symbol}: Trailing stop raised from ${old_stop:.4f} to ${new_stop:.4f}"
                            )
                    else:
                        new_stop = current_price * (1 + trail_distance)
                        if new_stop < position["stop_price"]:
                            old_stop = position["stop_price"]
                            position["stop_price"] = new_stop
                            logger.info(
                                f"📉 {symbol}: Trailing stop lowered from ${old_stop:.4f} to ${new_stop:.4f}"
                            )

                if should_exit:
                    logger.info(
                        f"🚨 EXIT SIGNAL: {symbol} | Reason: {exit_reason} | P&L: {pnl_pct:.2%}"
                    )
                    positions_to_close.append(
                        (symbol, exit_reason, current_price, pnl_pct)
                    )

            except APIError as e:
                logger.error(f"Alpaca API error checking exit for {symbol}: {e}")
            except (KeyError, AttributeError) as e:
                logger.warning(f"Missing position data for {symbol}: {e}")
            except (ZeroDivisionError, ValueError) as e:
                logger.warning(f"Calculation error checking exit for {symbol}: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error checking exit for {symbol}: {e}")

        # Close positions
        for symbol, reason, price, pnl_pct in positions_to_close:
            await self._execute_exit(symbol, reason, price, pnl_pct)

    async def _execute_exit(
        self, symbol: str, reason: str, price: float, pnl_pct: float
    ):
        """Execute exit trade with P&L recording"""
        start_time = time.time()
        activity = _get_activity()
        try:
            position = self.active_positions[symbol]

            # IMPORTANT: Get actual quantity from Alpaca to avoid balance mismatches
            actual_qty = position["quantity"]
            try:
                alpaca_position = self._api.get_position(symbol)
                actual_qty = abs(float(alpaca_position.qty))
                if abs(actual_qty - position["quantity"]) > 0.0001:
                    logger.warning(
                        f"⚠️ {symbol}: Quantity mismatch - tracked: {position['quantity']:.6f}, actual: {actual_qty:.6f}"
                    )
                    position["quantity"] = actual_qty
                    position["quantity_dec"] = Decimal(str(actual_qty))
            except Exception as e:
                logger.warning(f"Could not verify {symbol} position qty: {e}")
                # If we can't verify, try with what we have but be cautious

            if actual_qty <= 0:
                logger.warning(f"⚠️ {symbol}: No position to close (qty={actual_qty})")
                del self.active_positions[symbol]
                return

            # Log exit trigger to activity feed
            if activity:
                activity.log_exit_trigger(symbol, reason, pnl_pct)

            # Place closing order
            opposite_side = "sell" if position["side"] == "buy" else "buy"

            if activity:
                activity.log_order_submit(symbol, opposite_side, actual_qty, price)

            order = await self._place_crypto_order(
                symbol=symbol,
                side=opposite_side,
                quantity=actual_qty,
                order_type="market",
            )

            if order:
                # Update metrics
                qty_dec = position.get("quantity_dec")
                if qty_dec is None:
                    qty_dec = Decimal(str(position["quantity"]))
                price_dec = position.get("entry_price_dec")
                if price_dec is None:
                    price_dec = Decimal(str(position["entry_price"]))
                profit = float(qty_dec * price_dec * Decimal(str(pnl_pct)))
                self.daily_profit += profit
                self.total_trades += 1

                if pnl_pct > 0:
                    self.wins += 1

                self.win_rate = (
                    self.wins / self.total_trades if self.total_trades > 0 else 0
                )

                # Remove from active positions
                del self.active_positions[symbol]

                logger.info(
                    f"✅ Closed position: {symbol} | Reason: {reason} | P&L: {pnl_pct:.2%} | Profit: ${profit:.2f}"
                )

                # Record exit for learning
                try:
                    learner = get_trade_learner()
                    indicators = (
                        self.scanner.get_indicators(symbol) if self.scanner else {}
                    )
                    learner.record_exit(
                        symbol=symbol,
                        exit_price=price,
                        exit_reason=reason,
                        indicators=indicators,
                    )
                except Exception as learn_err:
                    logger.debug(f"Could not record exit for learning: {learn_err}")

                # Log exit trade to activity feed
                if activity:
                    activity.log_exit(symbol, reason, profit, pnl_pct)

                # Log the exit trade with actual P&L to TradeStore
                exit_trade_log = TradeLog(
                    timestamp=datetime.now().isoformat(),
                    action=opposite_side.upper(),
                    symbol=symbol,
                    quantity=position["quantity"],
                    price=price,
                    status="filled",
                    error_notes=f"EXIT:{reason}",
                    order_id=order.id if hasattr(order, "id") else str(order),
                    pnl=profit,  # Record actual realized P&L
                    execution_time_ms=int((time.time() - start_time) * 1000),
                )
                self._log_trade(exit_trade_log)

        except APIError as e:
            logger.error(f"Alpaca API error executing exit for {symbol}: {e}")
        except KeyError as e:
            logger.error(f"Position not found for {symbol}: {e}")
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Network error executing exit for {symbol}: {e}")
        except (ZeroDivisionError, ValueError, TypeError) as e:
            logger.warning(f"Calculation error in exit for {symbol}: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error executing exit for {symbol}: {e}")

    def reset_daily_limits(self):
        """Reset daily trading limits - allows trading to resume"""
        old_profit = self.daily_profit
        old_trades = self.daily_trades
        self.daily_profit = 0.0
        self.daily_trades = 0
        logger.info(
            f"🔄 Daily limits reset. Previous: ${old_profit:.2f} P&L, {old_trades} trades"
        )
        return {
            "previous_daily_profit": old_profit,
            "previous_daily_trades": old_trades,
            "new_daily_profit": self.daily_profit,
            "new_daily_trades": self.daily_trades,
        }

    async def _place_crypto_order(
        self, symbol: str, side: str, quantity: float, order_type: str = "market"
    ):
        """Place crypto order via Alpaca API - compatible with both alpaca_trade_api and alpaca-py"""
        try:
            # Convert symbol format if needed (BTC/USD -> BTCUSD)
            alpaca_symbol = symbol.replace("/", "")

            api = self._api

            # Check if using newer alpaca-py SDK (has submit_order with order_data param)
            # or older alpaca_trade_api (uses positional/keyword args directly)
            try:
                # Try newer alpaca-py SDK first
                from alpaca.trading.requests import MarketOrderRequest
                from alpaca.trading.enums import OrderSide, TimeInForce

                order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
                order_request = MarketOrderRequest(
                    symbol=alpaca_symbol,
                    qty=quantity,
                    side=order_side,
                    time_in_force=TimeInForce.IOC,
                )
                order = api.submit_order(order_data=order_request)
                return order
            except (ImportError, TypeError):
                # Fall back to older alpaca_trade_api format
                order = api.submit_order(
                    symbol=alpaca_symbol,
                    qty=quantity,
                    side=side.lower(),
                    type=order_type,
                    time_in_force="ioc",  # Immediate or cancel for crypto
                )
                return order

        except APIError as e:
            logger.error(f"Alpaca API error placing order for {symbol}: {e}")
            return None
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Network error placing order for {symbol}: {e}")
            return None
        except (ImportError, TypeError) as e:
            logger.error(f"SDK compatibility error placing order for {symbol}: {e}")
            return None
        except ValueError as e:
            logger.error(f"Invalid order parameters for {symbol}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error placing order for {symbol}: {e}")
            return None

    async def _place_crypto_order_with_retry(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        max_retries: int = 3,
    ):
        """Place crypto order with retry logic for transient failures"""
        for attempt in range(max_retries):
            try:
                order = await self._place_crypto_order(
                    symbol, side, quantity, order_type
                )
                if order:
                    return order

            except APIError as e:
                if hasattr(e, "code") and e.code == 429:
                    # Rate limit - wait longer
                    wait_time = min(60, 2**attempt * 5)
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry")
                    await asyncio.sleep(wait_time)
                elif attempt < max_retries - 1:
                    # Other API errors - exponential backoff
                    wait_time = 2**attempt
                    logger.warning(
                        f"Retrying order after {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise

            except ConnectionError as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(f"Connection error, retrying after {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise

        return None

    async def _handle_rate_limit(self):
        """Handle API rate limit errors with exponential backoff"""
        if self.rate_limit_errors > 5:
            logger.critical("Too many rate limit errors, pausing trading for 5 minutes")
            await asyncio.sleep(300)  # 5 minutes
            self.rate_limit_errors = 0
        else:
            wait_time = min(60, 2**self.rate_limit_errors)
            logger.warning(f"Rate limit: waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)

    async def _handle_connection_error(self):
        """Handle connection errors with reconnection logic"""
        self.reconnect_attempts += 1

        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.critical("Max reconnection attempts reached, stopping bot")
            self.is_running = False
            return

        wait_time = min(60, 2**self.reconnect_attempts)
        logger.info(
            f"Reconnecting in {wait_time} seconds (attempt {self.reconnect_attempts})"
        )
        await asyncio.sleep(wait_time)

        # Reset on successful operations
        self.reconnect_attempts = 0

    def _log_trade(self, trade_log: TradeLog):
        """Log trade to console and file with timeline format"""
        # Add to in-memory log
        self.trade_log.append(trade_log)

        # Print to console with formatting
        print(trade_log.to_console_string())

        # Write to file as JSON for analysis
        try:
            with open(self.log_file, "a") as f:
                # Convert to dict and handle UUID serialization
                trade_dict = asdict(trade_log)
                # Convert UUID to string if present
                if "order_id" in trade_dict and trade_dict["order_id"]:
                    trade_dict["order_id"] = str(trade_dict["order_id"])
                f.write(json.dumps(trade_dict) + "\n")
        except Exception as e:
            logger.error(f"Failed to write trade log to file: {e}")

        # Update metrics
        if trade_log.status == "filled":
            self.daily_trades += 1
            self.total_trades += 1
            try:
                TradeStore.record_trade(
                    symbol=trade_log.symbol,
                    side=trade_log.action.lower(),
                    qty=trade_log.quantity,
                    price=trade_log.price,
                    pnl=trade_log.pnl,
                    order_id=trade_log.order_id or None,
                    timestamp=trade_log.timestamp,
                )
            except Exception as exc:
                logger.error("Failed to persist trade log: %s", exc)

    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            # Get from price data
            with self.scanner.lock:
                if (
                    symbol in self.scanner.price_data
                    and self.scanner.price_data[symbol]
                ):
                    return self.scanner.price_data[symbol][-1]
            return None
        except (KeyError, IndexError, TypeError):
            return None

    def _start_market_data_feed(self):
        """Start RATE-LIMIT-AWARE polling feed for real market data

        Alpaca limits: 200 requests/minute
        Strategy:
        - Individual requests with delays (more reliable than batch)
        - 10 symbols × 2 requests/min = 20 requests/min for data
        - Leaves 180 requests/min for trading operations
        """
        import threading
        from alpaca_trade_api.rest import TimeFrame

        def poll_market_data():
            logger.info("📡 Starting RATE-LIMIT-AWARE market data polling...")
            logger.info("   Strategy: Individual requests with delays, 30-sec cycle")

            # Get focused symbol list (top 10 most liquid)
            all_symbols = self.scanner.get_enabled_symbols()
            priority_symbols = [
                "BTCUSD",
                "ETHUSD",
                "SOLUSD",
                "DOGEUSD",
                "LTCUSD",
                "AVAXUSD",
                "LINKUSD",
                "UNIUSD",
                "XRPUSD",
                "DOTUSD",
            ]
            focused_symbols = [s for s in priority_symbols if s in all_symbols][:10]
            logger.info(f"   Focused on {len(focused_symbols)} symbols")

            # Initial history fetch - individual requests with delays
            logger.info(f"📥 Loading initial history...")
            for symbol in focused_symbols:
                try:
                    api_symbol = symbol[:-3] + "/" + symbol[-3:]
                    end = datetime.now(timezone.utc)
                    start = end - timedelta(minutes=120)

                    bars = self._api.get_crypto_bars(
                        api_symbol,
                        TimeFrame.Minute,
                        start=start.isoformat(),
                        end=end.isoformat(),
                    ).df

                    if not bars.empty:
                        for idx, row in bars.iterrows():
                            self.scanner.update_market_data(
                                symbol, float(row["close"]), float(row["volume"])
                            )
                        logger.info(f"  ✅ {symbol}: {len(bars)} bars")

                    time.sleep(0.5)  # 500ms delay between requests

                except Exception as e:
                    logger.warning(f"  ⚠️ {symbol}: {e}")

            logger.info(f"✅ Initial data load complete")

            # Main polling loop - RATE LIMIT AWARE
            poll_interval = 30  # Full cycle every 30 seconds

            while self.is_running:
                try:
                    end = datetime.now(timezone.utc)
                    start = end - timedelta(minutes=5)
                    updates = 0

                    for symbol in focused_symbols:
                        try:
                            api_symbol = symbol[:-3] + "/" + symbol[-3:]
                            bars = self._api.get_crypto_bars(
                                api_symbol,
                                TimeFrame.Minute,
                                start=start.isoformat(),
                                end=end.isoformat(),
                            ).df

                            if not bars.empty:
                                latest = bars.iloc[-1]
                                self.scanner.update_market_data(
                                    symbol,
                                    float(latest["close"]),
                                    float(latest["volume"]),
                                )
                                updates += 1

                            time.sleep(0.3)  # 300ms between requests

                        except Exception as e:
                            if "429" in str(e):
                                logger.warning(f"⚠️ Rate limit, backing off...")
                                time.sleep(10)

                    if updates > 0:
                        logger.info(
                            f"📊 Updated {updates}/{len(focused_symbols)} symbols"
                        )

                    # Wait remaining time in cycle
                    time.sleep(max(1, poll_interval - len(focused_symbols) * 0.3))

                except Exception as e:
                    logger.error(f"Polling error: {e}")
                    time.sleep(poll_interval)

        threading.Thread(target=poll_market_data, daemon=True).start()
        logger.info("📊 Rate-limit-aware polling started")

    def _update_metrics(self):
        """Update trading metrics"""
        current_time = datetime.now()

        # Reset daily metrics at midnight
        if current_time.hour == 0 and current_time.minute == 0:
            self.daily_trades = 0
            self.daily_profit = 0.0

        logger.info(
            f"📈 Metrics: Active Positions: {len(self.active_positions)} | "
            f"Daily P&L: ${self.daily_profit:.2f} | Win Rate: {self.win_rate:.1%} | "
            f"Total Trades: {self.total_trades}"
        )

    def get_status(self) -> Dict:
        """Get current bot status with detailed position info for frontend"""
        position_count = len(self.active_positions)
        total_unrealized_pnl = 0.0
        positions_detail = []

        for symbol, pos in self.active_positions.items():
            try:
                entry_price = pos.get("entry_price", 0)
                current_price = pos.get("current_price", entry_price)
                quantity = float(pos.get("quantity", 0))

                # Try to get real-time price from Alpaca
                try:
                    alpaca_pos = self.alpaca.get_position(symbol)
                    current_price = float(alpaca_pos.current_price)
                    unrealized_pnl = float(alpaca_pos.unrealized_pl)
                except Exception:
                    # Calculate from cached data
                    if entry_price > 0:
                        if pos.get("side") == "buy":
                            unrealized_pnl = (current_price - entry_price) * quantity
                        else:
                            unrealized_pnl = (entry_price - current_price) * quantity
                    else:
                        unrealized_pnl = 0

                # Calculate P&L percentage
                if entry_price > 0:
                    if pos.get("side") == "buy":
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                    else:
                        pnl_pct = ((entry_price - current_price) / entry_price) * 100
                else:
                    pnl_pct = 0

                total_unrealized_pnl += unrealized_pnl

                # Calculate hold time
                entry_time = pos.get("entry_time")
                if isinstance(entry_time, datetime):
                    hold_time_seconds = int(
                        (datetime.now() - entry_time).total_seconds()
                    )
                else:
                    hold_time_seconds = 0

                positions_detail.append(
                    {
                        "symbol": symbol,
                        "side": pos.get("side", "buy"),
                        "entry_price": entry_price,
                        "current_price": current_price,
                        "quantity": quantity,
                        "stop_price": pos.get("stop_price", 0),
                        "target_price": pos.get("target_price", 0),
                        "pnl_pct": round(pnl_pct, 2),
                        "unrealized_pnl": round(unrealized_pnl, 4),
                        "hold_time_seconds": hold_time_seconds,
                    }
                )
            except Exception as e:
                logger.error(f"Error getting status for {symbol}: {e}")

        return {
            "is_running": self.is_running,
            "bot_running": self.is_running,  # For frontend compatibility
            "active_positions": position_count,
            "active_positions_count": position_count,  # Frontend expects this name
            "daily_profit": self.daily_profit,
            "daily_trades": self.daily_trades,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "positions": positions_detail,  # Full position objects for frontend
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "error_count": self.error_count,
            "rate_limit_errors": self.rate_limit_errors,
            "recent_trades": len(self.trade_log),
        }

    def print_trade_timeline(self, last_n: int = 20):
        """Print formatted trade timeline to console"""
        print("\n" + "=" * 100)
        print(
            "📊 TRADE TIMELINE (Last {} Trades)".format(
                min(last_n, len(self.trade_log))
            )
        )
        print("=" * 100)

        if not self.trade_log:
            print("No trades executed yet")
        else:
            # Print header
            print(
                f"{'Time':<20} {'Action':<6} {'Symbol':<10} {'Qty':<10} {'Price':<12} {'Status':<15} {'P&L':<10} {'Notes'}"
            )
            print("-" * 100)

            # Print recent trades
            for trade in self.trade_log[-last_n:]:
                print(trade.to_console_string())

        # Print summary statistics
        print("\n" + "=" * 100)
        print("📈 TRADING SUMMARY")
        print("-" * 100)

        filled_trades = [t for t in self.trade_log if t.status == "filled"]
        failed_trades = [t for t in self.trade_log if t.status == "failed"]

        print(f"Total Trades Attempted: {len(self.trade_log)}")
        print(f"Successful Trades: {len(filled_trades)}")
        print(f"Failed Trades: {len(failed_trades)}")

        if filled_trades:
            total_pnl = sum(t.pnl for t in filled_trades)
            avg_exec_time = sum(t.execution_time_ms for t in filled_trades) / len(
                filled_trades
            )
            print(f"Total P&L: ${total_pnl:+,.2f}")
            print(f"Average Execution Time: {avg_exec_time:.0f}ms")

        if failed_trades:
            print("\n⚠️ ERROR SUMMARY:")
            error_counts = {}
            for trade in failed_trades:
                error = (
                    trade.error_notes.split(":")[0] if trade.error_notes else "Unknown"
                )
                error_counts[error] = error_counts.get(error, 0) + 1

            for error, count in sorted(
                error_counts.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {error}: {count} occurrences")

        print("=" * 100 + "\n")

    def stop(self):
        """Stop the trading bot and print final summary"""
        logger.info("🛑 Stopping Crypto Day Trading Bot")
        self.is_running = False
        self.executor.shutdown(wait=True)

        # Print final trade timeline
        self.print_trade_timeline(last_n=50)


# Integration function for the main bot
def create_crypto_day_trader(
    alpaca_client, config: TradingConfig
) -> CryptoDayTradingBot:
    """Create and configure crypto day trading bot."""

    bot = CryptoDayTradingBot(
        alpaca_client,
        config.investment_amount,
        scanner_config=config.crypto_scanner,
        enabled_symbols=config.symbols,
    )

    risk_settings = config.risk_management
    position_ratio = risk_settings.max_position_size or 0.05
    bot.max_position_size = config.investment_amount * position_ratio
    bot.max_concurrent_positions = config.max_trades_active
    bot.min_profit_target = 0.003
    bot.max_daily_loss = config.investment_amount * (
        risk_settings.max_daily_loss or RISK.MAX_DAILY_LOSS
    )

    logger.info(
        "Crypto day trader configured with %d scanner symbols (defaults merged with overrides)",
        len(bot.scanner.get_enabled_symbols()),
    )

    return bot
