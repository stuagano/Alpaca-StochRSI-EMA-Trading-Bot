"""Service wiring for the Flask backend with dependency injection via ServiceRegistry."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from utils.alpaca import load_alpaca_credentials
from core.service_registry import get_service_registry
from utils.trade_store import TradeStore
from core.alpaca_data_service import AlpacaDataService
from core.scanner_service import ScannerService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Trading service import with graceful degradation
# ---------------------------------------------------------------------------
try:
    from .trading_service import TradingService as _TradingServiceImpl
except Exception as exc:  # pragma: no cover - optional dependency fallback
    _TRADING_IMPORT_ERROR = exc

    class TradingService:  # type: ignore[override]
        """Fallback trading service used when the real implementation is unavailable."""

        def __init__(self, *_, **__) -> None:
            self.is_trading = False
            logger.warning("TradingService fallback active: %s", _TRADING_IMPORT_ERROR)

        def _message(self) -> str:
            return f"Trading service unavailable: {_TRADING_IMPORT_ERROR}"

        def start_trading(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            return {"status": "unavailable", "config": {}, "message": self._message()}

        def stop_trading(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            return {"status": "unavailable", "positions_closed": 0, "message": self._message()}

        def place_order(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            return {"status": "unavailable", "reason": self._message()}

        def close_position(self, *_args: Any, **_kwargs: Any) -> Optional[Dict[str, Any]]:
            return None

        def close_all_positions(self, *_args: Any, **_kwargs: Any) -> List[Dict[str, Any]]:
            return []

        def update_strategy(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            return {"strategy": None, "parameters": {}, "message": self._message()}

        def get_positions(self, *_args: Any, **_kwargs: Any) -> List[Dict[str, Any]]:
            return []

        def calculate_signals(self, *_args: Any, **_kwargs: Any) -> List[Dict[str, Any]]:
            return []

        def get_orders(self, *_args: Any, **_kwargs: Any) -> List[Dict[str, Any]]:
            return []

        def get_account_data(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            return {
                "status": "unavailable",
                "buying_power": 0,
                "portfolio_value": 0,
                "cash": 0,
                "equity": 0,
                "pattern_day_trader": False,
                "trading_blocked": False,
                "account_blocked": False,
            }

        def get_system_status(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            return {
                "last_update": None,
                "market_status": "UNKNOWN",
                "is_trading": False,
                "services": {"trading": "unavailable"},
            }

    TradingService.__module__ = __name__
else:  # pragma: no cover - real implementation available
    TradingService = _TradingServiceImpl


# ---------------------------------------------------------------------------
# P&L service import with graceful degradation
# ---------------------------------------------------------------------------
try:
    from .pnl_service import PnLService as _PnLServiceImpl
except Exception as exc:  # pragma: no cover
    _PNL_IMPORT_ERROR = exc

    class PnLService:  # type: ignore[override]
        """Fallback P&L service returning safe default structures."""

        def __init__(self, *_, **kwargs: Any) -> None:
            self.db_path = kwargs.get("db_path", "database/crypto_trading.db")
            logger.warning("PnLService fallback active: %s", _PNL_IMPORT_ERROR)

        def _message(self) -> str:
            return f"PnL service unavailable: {_PNL_IMPORT_ERROR}"

        def get_current_pnl(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            return {
                "daily_pnl": 0,
                "total_pnl": 0,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "win_rate": 0,
                "positions": [],
                "message": self._message(),
            }

        def get_pnl_history(self, *_args: Any, **_kwargs: Any) -> List[Dict[str, Any]]:
            return []

        def get_chart_data(self, *_args: Any, **_kwargs: Any) -> Dict[str, List[Any]]:
            return {"labels": [], "daily_pnl": [], "cumulative_pnl": []}

        def calculate_statistics(self, *_args: Any, **_kwargs: Any) -> Dict[str, Any]:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "average_win": 0,
                "average_loss": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "best_day": None,
                "worst_day": None,
                "current_streak": 0,
                "max_streak": 0,
                "message": self._message(),
            }

        def get_export_data(self, *_args: Any, **_kwargs: Any) -> List[Dict[str, Any]]:
            return []

        def get_recent_trades(self, *_args: Any, **_kwargs: Any) -> List[Dict[str, Any]]:
            return []

        def get_performance_by_symbol(self, *_args: Any, **_kwargs: Any) -> Dict[str, Dict[str, Any]]:
            return {}

    PnLService.__module__ = __name__
else:  # pragma: no cover
    PnLService = _PnLServiceImpl


# ---------------------------------------------------------------------------
# Alpaca client import with graceful degradation
# ---------------------------------------------------------------------------
try:
    from .alpaca_client import AlpacaClient as _AlpacaClientImpl
except Exception as exc:  # pragma: no cover
    _ALPACA_IMPORT_ERROR = exc

    class AlpacaClient:  # type: ignore[override]
        """Fallback Alpaca client that keeps the API surface minimal."""

        def __init__(self, *_, **__) -> None:
            self.api = None
            logger.warning("AlpacaClient fallback active: %s", _ALPACA_IMPORT_ERROR)

        def is_connected(self) -> bool:
            return False

        def reconnect(self) -> None:
            raise RuntimeError(f"Alpaca client unavailable: {_ALPACA_IMPORT_ERROR}") from _ALPACA_IMPORT_ERROR

    AlpacaClient.__module__ = __name__
else:  # pragma: no cover
    AlpacaClient = _AlpacaClientImpl


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _sqlite_path_from_url(db_url: str) -> str:
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "", 1)
    return db_url


# ---------------------------------------------------------------------------
# Public service initialiser
# ---------------------------------------------------------------------------
def init_services(app) -> None:
    """Initialise core services and attach them to the Flask ``app``.

    All services are registered with a mandatory ServiceRegistry for consistent
    dependency injection. The database path is resolved from unified configuration.
    """
    if "TRADING_CONFIG" not in app.config:
        raise KeyError("TRADING_CONFIG missing from app.config; cannot initialise services")

    trading_config = app.config["TRADING_CONFIG"]
    logger.info("Initialising backend services")

    # Set up logging from unified configuration
    try:
        from config.unified_config import setup_logging
        setup_logging(trading_config)
    except Exception as exc:
        logger.warning("Failed to configure logging from unified config: %s", exc)

    # Resolve database path from config
    database_url = getattr(getattr(trading_config, "database", None), "url", "")
    db_path = _sqlite_path_from_url(database_url) if database_url else "database/crypto_trading.db"
    if not database_url:
        logger.warning("Trading config missing database URL; defaulting to %s", db_path)

    # Configure TradeStore with unified database path
    TradeStore.configure(db_path)
    logger.info("TradeStore configured with database: %s", db_path)

    # Use global service registry singleton (mandatory)
    registry = get_service_registry()
    app.service_registry = registry

    # Initialise Alpaca client
    try:
        credentials = load_alpaca_credentials(trading_config)
        alpaca_client = AlpacaClient(credentials)
        registry.register("alpaca_client", alpaca_client)
        logger.info("Alpaca client initialised successfully")
    except Exception as exc:
        logger.warning("Failed to initialise Alpaca client: %s", exc)
        logger.warning("Running without Alpaca API - some features will be unavailable")
        alpaca_client = None
    app.alpaca_client = alpaca_client

    # Initialise data manager for market data
    data_manager = None
    if alpaca_client:
        try:
            # AlpacaCredentials uses 'key_id' not 'api_key'
            data_manager = AlpacaDataService(
                api_key=getattr(credentials, 'key_id', ''),
                secret_key=getattr(credentials, 'secret_key', ''),
                base_url=getattr(credentials, 'base_url', 'https://paper-api.alpaca.markets')
            )
            registry.register("data_manager", data_manager)
            logger.info("AlpacaDataService registered as data_manager")
        except Exception as exc:
            logger.warning("Failed to initialise data_manager: %s", exc)
    app.data_manager = data_manager

    # Initialise trading service
    trading_service = (
        TradingService(alpaca_client=alpaca_client, config=trading_config)
        if alpaca_client
        else None
    )
    if trading_service:
        registry.register("trading_service", trading_service)
    app.trading_service = trading_service

    # Initialise P&L service
    pnl_service = PnLService(alpaca_client=alpaca_client, db_path=db_path) if alpaca_client else None
    if pnl_service:
        registry.register("pnl_service", pnl_service)
    app.pnl_service = pnl_service

    # Register config in registry for easy access
    registry.register("trading_config", trading_config)
    registry.register("db_path", db_path)

    # Initialize and register centralized ScannerService
    try:
        scanner_config = getattr(trading_config, 'crypto_scanner', None)
        symbols = getattr(trading_config, 'symbols', None)
        scanner_service = ScannerService(config=scanner_config, enabled_symbols=symbols)
        registry.register("scanner_service", scanner_service)
        logger.info("ScannerService initialized with %d symbols", len(scanner_service.get_enabled_symbols()))
    except Exception as exc:
        logger.warning("Failed to initialize ScannerService: %s", exc)

    logger.info("Services initialised and registered with ServiceRegistry")


__all__ = ["init_services", "TradingService", "PnLService", "AlpacaClient"]
