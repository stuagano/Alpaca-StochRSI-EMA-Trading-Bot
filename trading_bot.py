import logging
import asyncio
import alpaca_trade_api as tradeapi
from trading_executor import TradingExecutor, TradingSignal
from signal_processor import SignalProcessor
from config.unified_config import get_config
from core.signal_filters import ensure_signal_filters
from utils.alpaca import load_alpaca_credentials

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, data_manager, strategy):
        self.data_manager = data_manager
        self.strategy = strategy
        self.config = get_config() # Get the full configuration

        # Read Alpaca API credentials from file
        creds = load_alpaca_credentials(self.config)
        self.alpaca_api = tradeapi.REST(creds.key_id, creds.secret_key, creds.base_url)

        # Initialize TradingExecutor
        # Assuming trading config is under 'trading' attribute of the main config
        self.trading_executor = TradingExecutor(self.alpaca_api, self.config)

        # Initialize SignalProcessor with signal filter configuration
        signal_config = ensure_signal_filters(self.config)
        self.signal_processor = SignalProcessor(self.trading_executor, signal_config)

        logger.info("TradingBot initialized.")

    async def run(self):
        logger.info("TradingBot running.")
        while True:
            # 1. Fetch data (placeholder for now)
            # In a real scenario, data_manager would fetch real-time data
            # For POC, we'll simulate data or use historical data
            data = {"symbol": "BTC/USD", "price": 30000.0, "timestamp": "2025-09-11T12:00:00Z"} # Placeholder

            # 2. Generate signals
            # The strategy would analyze data and produce signals
            # For POC, we'll simulate a signal
            signal_data = {
                "signal": "BUY",
                "strength": 80,
                "price": data["price"],
                "reason": "StochRSI crossover",
                "indicators": {"rsi": 30, "stoch_rsi": 20}
            }
            # Create TradingSignal object - this needs to be imported or defined
            # For now, I'll assume it's defined in signal_processor.py
            signal = TradingSignal(
                symbol=data["symbol"],
                action=signal_data["signal"],
                strength=signal_data["strength"],
                price=signal_data["price"],
                timestamp=data["timestamp"],
                reason=signal_data["reason"],
                indicators=signal_data["indicators"]
            )

            # 3. Process signal and execute trade
            # This will call the TradingExecutor
            execution_result = await self.signal_processor.process_signal(signal.symbol, signal_data)

            if execution_result:
                logger.info(f"Trade executed: {execution_result}")
            else:
                logger.info("No trade executed.")

            await asyncio.sleep(5) # Run every 5 seconds for POC) # Run every 5 seconds for POC
