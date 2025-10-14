#!/usr/bin/env python3
"""
Services Module
Business logic layer for Flask application
"""

import logging
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.api.services.trading_service import TradingService
from backend.api.services.pnl_service import PnLService
from backend.api.services.alpaca_client import AlpacaClient
from utils.alpaca import load_alpaca_credentials


def _sqlite_path_from_url(db_url: str) -> str:
    if db_url.startswith('sqlite:///'):
        return db_url.replace('sqlite:///', '', 1)
    return db_url

logger = logging.getLogger(__name__)

def init_services(app):
    """
    Initialize all services and attach to app context

    Args:
        app: Flask application instance
    """
    # Initialize Alpaca client
    trading_config = app.config['TRADING_CONFIG']
    credentials = load_alpaca_credentials(trading_config)
    app.alpaca_client = AlpacaClient(credentials)

    # Initialize trading service
    app.trading_service = TradingService(
        alpaca_client=app.alpaca_client,
        config=trading_config
    )

    # Initialize P&L service
    db_path = _sqlite_path_from_url(trading_config.database.url)
    app.pnl_service = PnLService(
        alpaca_client=app.alpaca_client,
        db_path=db_path
    )

    # Register with service registry if available
    try:
        from core.service_registry import ServiceRegistry
        registry = ServiceRegistry()

        registry.register('alpaca_client', app.alpaca_client)
        registry.register('trading_service', app.trading_service)
        registry.register('pnl_service', app.pnl_service)

        app.service_registry = registry
        logger.info("Services registered with service registry")
    except ImportError:
        logger.warning("Service registry not available, using direct service attachment")

    logger.info("Services initialized successfully")

__all__ = [
    'init_services',
    'TradingService',
    'PnLService',
    'AlpacaClient'
]
