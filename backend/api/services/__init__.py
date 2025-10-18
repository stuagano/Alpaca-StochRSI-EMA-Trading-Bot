"""Service wiring for the Flask backend with optional dependency fallbacks."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from utils.alpaca import load_alpaca_credentials

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
            self.db_path = kwargs.get("db_path", "database/trading_data.db")
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
    """Initialise core services and attach them to the Flask ``app``."""

    if "TRADING_CONFIG" not in app.config:
        raise KeyError("TRADING_CONFIG missing from app.config; cannot initialise services")

    trading_config = app.config["TRADING_CONFIG"]
    logger.info("Initialising backend services")

    try:
        credentials = load_alpaca_credentials(trading_config)
        alpaca_client = AlpacaClient(credentials)
        logger.info("Alpaca client initialised successfully")
    except Exception as exc:
        logger.warning("Failed to initialise Alpaca client: %s", exc)
        logger.warning("Running without Alpaca API - some features will be unavailable")
        alpaca_client = None
    app.alpaca_client = alpaca_client

    trading_service = (
        TradingService(alpaca_client=alpaca_client, config=trading_config)
        if alpaca_client
        else None
    )
    app.trading_service = trading_service

    database_url = getattr(getattr(trading_config, "database", None), "url", "")
    db_path = _sqlite_path_from_url(database_url) if database_url else "database/trading_data.db"
    if not database_url:
        logger.warning("Trading config missing database URL; defaulting to %s", db_path)

    pnl_service = PnLService(alpaca_client=alpaca_client, db_path=db_path) if alpaca_client else None
    app.pnl_service = pnl_service

    try:
        from core.service_registry import ServiceRegistry
    except Exception:  # pragma: no cover - optional dependency
        logger.info("ServiceRegistry unavailable; skipping registry integration")
    else:
        registry = ServiceRegistry()
        registered = False
        if alpaca_client:
            registry.register("alpaca_client", alpaca_client)
            registered = True
        if trading_service:
            registry.register("trading_service", trading_service)
            registered = True
        if pnl_service:
            registry.register("pnl_service", pnl_service)
            registered = True
        if registered:
            app.service_registry = registry
            logger.info("Services registered with ServiceRegistry")

    logger.info("Services initialised successfully")


__all__ = ["init_services", "TradingService", "PnLService", "AlpacaClient"]
