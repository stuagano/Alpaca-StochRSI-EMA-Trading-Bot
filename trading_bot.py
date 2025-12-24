import logging
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import alpaca_trade_api as tradeapi
from trading_executor import TradingExecutor, TradingSignal
from signal_processor import SignalProcessor
from config.unified_config import get_config, TradingConfig
from core.signal_filters import ensure_signal_filters
from utils.alpaca import load_alpaca_credentials
from strategies.base_strategy import Strategy

logger = logging.getLogger(__name__)


class TradingBot:
    def __init__(
        self,
        config: TradingConfig,
        strategy: Strategy,
        signal_processor: SignalProcessor,
        data_manager: Any
    ) -> None:
        """
        Initialize the TradingBot with modular dependencies.

        Args:
            config: TradingConfig object
            strategy: Strategy instance (e.g., StochRSIStrategy)
            signal_processor: SignalProcessor instance
            data_manager: Data manager service (e.g., AlpacaDataService)
        """
        self.config = config
        self.strategy = strategy
        self.signal_processor = signal_processor
        self.data_manager = data_manager

        # Status tracking
        self._running = False
        self._start_time: Optional[datetime] = None
        self._trade_count = 0
        self._signal_count = 0
        self._last_signal_time: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._positions: List[Dict] = []

        logger.info(f"TradingBot initialized with {self.strategy.name} strategy.")

    def get_status(self) -> Dict[str, Any]:
        """Get current bot status for dashboard display."""
        return {
            'is_running': self._running,
            'start_time': self._start_time.isoformat() if self._start_time else None,
            'uptime_seconds': (datetime.now() - self._start_time).total_seconds() if self._start_time else 0,
            'strategy': self.strategy.name if hasattr(self.strategy, 'name') else 'unknown',
            'symbols': self.config.symbols or [],
            'total_trades': self._trade_count,
            'total_signals': self._signal_count,
            'last_signal_time': self._last_signal_time.isoformat() if self._last_signal_time else None,
            'last_error': self._last_error,
            'positions': self._positions,
        }

    def stop(self) -> None:
        """Stop the trading bot."""
        logger.info("TradingBot stopping...")
        self._running = False

    async def run(self) -> None:
        """Main bot execution loop using standardized strategy interface."""
        self._running = True
        self._start_time = datetime.now()
        logger.info("TradingBot running.")

        while self._running:
            try:
                # 1. Fetch real-time data for configured symbols
                symbols = self.config.symbols or ['BTC/USD']
                for symbol in symbols:
                    if not self._running:
                        break

                    # Fetch OHLCV data via data_manager
                    df = self.data_manager.get_market_data(symbol)

                    if df is None or df.empty:
                        logger.debug(f"No data available for {symbol}")
                        continue

                    # 2. Generate signals using the standardized strategy
                    signals = self.strategy.generate_signals(df)

                    # 3. Process signals and execute trades
                    for sig_data in signals:
                        self._signal_count += 1
                        self._last_signal_time = datetime.now()

                        # Convert dict to TradingSignal object
                        signal = TradingSignal(
                            symbol=sig_data["symbol"],
                            action=sig_data["action"].upper(),
                            strength=sig_data.get("strength", 50.0) if isinstance(sig_data.get("strength"), (int, float)) else 50.0,
                            price=sig_data["price"],
                            timestamp=sig_data["timestamp"],
                            reason=sig_data["reason"],
                            indicators=sig_data.get("indicators", {})
                        )

                        logger.info(f"Generated signal: {signal.action} {signal.symbol} at {signal.price}")
                        execution_result = await self.signal_processor.process_signal(signal.symbol, sig_data)

                        if execution_result:
                            self._trade_count += 1
                            logger.info(f"Trade successfully executed for {signal.symbol}")

                # Clear last error on successful iteration
                self._last_error = None

            except Exception as e:
                self._last_error = str(e)
                logger.error(f"Error in TradingBot loop: {e}", exc_info=True)

            await asyncio.sleep(60)  # Standard poll interval

        logger.info("TradingBot stopped.")
