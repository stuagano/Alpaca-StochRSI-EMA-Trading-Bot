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
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from strategies.crypto_scalping_strategy import CryptoDayTradingBot, create_crypto_day_trader
from utils.logging_config import setup_logging
from utils.alpaca import load_alpaca_credentials

ALPACA_IMPORT_ERROR: Exception | None

# Import Alpaca client
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import GetAssetsRequest
    from alpaca.data.historical import CryptoHistoricalDataClient
    ALPACA_IMPORT_ERROR = None
except ImportError as e:
    logging.error("Failed to import Alpaca modules: %s", e)
    logging.error("Install alpaca-py with 'pip install alpaca-py' to enable live trading.")
    TradingClient = None  # type: ignore[assignment]
    GetAssetsRequest = None  # type: ignore[assignment]
    CryptoHistoricalDataClient = None  # type: ignore[assignment]
    ALPACA_IMPORT_ERROR = e

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


def get_strategy(strategy_name: str, config):
    """Factory function to create strategy instances."""
    if strategy_name == 'StochRSI':
        return StochRSIStrategy(config)
    elif strategy_name == 'MACrossover':
        return MACrossoverStrategy(config)
    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")


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
    """Create Alpaca trading client from configuration."""
    if TradingClient is None:  # pragma: no cover - optional dependency fallback
        raise RuntimeError(
            "alpaca-py is not installed; unable to create Alpaca client"
        ) from ALPACA_IMPORT_ERROR

    try:
        creds = load_alpaca_credentials(config)

        trading_client = TradingClient(
            api_key=creds.key_id,
            secret_key=creds.secret_key,
            paper=creds.is_paper  # Always use paper trading for crypto scalping
        )

        logger.info("Alpaca trading client initialized successfully")
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
            bot = create_crypto_day_trader(alpaca_client, {
                'crypto_capital': config.investment_amount,
                'max_position_size': config.investment_amount * (config.risk_management.max_position_size or 0.05),
                'max_positions': config.max_trades_active,
                'min_profit': 0.003,  # 0.3% minimum profit
                'max_daily_loss': config.investment_amount * (config.risk_management.max_daily_loss or 0.02)
            })

            logger.info("Crypto scalping bot created and configured")

            # Setup signal handlers for graceful shutdown
            setup_signal_handlers(bot)

            # Initialize enabled symbols from config
            if hasattr(config, 'symbols') and config.symbols:
                bot.scanner.update_enabled_symbols(config.symbols)
                logger.info(f"Using configured symbols: {config.symbols}")
            else:
                # Fallback to dynamic symbol selection
                logger.info("No symbols configured, will use dynamic selection")

            # Start the crypto scalping bot
            logger.info("🎯 Starting crypto scalping execution...")
            await bot.start_trading()

        else:
            logger.info("Starting Alpaca Trading Bot with unified architecture...")

            env_config = get_environment_config()
            logger.info("Runtime environment: %s", env_config.name.value)
            if not env_config.enable_order_execution:
                logger.warning(
                    "Order execution is disabled for this environment. Set TRADING_ENABLE_EXECUTION=1"
                    " if you intend to place live orders."
                )

            # Setup core services
            logger.info("Initializing service registry...")
            setup_core_services()

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

            # Create trading bot
            bot = TradingBot(data_manager, strategy)
            logger.info("Trading bot initialized")

            # Setup signal handlers for graceful shutdown
            setup_signal_handlers(bot)

            # Log system health
            health_report = registry.get_health_report()
            if METRIC_READY_SERVICES and METRIC_TOTAL_SERVICES:
                METRIC_READY_SERVICES.set(health_report.get('ready_services', 0))
                METRIC_TOTAL_SERVICES.set(health_report.get('total_services', 0))
            logger.info(f"System health check: {health_report['ready_services']}/{health_report['total_services']} services ready")

            # Start the bot
            logger.info("Starting trading bot execution...")
            bot.run()

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
