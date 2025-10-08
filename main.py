import logging
import os
import signal
import sys
from typing import Optional

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
from utils.logging_config import setup_logging

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


def setup_signal_handlers(bot: Optional[TradingBot] = None):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        
        if bot:
            logger.info("Stopping trading bot...")
            # Add any bot cleanup here if needed
        
        logger.info("Cleaning up services...")
        cleanup_service_registry()
        
        logger.info("Shutdown complete")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main entry point for the trading bot."""
    bot = None
    
    try:
        # Load configuration
        config = get_config()
        
        # Setup logging
        setup_logging()
        _enable_metrics_if_configured()
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
        logger.info("Performing cleanup...")
        cleanup_service_registry()
        logger.info("Main process completed")


if __name__ == "__main__":
    main()
