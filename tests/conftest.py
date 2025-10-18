"""Pytest configuration shared across the test suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

# Always disable backend service init in tests; we patch services below.
os.environ.setdefault("DISABLE_BACKEND_SERVICE_INIT", "1")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.helpers import ensure_strategy_runtime_dependencies

_SERVICE_PATCH: pytest.MonkeyPatch | None = None


def pytest_sessionstart(session: pytest.Session) -> None:
    """Install backend service stubs before collection begins."""

    if os.environ.get("DISABLE_BACKEND_SERVICE_INIT") != "1":
        return

    _apply_backend_service_stubs()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Restore backend service wiring after the test session."""

    if os.environ.get("DISABLE_BACKEND_SERVICE_INIT") != "1":
        return

    _remove_backend_service_stubs()


class _StubTradingService:
    def __init__(self, _alpaca_client: Any, config: Any) -> None:
        self._config = config

    def get_system_status(self) -> Dict[str, Any]:
        return {
            "last_update": None,
            "market_status": "OPEN",
            "is_trading": False,
            "services": {"alpaca": "connected", "trading_bot": "stopped"},
        }

    def get_account_data(self) -> Dict[str, Any]:
        return {
            "status": "ACTIVE",
            "buying_power": 100000.0,
            "portfolio_value": 100000.0,
            "cash": 100000.0,
            "equity": 100000.0,
            "pattern_day_trader": False,
            "trading_blocked": False,
            "account_blocked": False,
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        return []

    def calculate_signals(self, symbols: List[str] | None = None) -> List[Dict[str, Any]]:
        effective = symbols or list(getattr(self._config, "symbols", []) or [])
        return [{"symbol": symbol, "action": "BUY"} for symbol in effective]


class _StubPnLService:
    def __init__(self, *_, **__) -> None:
        pass

    def get_current_pnl(self) -> Dict[str, Any]:
        return {
            "daily_pnl": 0.0,
            "total_pnl": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "win_rate": 0.0,
            "positions": [],
        }

    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        trades = [
            {
                "timestamp": "2025-10-15T10:00:00Z",
                "symbol": "BTC/USD",
                "side": "buy",
                "qty": 0.01,
                "price": 30000.0,
            }
        ]
        return trades[:limit]

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Automatically guard strategy tests behind their optional dependencies."""

    if item.get_closest_marker("requires_strategy_runtime"):
        ensure_strategy_runtime_dependencies()


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used across the suite."""

    config.addinivalue_line(
        "markers",
        "requires_strategy_runtime: skip when strategy runtime dependencies are missing",
    )


def _apply_backend_service_stubs() -> None:
    """Patch backend service wiring to use lightweight test doubles."""

    global _SERVICE_PATCH

    if _SERVICE_PATCH is not None:
        return

    import backend.api as backend_api
    from backend.api import services

    patch = pytest.MonkeyPatch()
    _SERVICE_PATCH = patch

    patch.setattr(services, "load_alpaca_credentials", lambda _cfg: SimpleNamespace())
    patch.setattr(services, "TradingService", _StubTradingService)
    patch.setattr(services, "PnLService", _StubPnLService)
    patch.setattr(services, "AlpacaClient", lambda *_, **__: SimpleNamespace())

    def _init_services(app) -> None:  # type: ignore[override]
        trading_cfg = app.config.get("TRADING_CONFIG")
        app.alpaca_client = SimpleNamespace()
        app.trading_service = _StubTradingService(app.alpaca_client, trading_cfg)
        app.pnl_service = _StubPnLService()

    patch.setattr(services, "init_services", _init_services, raising=False)

    original_create_app = backend_api.create_app
    
    def _wrapped_create_app(config_name: str = "development"):
        app = original_create_app(config_name)
        if os.environ.get("DISABLE_BACKEND_SERVICE_INIT") == "1":
            if not hasattr(app, "alpaca_client"):
                app.alpaca_client = SimpleNamespace()
            if not hasattr(app, "trading_service"):
                app.trading_service = _StubTradingService(app.alpaca_client, app.config.get("TRADING_CONFIG"))
            if not hasattr(app, "pnl_service"):
                app.pnl_service = _StubPnLService()
        return app

    patch.setattr(backend_api, "create_app", _wrapped_create_app, raising=False)


def _remove_backend_service_stubs() -> None:
    """Undo backend service monkeypatching."""

    global _SERVICE_PATCH

    if _SERVICE_PATCH is None:
        return

    _SERVICE_PATCH.undo()
    _SERVICE_PATCH = None
