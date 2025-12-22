import asyncio
import logging
import os
import signal
import sys
from typing import Optional, Union

try:
    from prometheus_client import Counter, Gauge, start_http_server
except ImportError:  # pragma: no cover - optional dependency
    Counter = None  # type: ignore[assignment]
    Gauge = None  # type: ignore[assignment]

    def start_http_server(_port: int) -> None:  # type: ignore[override]
        """Fallback when ``prometheus_client`` is not installed."""

        return

from core.service_registry import get_service_registry, setup_core_services, cleanup_service_registry
from config.unified_config import get_config
from config.environment import get_environment_config
from trading_bot import TradingBot
from trading_executor import TradingExecutor
from signal_processor import SignalProcessor
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from strategies.crypto_scalping_strategy import CryptoDayTradingBot, create_crypto_day_trader
from utils.logging_config import setup_logging
from utils.alpaca import load_alpaca_credentials
from services.swarm_learning_service import get_learning_service, start_learning_service

ALPACA_IMPORT_ERROR: Optional[Exception]

# Import Alpaca client - prefer legacy SDK for compatibility with existing strategy code
try:
    import alpaca_trade_api as tradeapi
    ALPACA_IMPORT_ERROR = None
except ImportError as e:
    logging.error("Failed to import alpaca_trade_api: %s", e)
    logging.error("Install alpaca_trade_api with 'pip install alpaca-trade-api' to enable live trading.")
    tradeapi = None  # type: ignore[assignment]
    ALPACA_IMPORT_ERROR = e

# Also try importing new SDK for potential future use
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import GetAssetsRequest
    from alpaca.data.historical import CryptoHistoricalDataClient
except ImportError:
    TradingClient = None  # type: ignore[assignment]
    GetAssetsRequest = None  # type: ignore[assignment]
    CryptoHistoricalDataClient = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


METRIC_BOT_STARTUPS = Counter("trading_bot_startups_total", "Number of trading bot startups") if Counter else None
METRIC_BOT_EXCEPTIONS = Counter("trading_bot_exceptions_total", "Number of unhandled exceptions in trading bot") if Counter else None
METRIC_READY_SERVICES = Gauge("trading_services_ready", "Number of ready services registered") if Gauge else None
METRIC_TOTAL_SERVICES = Gauge("trading_services_total", "Total services registered in the registry") if Gauge else None

_METRICS_INITIALISED = False


def _enable_metrics_if_configured() -> None:
    """Start the Prometheus exporter when metrics are enabled."""

    global _METRICS_INITIALISED
    if _METRICS_INITIALISED or METRIC_BOT_STARTUPS is None:
        return

    raw_toggle = os.getenv("ENABLE_PROMETHEUS_METRICS", "true").strip().lower()
    if raw_toggle not in {"1", "true", "yes", "on"}:
        return

    port = int(os.getenv("PROMETHEUS_EXPORTER_PORT", "9464"))
    start_http_server(port)
    METRIC_BOT_STARTUPS.inc()
    _METRICS_INITIALISED = True


from strategies import get_strategy


def setup_signal_handlers(bot: Optional[Union[TradingBot, CryptoDayTradingBot]] = None):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")

        if bot:
            if isinstance(bot, CryptoDayTradingBot):
                logger.info("Stopping crypto scalping bot...")
            else:
                logger.info("Stopping trading bot...")
            bot.stop()

        logger.info("Cleaning up services...")
        cleanup_service_registry()

        logger.info("Shutdown complete")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def create_alpaca_client(config):
    """Create Alpaca trading client from configuration using legacy SDK.

    Uses alpaca_trade_api (legacy SDK) for compatibility with strategy code
    that expects list_positions(), get_crypto_bars(), etc.
    """
    if tradeapi is None:  # pragma: no cover - optional dependency fallback
        raise RuntimeError(
            "alpaca_trade_api is not installed; unable to create Alpaca client"
        ) from ALPACA_IMPORT_ERROR

    try:
        creds = load_alpaca_credentials(config)

        # Use legacy REST API for full compatibility with existing strategy code
        trading_client = tradeapi.REST(
            creds.key_id,
            creds.secret_key,
            creds.base_url,
            api_version='v2'
        )

        # Verify connection
        account = trading_client.get_account()
        logger.info(f"Alpaca trading client initialized successfully (Account status: {account.status})")
        return trading_client

    except Exception as e:
        logger.error(f"Failed to create Alpaca client: {e}")
        raise


async def main():
    """Main entry point for the trading bot."""
    bot = None

    try:
        # Load configuration
        config = get_config()

        # Setup logging
        setup_logging()
        _enable_metrics_if_configured()

        # Check if we're using crypto scalping strategy
        if config.strategy == 'crypto_scalping':
            logger.info("🚀 Starting Crypto Scalping Bot - High Frequency Trading")

            # Create Alpaca client
            alpaca_client = create_alpaca_client(config)

            # Create crypto day trading bot
            bot = create_crypto_day_trader(alpaca_client, config)

            logger.info("Crypto scalping bot created and configured")

            # Setup signal handlers for graceful shutdown
            setup_signal_handlers(bot)

            if config.symbols:
                logger.info("Using configured symbols: %s", config.symbols)
            else:
                logger.info("No symbols configured, will use dynamic selection")

            # Start the swarm learning service for self-healing and pattern learning
            logger.info("🧠 Starting swarm learning service...")
            learning_service = await start_learning_service()
            logger.info("Swarm learning service active - trades will feed into pattern optimization")

            # Start the crypto scalping bot
            logger.info("🎯 Starting crypto scalping execution...")
            await bot.start_trading()

        else:
            logger.info("Starting Alpaca Trading Bot with unified architecture...")

            env_config = get_environment_config()
            logger.info("Runtime environment: %s", env_config.name.value)
            
            # Load credentials for services
            creds = load_alpaca_credentials(config)

            # Setup core services with real credentials
            logger.info("Initializing service registry with production services...")
            setup_core_services(api_key=creds.key_id, secret_key=creds.secret_key)

            # Get service registry
            registry = get_service_registry()

            # Start health monitoring
            registry.start_health_monitoring(check_interval=60.0)

            # Get services from registry
            data_manager = registry.get('data_manager')
            logger.info("Data manager service initialized")

            # Create strategy
            strategy = get_strategy(config.strategy, config)
            logger.info(f"Strategy initialized: {config.strategy}")

            # Initialize Executor and SignalProcessor
            # Use same REST client as other components
            alpaca_api = tradeapi.REST(creds.key_id, creds.secret_key, creds.base_url)
            executor = TradingExecutor(alpaca_api, config)
            processor = SignalProcessor(executor, config)

            # Create trading bot with dependency injection
            bot = TradingBot(
                config=config,
                strategy=strategy,
                signal_processor=processor,
                data_manager=data_manager
            )
            logger.info("Modular TradingBot initialized with dependency injection")

            # Setup signal handlers for graceful shutdown
            setup_signal_handlers(bot)

            # Log system health
            health_report = registry.get_health_report()
            logger.info(f"System health check: {health_report['ready_services']}/{health_report['total_services']} services ready")

            # Start the swarm learning service for self-healing and pattern learning
            logger.info("🧠 Starting swarm learning service...")
            learning_service = await start_learning_service()
            logger.info("Swarm learning service active - trades will feed into pattern optimization")

            # Start the bot
            logger.info("Starting trading bot execution...")
            await bot.run()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        if METRIC_BOT_EXCEPTIONS:
            METRIC_BOT_EXCEPTIONS.inc()
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise
    finally:
        if bot:
            bot.stop()
        logger.info("Trading bot shutdown completed")


if __name__ == "__main__":
    asyncio.run(main())
