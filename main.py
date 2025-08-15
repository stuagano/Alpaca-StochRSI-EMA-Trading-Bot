import logging
import signal
import sys
from typing import Optional

from core.service_registry import get_service_registry, setup_core_services, cleanup_service_registry
from config.unified_config import get_config
from trading_bot import TradingBot
from strategies.stoch_rsi_strategy import StochRSIStrategy
from strategies.ma_crossover_strategy import MACrossoverStrategy
from utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


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
        logger.info("Starting Alpaca Trading Bot with unified architecture...")
        
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
        logger.info(f"System health check: {health_report['ready_services']}/{health_report['total_services']} services ready")
        
        # Start the bot
        logger.info("Starting trading bot execution...")
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
        raise
    finally:
        logger.info("Performing cleanup...")
        cleanup_service_registry()
        logger.info("Main process completed")


if __name__ == "__main__":
    main()
