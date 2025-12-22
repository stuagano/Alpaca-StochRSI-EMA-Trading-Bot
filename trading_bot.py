import logging
import asyncio
from typing import Any, Optional

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
        
        logger.info(f"TradingBot initialized with {self.strategy.name} strategy.")

    async def run(self) -> None:
        """Main bot execution loop using standardized strategy interface."""
        logger.info("TradingBot running.")
        while True:
            try:
                # 1. Fetch real-time data for configured symbols
                symbols = self.config.symbols or ['BTC/USD']
                for symbol in symbols:
                    # Fetch OHLCV data via data_manager
                    df = self.data_manager.get_market_data(symbol)
                    
                    if df is None or df.empty:
                        logger.debug(f"No data available for {symbol}")
                        continue
                        
                    # 2. Generate signals using the standardized strategy
                    signals = self.strategy.generate_signals(df)
                    
                    # 3. Process signals and execute trades
                    for sig_data in signals:
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
                            logger.info(f"Trade successfully executed for {signal.symbol}")
            
            except Exception as e:
                logger.error(f"Error in TradingBot loop: {e}", exc_info=True)

            await asyncio.sleep(60)  # Standard poll interval
